"""Comprehensive error handling framework with retry logic and graceful degradation"""

import asyncio
import functools
import logging
from typing import Optional, Callable, Any, Type, Tuple, Dict
from dataclasses import dataclass
from enum import Enum
import traceback

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for error handling"""
    error: Exception
    severity: ErrorSeverity
    operation: str
    retry_count: int = 0
    recoverable: bool = True
    metadata: Dict[str, Any] = None


class ErrorHandler:
    """
    Comprehensive error handling with retry logic, fallbacks, and monitoring.

    Features:
    - Automatic retry with exponential backoff
    - Fallback functions
    - Error categorization and severity
    - Error metrics and reporting
    - Graceful degradation
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        enable_logging: bool = True
    ):
        """
        Initialize error handler

        Args:
            max_retries: Maximum retry attempts
            base_delay: Base delay between retries (seconds)
            max_delay: Maximum delay between retries (seconds)
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to delays
            enable_logging: Enable error logging
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.enable_logging = enable_logging

        # Error statistics
        self._stats = {
            "total_errors": 0,
            "retried_operations": 0,
            "successful_retries": 0,
            "failed_retries": 0,
            "fallbacks_used": 0,
            "errors_by_type": {},
            "errors_by_severity": {
                ErrorSeverity.LOW: 0,
                ErrorSeverity.MEDIUM: 0,
                ErrorSeverity.HIGH: 0,
                ErrorSeverity.CRITICAL: 0,
            }
        }

    def _calculate_delay(self, retry_count: int) -> float:
        """Calculate delay for retry with exponential backoff"""
        delay = min(
            self.base_delay * (self.exponential_base ** retry_count),
            self.max_delay
        )

        # Add jitter
        if self.jitter:
            import random
            delay *= (0.5 + random.random())

        return delay

    def _categorize_error(self, error: Exception) -> Tuple[ErrorSeverity, bool]:
        """
        Categorize error by severity and recoverability

        Args:
            error: Exception to categorize

        Returns:
            Tuple of (severity, recoverable)
        """
        # Network/IO errors - usually recoverable
        if isinstance(error, (ConnectionError, TimeoutError, OSError)):
            return ErrorSeverity.MEDIUM, True

        # Resource errors - may be recoverable
        if isinstance(error, (MemoryError, ResourceWarning)):
            return ErrorSeverity.HIGH, True

        # Value/Type errors - usually not recoverable
        if isinstance(error, (ValueError, TypeError, KeyError)):
            return ErrorSeverity.LOW, False

        # System errors - critical
        if isinstance(error, (SystemError, RuntimeError)):
            return ErrorSeverity.CRITICAL, False

        # Default
        return ErrorSeverity.MEDIUM, True

    async def handle_async(
        self,
        func: Callable,
        *args,
        operation_name: str = None,
        fallback: Optional[Callable] = None,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
        **kwargs
    ) -> Any:
        """
        Handle async function with retry logic

        Args:
            func: Async function to execute
            *args: Function arguments
            operation_name: Name of operation for logging
            fallback: Fallback function if all retries fail
            retryable_exceptions: Exceptions to retry on
            **kwargs: Function keyword arguments

        Returns:
            Function result or fallback result

        Raises:
            Exception: If all retries fail and no fallback
        """
        operation = operation_name or func.__name__
        last_error = None

        for retry in range(self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)

                if retry > 0 and self.enable_logging:
                    logger.info(f"Operation '{operation}' succeeded after {retry} retries")
                    self._stats["successful_retries"] += 1

                return result

            except retryable_exceptions as e:
                last_error = e
                severity, recoverable = self._categorize_error(e)

                # If exception is explicitly in retryable_exceptions, mark as recoverable
                recoverable = True

                # Update statistics
                self._stats["total_errors"] += 1
                self._stats["errors_by_severity"][severity] += 1
                error_type = type(e).__name__
                self._stats["errors_by_type"][error_type] = \
                    self._stats["errors_by_type"].get(error_type, 0) + 1

                # Log error
                if self.enable_logging:
                    if retry < self.max_retries:
                        logger.warning(
                            f"Operation '{operation}' failed (attempt {retry + 1}/{self.max_retries + 1}): {e}"
                        )
                    else:
                        logger.error(
                            f"Operation '{operation}' failed permanently: {e}\n"
                            f"{traceback.format_exc()}"
                        )

                # Update retry stats
                if retry < self.max_retries:
                    self._stats["retried_operations"] += 1
                else:
                    self._stats["failed_retries"] += 1

                # Check if we should retry
                if retry >= self.max_retries:
                    break

                # Wait before retry
                delay = self._calculate_delay(retry)
                await asyncio.sleep(delay)

        # All retries failed, try fallback
        if fallback:
            if self.enable_logging:
                logger.info(f"Using fallback for operation '{operation}'")
            self._stats["fallbacks_used"] += 1

            try:
                if asyncio.iscoroutinefunction(fallback):
                    return await fallback(*args, **kwargs)
                else:
                    return fallback(*args, **kwargs)
            except Exception as fallback_error:
                logger.error(f"Fallback failed for '{operation}': {fallback_error}")
                raise last_error from fallback_error

        # No fallback, raise last error
        raise last_error

    def handle_sync(
        self,
        func: Callable,
        *args,
        operation_name: str = None,
        fallback: Optional[Callable] = None,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
        **kwargs
    ) -> Any:
        """
        Handle sync function with retry logic

        Args:
            func: Function to execute
            *args: Function arguments
            operation_name: Name of operation for logging
            fallback: Fallback function if all retries fail
            retryable_exceptions: Exceptions to retry on
            **kwargs: Function keyword arguments

        Returns:
            Function result or fallback result

        Raises:
            Exception: If all retries fail and no fallback
        """
        operation = operation_name or func.__name__
        last_error = None

        for retry in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)

                if retry > 0 and self.enable_logging:
                    logger.info(f"Operation '{operation}' succeeded after {retry} retries")
                    self._stats["successful_retries"] += 1

                return result

            except retryable_exceptions as e:
                last_error = e
                severity, recoverable = self._categorize_error(e)

                # If exception is explicitly in retryable_exceptions, mark as recoverable
                recoverable = True

                # Update statistics
                self._stats["total_errors"] += 1
                self._stats["errors_by_severity"][severity] += 1
                error_type = type(e).__name__
                self._stats["errors_by_type"][error_type] = \
                    self._stats["errors_by_type"].get(error_type, 0) + 1

                # Log error
                if self.enable_logging:
                    if retry < self.max_retries:
                        logger.warning(
                            f"Operation '{operation}' failed (attempt {retry + 1}/{self.max_retries + 1}): {e}"
                        )
                    else:
                        logger.error(
                            f"Operation '{operation}' failed permanently: {e}\n"
                            f"{traceback.format_exc()}"
                        )

                # Update retry stats
                if retry < self.max_retries:
                    self._stats["retried_operations"] += 1
                else:
                    self._stats["failed_retries"] += 1

                # Check if we should retry
                if retry >= self.max_retries:
                    break

                # Wait before retry
                import time
                delay = self._calculate_delay(retry)
                time.sleep(delay)

        # All retries failed, try fallback
        if fallback:
            if self.enable_logging:
                logger.info(f"Using fallback for operation '{operation}'")
            self._stats["fallbacks_used"] += 1

            try:
                return fallback(*args, **kwargs)
            except Exception as fallback_error:
                logger.error(f"Fallback failed for '{operation}': {fallback_error}")
                raise last_error from fallback_error

        # No fallback, raise last error
        raise last_error

    def get_stats(self) -> Dict[str, Any]:
        """Get error handling statistics"""
        return {
            **self._stats,
            "retry_success_rate": (
                self._stats["successful_retries"] / self._stats["retried_operations"]
                if self._stats["retried_operations"] > 0
                else 0.0
            )
        }


# Decorator for async functions
def with_retry(
    max_retries: int = 3,
    fallback: Optional[Callable] = None,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for automatic retry logic on async functions

    Args:
        max_retries: Maximum retry attempts
        fallback: Fallback function
        retryable_exceptions: Exceptions to retry on

    Returns:
        Decorated function
    """
    def decorator(func):
        handler = ErrorHandler(max_retries=max_retries)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await handler.handle_async(
                func,
                *args,
                fallback=fallback,
                retryable_exceptions=retryable_exceptions,
                **kwargs
            )
        return wrapper
    return decorator


# Global error handler instance
_global_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    return _global_handler
