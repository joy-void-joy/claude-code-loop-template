"""Docker-based Python sandbox for isolated code execution.

Provides a persistent REPL inside a Docker container with state that
survives across calls (variables, imports, data).  Use ``Sandbox`` as a
context manager and call ``run_code`` / ``run_install`` directly, or
expose it to a Claude Agent SDK agent via ``create_tools()`` /
``create_mcp_server()``.

Network modes:
- "bridge": Full network access (default)
- "none": No network access at all
"""

import io
import json
import logging
import tarfile
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal, Self, TypedDict

import docker
from claude_agent_sdk import SdkMcpTool, tool
from claude_agent_sdk.types import McpSdkServerConfig
from docker.errors import APIError, DockerException, NotFound
from docker.models.containers import Container, ExecResult
from docker.utils.socket import SocketError, next_frame_header, read_exactly
from pydantic import BaseModel, Field

from lup.lib.mcp import create_mcp_server
from lup.lib.metrics import tracked
from lup.lib.responses import mcp_error, mcp_success

logger = logging.getLogger(__name__)

NetworkMode = Literal["bridge", "none"]

DEFAULT_PRE_INSTALL: tuple[str, ...] = (
    "requests",
    "pandas",
    "numpy",
    "beautifulsoup4",
    "lxml",
)
"""Packages pre-installed in new containers by default."""


# --- Pydantic input schemas ---


class ExecuteCodeInput(BaseModel):
    """Input schema for the execute_code tool."""

    code: str = Field(min_length=1)


class InstallPackageInput(BaseModel):
    """Input schema for the install_package tool."""

    packages: list[str] = Field(min_length=1)


# --- TypedDict definitions for result types ---


class ExecuteCodeResult(TypedDict):
    """Result from executing Python code in the sandbox."""

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


class InstallPackageResult(TypedDict):
    """Result from installing packages in the sandbox."""

    exit_code: int
    output: str
    packages: list[str]


# --- Helper functions ---


def _decode_output(output: bytes | None) -> str:
    """Decode bytes output to string, handling None and errors."""
    if output is None:
        return ""
    return output.decode("utf-8", errors="replace")


# --- Sandbox class ---


class SandboxNotInitializedError(RuntimeError):
    """Raised when sandbox operations are called on an inactive sandbox."""


class CodeExecutionTimeoutError(RuntimeError):
    """Raised when code execution exceeds the timeout."""


class ReplCrashedError(RuntimeError):
    """Raised when the persistent REPL process has exited unexpectedly."""


_REPL_SERVER_SCRIPT = r"""
import json, signal, sys, time, traceback
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

_MAX_OUTPUT = 1_048_576
_namespace = {"__builtins__": __builtins__}

class _Timeout(Exception):
    pass

def _alarm(signum, frame):
    raise _Timeout()

_proto_in = sys.stdin
_proto_out = sys.stdout
sys.stdin = open("/dev/null", "r")
sys.stdout = open("/dev/null", "w")
sys.stderr = open("/dev/null", "w")

for _line in _proto_in:
    _line = _line.strip()
    if not _line:
        continue
    try:
        _req = json.loads(_line)
    except json.JSONDecodeError:
        _proto_out.write(json.dumps({"exit_code": 1, "stdout": "", "stderr": "Invalid JSON", "duration_ms": 0}) + "\n")
        _proto_out.flush()
        continue

    _code = _req.get("code", "")
    _timeout = _req.get("timeout", 30)
    _so = StringIO()
    _se = StringIO()
    _ec = 0
    _t0 = time.perf_counter()
    _old_alarm = signal.signal(signal.SIGALRM, _alarm)
    try:
        if _timeout > 0:
            signal.alarm(_timeout)
        with redirect_stdout(_so), redirect_stderr(_se):
            exec(compile(_code, "<cell>", "exec"), _namespace)
    except _Timeout:
        _ec = 124
        _se.write(f"Execution timed out after {_timeout} seconds\n")
    except SystemExit as _e:
        _ec = _e.code if isinstance(_e.code, int) else 1
    except BaseException:
        _ec = 1
        _se.write(traceback.format_exc())
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, _old_alarm)

    _ms = int((time.perf_counter() - _t0) * 1000)
    _proto_out.write(json.dumps({
        "exit_code": _ec,
        "stdout": _so.getvalue()[:_MAX_OUTPUT],
        "stderr": _se.getvalue()[:_MAX_OUTPUT],
        "duration_ms": _ms,
    }) + "\n")
    _proto_out.flush()
"""


class ReplSession:
    """Persistent Python REPL inside a Docker container.

    Communicates over Docker's exec socket API using a JSON-line protocol.
    The REPL maintains a shared namespace across code executions, so
    variables and imports persist between calls.
    """

    def __init__(
        self,
        client: docker.DockerClient,
        container: Container,
        environment: dict[str, str],
    ) -> None:
        self._client = client
        self._container = container
        self._environment = environment
        self._sock: Any = None
        self._exec_id: str | None = None

    def start(self) -> None:
        """Start the REPL process and verify it responds."""
        exec_result: dict[str, str] = self._client.api.exec_create(
            self._container.id,
            ["python", "-u", "/workspace/.repl_server.py"],
            stdin=True,
            stdout=True,
            stderr=True,
            tty=False,
            workdir="/workspace",
            environment=self._environment or None,
        )
        self._exec_id = exec_result["Id"]
        self._sock = self._client.api.exec_start(self._exec_id, socket=True)
        result = self.execute("pass", timeout_seconds=10)
        if result["exit_code"] != 0:
            raise RuntimeError(f"REPL startup failed: {result['stderr']}")
        logger.info("Persistent REPL started")

    def stop(self) -> None:
        """Close the socket connection to the REPL."""
        if self._sock is not None:
            try:
                response = getattr(self._sock, "_response", None)
                if response is not None:
                    response.close()
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        self._exec_id = None

    def execute(self, code: str, timeout_seconds: int) -> ExecuteCodeResult:
        """Send code to the REPL and return the result."""
        if self._sock is None:
            raise SandboxNotInitializedError("REPL not connected")

        request = json.dumps({"code": code, "timeout": timeout_seconds}) + "\n"
        self._send(request.encode("utf-8"))

        deadline = time.monotonic() + timeout_seconds + 5
        try:
            response = self._recv_response(deadline)
        except (SocketError, OSError) as e:
            raise ReplCrashedError(f"REPL exited: {e}") from e

        if response.get("exit_code") == 124:
            raise CodeExecutionTimeoutError(
                f"Code execution timed out after {timeout_seconds} seconds"
            )

        return ExecuteCodeResult(
            exit_code=int(response.get("exit_code", 1)),
            stdout=str(response.get("stdout", "")),
            stderr=str(response.get("stderr", "")),
            duration_ms=int(response.get("duration_ms", 0)),
        )

    def _send(self, data: bytes) -> None:
        """Write raw bytes to the exec socket stdin."""
        try:
            sock = getattr(self._sock, "_sock", self._sock)
            if hasattr(sock, "sendall"):
                sock.sendall(data)
            else:
                self._sock.write(data)
        except (BrokenPipeError, OSError) as e:
            raise ReplCrashedError(f"REPL write failed: {e}") from e

    def _recv_response(self, deadline: float) -> dict[str, int | str]:
        """Read Docker multiplex frames until a complete JSON line arrives."""
        stdout_buf = b""
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ReplCrashedError("Timed out waiting for REPL response")
            self._set_socket_timeout(remaining)

            stream_type, size = next_frame_header(self._sock)
            if size < 0:
                raise ReplCrashedError("REPL EOF")

            data = read_exactly(self._sock, size)
            match stream_type:
                case 1:  # stdout
                    stdout_buf += data
                    if b"\n" in stdout_buf:
                        line, _, _ = stdout_buf.partition(b"\n")
                        return json.loads(line.decode("utf-8"))
                case 2:  # stderr
                    logger.debug(
                        "REPL stderr: %s", data.decode("utf-8", errors="replace")
                    )

    def _set_socket_timeout(self, timeout: float) -> None:
        """Set timeout on the underlying socket."""
        sock = self._sock
        for candidate in [sock, getattr(sock, "_sock", None)]:
            if hasattr(candidate, "settimeout"):
                candidate.settimeout(timeout)
                return


class Sandbox:
    """Docker-based Python sandbox for isolated code execution.

    Each session gets a unique container and volume, so concurrent sessions
    cannot interfere with each other.

    Args:
        session_id: Unique identifier for this session (used in container/volume names).
        shared_dir: Local directory to mount at /shared for host-sandbox file exchange.
        docker_image: Docker image to use for the sandbox.
        network_mode: Network access level ("bridge" or "none").
        timeout_seconds: Default timeout for code execution.
        pre_install: Packages to pre-install on start. Pass ``None`` to skip.
    """

    DEFAULT_DOCKER_IMAGE = "ghcr.io/astral-sh/uv:python3.12-bookworm-slim"

    def __init__(
        self,
        *,
        session_id: str,
        shared_dir: str | Path,
        docker_image: str = DEFAULT_DOCKER_IMAGE,
        network_mode: NetworkMode = "bridge",
        timeout_seconds: int = 30,
        pre_install: Sequence[str] | None = DEFAULT_PRE_INSTALL,
    ) -> None:
        suffix = session_id.replace("/", "-")
        self._container_name = f"lup-sandbox-{suffix}"
        self._docker_image = docker_image
        self._volume_name = f"lup-sandbox-ws-{suffix}"
        self._shared_dir = Path(shared_dir).resolve()
        self._network_mode = network_mode
        self._timeout_seconds = timeout_seconds
        self._pre_install = list(pre_install) if pre_install is not None else None
        self._container: Container | None = None
        self._client: docker.DockerClient | None = None
        self._repl: ReplSession | None = None

    @property
    def container(self) -> Container:
        """Get the active container."""
        if self._container is None:
            raise SandboxNotInitializedError(
                "Sandbox not initialized. Use 'with Sandbox() as sandbox:' first."
            )
        return self._container

    @property
    def is_active(self) -> bool:
        """Check if the sandbox container is currently running."""
        return self._container is not None

    def _remove_stale_container(self) -> None:
        """Remove a pre-existing container with the same name, if any."""
        if self._client is None:
            return
        try:
            old = self._client.containers.get(self._container_name)
            logger.warning("Removing stale container: %s", self._container_name)
            old.remove(force=True)
        except NotFound:
            pass

    def _destroy_container(self) -> None:
        """Stop and remove the current container and its session volume."""
        if self._container is None:
            return
        try:
            self._container.stop(timeout=5)
            self._container.remove()
        except (APIError, DockerException) as e:
            logger.warning("Failed to cleanup container: %s", e)
        finally:
            self._container = None

        if self._client is not None:
            try:
                vol = self._client.volumes.get(self._volume_name)
                vol.remove()
            except (NotFound, APIError):
                pass

    def _exec(self, cmd: str | list[str]) -> ExecResult:
        """Execute a command in the container."""
        if isinstance(cmd, str):
            cmd = ["sh", "-c", cmd]
        return self.container.exec_run(cmd, demux=False)

    def _write_repl_script(self) -> None:
        """Write the REPL server script into the container via tar archive."""
        script_bytes = _REPL_SERVER_SCRIPT.encode("utf-8")
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            info = tarfile.TarInfo(name=".repl_server.py")
            info.size = len(script_bytes)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(script_bytes))
        buf.seek(0)
        self.container.put_archive("/workspace", buf)

    def _run_pre_install(self) -> None:
        """Pre-install packages for faster agent execution."""
        if self._pre_install is None:
            return
        logger.info("Pre-installing packages: %s", self._pre_install)
        cmd = ["uv", "pip", "install", "--system", *self._pre_install]
        result = self.container.exec_run(cmd, demux=False)
        if result.exit_code != 0:
            logger.warning(
                "Package pre-install failed (exit %d): %s",
                result.exit_code,
                _decode_output(result.output)[:500],
            )
        else:
            logger.info("Pre-installed packages successfully")

    def start(self) -> None:
        """Start the sandbox container.

        Creates a new Docker container for code execution. Removes any
        stale container with the same name first.
        """
        self._client = docker.from_env()

        self._remove_stale_container()

        self._shared_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Creating sandbox container: %s (network=%s)",
            self._container_name,
            self._network_mode,
        )
        logger.info("Mounting shared directory: %s -> /shared", self._shared_dir)
        self._container = self._client.containers.run(
            self._docker_image,
            name=self._container_name,
            command="sleep infinity",
            detach=True,
            volumes={
                self._volume_name: {"bind": "/workspace", "mode": "rw"},
                str(self._shared_dir): {"bind": "/shared", "mode": "rw"},
            },
            working_dir="/workspace",
            mem_limit="1g",
            network_mode=self._network_mode,
        )

        if self._network_mode != "none":
            self._run_pre_install()

        self._write_repl_script()
        assert self._client is not None
        assert self._container is not None
        self._repl = ReplSession(self._client, self._container, {})
        self._repl.start()

    def stop(self) -> None:
        """Stop and remove the sandbox container."""
        if self._repl is not None:
            self._repl.stop()
            self._repl = None
        logger.info("Destroying sandbox container")
        self._destroy_container()
        self._client = None

    def __enter__(self) -> Self:
        """Enter context manager, starting the sandbox."""
        started = False
        try:
            self.start()
            started = True
        finally:
            if not started:
                self.stop()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit context manager, stopping the sandbox."""
        self.stop()

    # --- Code execution methods ---

    def run_code(
        self, code: str, timeout_seconds: int | None = None
    ) -> ExecuteCodeResult:
        """Execute Python code in the sandbox's persistent REPL.

        Variables, imports, and data persist between calls within the same
        session. If the REPL crashes, it is restarted automatically (but
        state from previous cells is lost).

        Args:
            code: Python code to execute.
            timeout_seconds: Max execution time in seconds. If None, uses
                the sandbox's default timeout. Set to 0 for no timeout.

        Returns:
            Result containing exit code, stdout, stderr, and duration.
        """
        if self._repl is None:
            raise SandboxNotInitializedError("REPL not initialized")
        if timeout_seconds is None:
            timeout_seconds = self._timeout_seconds

        try:
            return self._repl.execute(code, timeout_seconds)
        except ReplCrashedError:
            logger.warning("REPL crashed, restarting")
            self._repl.stop()
            try:
                self._repl.start()
            except (RuntimeError, DockerException, APIError, SocketError):
                logger.exception("REPL restart failed")
                self._repl = None
                raise SandboxNotInitializedError("REPL restart failed")
            return ExecuteCodeResult(
                exit_code=1,
                stdout="",
                stderr=(
                    "REPL process crashed and was restarted. "
                    "Variables from previous cells have been lost. "
                    "Please re-run any setup code."
                ),
                duration_ms=0,
            )

    def run_install(self, packages: list[str]) -> InstallPackageResult:
        """Install Python packages using uv.

        Args:
            packages: List of package names to install.

        Returns:
            Result containing exit code, output, and package list.
        """
        cmd = ["uv", "pip", "install", "--system", *packages]
        result: ExecResult = self.container.exec_run(cmd, demux=False)

        output_text = _decode_output(result.output)

        return InstallPackageResult(
            exit_code=result.exit_code,
            output=output_text,
            packages=packages,
        )

    # --- MCP tool creation ---

    def create_tools(
        self,
    ) -> list[SdkMcpTool[ExecuteCodeInput] | SdkMcpTool[InstallPackageInput]]:
        """Create MCP tools bound to this sandbox instance.

        Returns:
            List of MCP tools for code execution and package installation.
        """
        timeout_seconds = self._timeout_seconds

        @tool(
            "execute_code",
            (
                "Execute Python code in an isolated Docker container with persistent state. "
                "Variables, imports, and data persist between calls — no need to re-define them. "
                f"The container has network access, a persistent /workspace directory, and a "
                f"/shared directory for file exchange with the host. Timeout: {timeout_seconds}s.\n\n"
                "Examples:\n"
                "  execute_code(code='import numpy as np; data = [1,2,3]; print(np.mean(data))')\n"
                "  execute_code(code='# Monte Carlo simulation\\nimport numpy as np\\n"
                "returns = np.random.normal(0.0005, 0.015, (10000, 14))\\n"
                "paths = 100 * np.cumprod(1 + returns, axis=1)\\n"
                "print(np.percentile(paths[:,-1], [10,25,50,75,90]))')\n"
                "State persists: define variables in one call, use them in the next."
            ),
            ExecuteCodeInput.model_json_schema(),
        )
        @tracked("execute_code")
        async def execute_code(args: dict[str, Any]) -> dict[str, Any]:
            try:
                validated = ExecuteCodeInput.model_validate(args)
            except Exception as e:
                return mcp_error(f"Invalid input: {e}")

            try:
                result = self.run_code(validated.code)
                return mcp_success(result)
            except SandboxNotInitializedError as e:
                logger.error("Sandbox not initialized: %s", e)
                return mcp_error(f"Sandbox error: {e}")
            except CodeExecutionTimeoutError as e:
                logger.warning("Code execution timed out")
                return mcp_error(str(e))
            except (APIError, DockerException) as e:
                logger.exception("Docker execution failed")
                return mcp_error(f"Docker error: {e}")

        @tool(
            "install_package",
            "Install one or more Python packages from PyPI using uv. Packages persist "
            "in the container across executions.",
            InstallPackageInput.model_json_schema(),
        )
        @tracked("install_package")
        async def install_package(args: dict[str, Any]) -> dict[str, Any]:
            try:
                validated = InstallPackageInput.model_validate(args)
            except Exception as e:
                return mcp_error(f"Invalid input: {e}")

            try:
                result = self.run_install(validated.packages)
                return mcp_success(result)
            except SandboxNotInitializedError as e:
                logger.error("Sandbox not initialized: %s", e)
                return mcp_error(f"Sandbox error: {e}")
            except (APIError, DockerException) as e:
                logger.exception("Docker execution failed")
                return mcp_error(f"Docker error: {e}")

        return [execute_code, install_package]

    def create_mcp_server(
        self,
        name: str = "sandbox",
        version: str = "1.0.0",
    ) -> McpSdkServerConfig:
        """Create an MCP server with sandbox tools."""
        return create_mcp_server(
            name=name,
            version=version,
            tools=self.create_tools(),
        )
