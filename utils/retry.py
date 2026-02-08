"""Async retry decorator with exponential backoff."""

import asyncio
import functools
import re
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar
import structlog

log = structlog.get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

# Patterns that look like API keys in URLs
_SENSITIVE_PARAMS = re.compile(
    r"((?:token|api_?key|api_?token|secret|password|authorization)=)[^&\s'\")]+",
    re.IGNORECASE,
)


def _sanitize_error(error: str) -> str:
    """Strip API keys and tokens from error messages."""
    return _SENSITIVE_PARAMS.sub(r"\1[REDACTED]", error)


def async_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorator for async functions with exponential backoff retry."""

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_exception: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        break
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    log.warning(
                        "retry_attempt",
                        func=func.__name__,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay=delay,
                        error=_sanitize_error(str(e)),
                    )
                    await asyncio.sleep(delay)
            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator
