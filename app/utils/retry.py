from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from app.utils.logging import get_logger

T = TypeVar("T")


def retry_call(
    operation: Callable[[], T],
    *,
    operation_name: str,
    max_attempts: int = 3,
    base_delay_seconds: float = 1.0,
    retry_exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    """Retry transient failures with exponential backoff."""

    logger = get_logger(__name__)
    attempt = 1

    while True:
        try:
            return operation()
        except retry_exceptions as exc:
            if attempt >= max_attempts:
                logger.exception(
                    "Operation '%s' failed after %s attempts.",
                    operation_name,
                    attempt,
                )
                raise

            delay = base_delay_seconds * (2 ** (attempt - 1))
            logger.warning(
                "Operation '%s' failed on attempt %s/%s: %s. Retrying in %.1f seconds.",
                operation_name,
                attempt,
                max_attempts,
                exc,
                delay,
            )
            time.sleep(delay)
            attempt += 1
