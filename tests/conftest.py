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
