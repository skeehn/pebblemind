"""Pytest configuration and fixtures"""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
async def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_config():
    """Sample configuration for tests"""
    return {
        "llm": {
            "model_size": "3b",
            "context_length": 2048,
            "max_tokens": 256,
        },
        "cache": {
            "enabled": True,
            "max_size": 100,
            "max_memory_mb": 50,
        },
        "monitoring": {
            "enabled": True,
        }
    }


_exit_status = None


def pytest_sessionfinish(session, exitstatus):
    """Remember the final status; the hard exit happens in unconfigure
    (after the terminal summary and cache writes)."""
    global _exit_status
    _exit_status = int(exitstatus)


def pytest_unconfigure(config):
    """Hard-exit with pytest's status on macOS.

    The bundled ggml Metal backend aborts during exit-time device teardown
    (GGML_ASSERT([rsets->data count] == 0) — ggml-org/llama.cpp#17869),
    which turns a fully green run into SIGABRT/-6 for anything checking
    the return code. CI (Linux) is unaffected.
    """
    import os
    import sys

    if _exit_status is not None and sys.platform == "darwin" and "llama_cpp" in sys.modules:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(_exit_status)
