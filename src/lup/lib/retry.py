"""Retry utilities for API calls using tenacity."""

from collections.abc import Callable

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


def with_retry[T](
    max_attempts: int = 3,
    min_wait: float = 2,
    max_wait: float = 10,
    extra_exceptions: tuple[type[Exception], ...] = (),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retrying async functions with exponential backoff.

    Retries on HTTP errors (status errors, timeouts, connection errors)
    plus any additional exception types specified via extra_exceptions.

    Args:
        max_attempts: Maximum number of retry attempts.
        min_wait: Minimum wait time between retries in seconds.
        max_wait: Maximum wait time between retries in seconds.
        extra_exceptions: Additional exception types to retry on.

    Returns:
        Decorator that wraps the function with retry logic.

    Example:
        @with_retry(max_attempts=3)
        async def fetch_data():
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
    """
    retryable = (
        httpx.HTTPStatusError,
        httpx.TimeoutException,
        httpx.ConnectError,
        *extra_exceptions,
    )
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(retryable),
        reraise=True,
    )
