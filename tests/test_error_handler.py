"""Tests for error handling framework"""

import pytest
import asyncio
from pebblemind.utils.error_handler import ErrorHandler, with_retry


@pytest.mark.asyncio
async def test_successful_execution():
    """Test successful function execution"""
    handler = ErrorHandler(max_retries=3)

    async def successful_func():
        return "success"

    result = await handler.handle_async(successful_func)
    assert result == "success"


@pytest.mark.asyncio
async def test_retry_on_failure():
    """Test retry logic on failures"""
    handler = ErrorHandler(max_retries=3, base_delay=0.1)

    attempts = []

    async def failing_func():
        attempts.append(1)
        if len(attempts) < 3:
            raise ConnectionError("Temporary failure")
        return "success"

    result = await handler.handle_async(
        failing_func,
        retryable_exceptions=(ConnectionError,)
    )

    assert result == "success"
    assert len(attempts) == 3  # Failed twice, succeeded on third


@pytest.mark.asyncio
async def test_max_retries_exceeded():
    """Test behavior when max retries exceeded"""
    handler = ErrorHandler(max_retries=2, base_delay=0.1)

    async def always_failing():
        raise ConnectionError("Always fails")

    with pytest.raises(ConnectionError):
        await handler.handle_async(
            always_failing,
            retryable_exceptions=(ConnectionError,)
        )


@pytest.mark.asyncio
async def test_fallback_function():
    """Test fallback function execution"""
    handler = ErrorHandler(max_retries=2, base_delay=0.1)

    async def failing_func():
        raise ValueError("Always fails")

    async def fallback_func():
        return "fallback_result"

    result = await handler.handle_async(
        failing_func,
        fallback=fallback_func,
        retryable_exceptions=(ValueError,)
    )

    assert result == "fallback_result"


@pytest.mark.asyncio
async def test_non_retryable_exception():
    """Test that non-retryable exceptions fail immediately"""
    handler = ErrorHandler(max_retries=3, base_delay=0.1)

    attempts = []

    async def func_with_value_error():
        attempts.append(1)
        raise ValueError("Not retryable")

    with pytest.raises(ValueError):
        await handler.handle_async(
            func_with_value_error,
            retryable_exceptions=(ConnectionError,)  # Only retry ConnectionError
        )

    # Should fail immediately without retries
    assert len(attempts) == 1


@pytest.mark.asyncio
async def test_retry_decorator():
    """Test retry decorator"""
    attempts = []

    @with_retry(max_retries=3, retryable_exceptions=(ValueError,))
    async def decorated_func():
        attempts.append(1)
        if len(attempts) < 2:
            raise ValueError("Temporary failure")
        return "success"

    result = await decorated_func()
    assert result == "success"
    assert len(attempts) == 2


def test_sync_error_handler():
    """Test synchronous error handling"""
    handler = ErrorHandler(max_retries=2, base_delay=0.1)

    attempts = []

    def failing_func():
        attempts.append(1)
        if len(attempts) < 2:
            raise ValueError("Temporary failure")
        return "success"

    result = handler.handle_sync(
        failing_func,
        retryable_exceptions=(ValueError,)
    )

    assert result == "success"
    assert len(attempts) == 2


def test_error_handler_stats():
    """Test error handler statistics"""
    handler = ErrorHandler(max_retries=2, base_delay=0.1)

    def failing_func():
        raise ValueError("Always fails")

    try:
        handler.handle_sync(
            failing_func,
            retryable_exceptions=(ValueError,)
        )
    except ValueError:
        pass

    stats = handler.get_stats()
    assert stats["total_errors"] > 0
    assert stats["retried_operations"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
