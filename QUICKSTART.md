# PebbleMind Quick Start Guide

Get PebbleMind up and running in 5 minutes! This guide will help you set up and test the core functionality.

## Prerequisites

- Python 3.9 or higher
- 8GB+ RAM (16GB recommended)
- macOS, Linux, or Windows

## Installation

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/yourusername/pebblemind.git
cd pebblemind

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install PebbleMind with development dependencies
pip install -e ".[dev]"
```

### 2. Install Optional Dependencies

```bash
# For voice features (optional)
pip install -e ".[voice]"

# For desktop app (optional)
pip install -e ".[desktop]"
```

## Running Tests

Verify your installation by running the test suite:

```bash
# Run all tests (should see 79 passing)
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ --cov=pebblemind --cov-report=html
```

**Expected output:**
```
============================== 79 passed in 5.61s ===============================
```

## Basic Usage Examples

### 1. Response Caching

```python
import asyncio
from pebblemind.cache import ResponseCache

async def main():
    # Create cache
    cache = ResponseCache(max_size=100, default_ttl=300)
    await cache.start()

    # Store value
    await cache.set("question", "What is AI?")

    # Retrieve value
    value, hit = await cache.get("question")
    print(f"Cache hit: {hit}, Value: {value}")

    # Get statistics
    stats = cache.get_stats()
    print(f"Cache stats: {stats}")

    await cache.stop()

asyncio.run(main())
```

### 2. Error Handling with Retry

```python
import asyncio
from pebblemind.utils.error_handler import ErrorHandler

async def unreliable_api_call():
    """Simulates an API that might fail"""
    import random
    if random.random() < 0.5:
        raise ConnectionError("Network timeout")
    return {"status": "success"}

async def main():
    handler = ErrorHandler(
        max_retries=3,
        base_delay=0.5,
        exponential_base=2
    )

    try:
        result = await handler.handle_async(
            unreliable_api_call,
            retryable_exceptions=(ConnectionError,)
        )
        print(f"Success: {result}")
    except Exception as e:
        print(f"Failed after retries: {e}")

    # View retry statistics
    stats = handler.get_stats()
    print(f"Retry stats: {stats}")

asyncio.run(main())
```

### 3. LLM Engine (with mocking for testing)

```python
import asyncio
from unittest.mock import MagicMock, patch
from pebblemind.config import LLMConfig
from pebblemind.core.llm import LLMEngine

async def main():
    # Create configuration
    config = LLMConfig(
        model_size="1.5b",
        model_path="",
        context_length=2048,
        max_tokens=256,
        threads=4
    )

    # Note: This requires llama-cpp-python and actual model files
    # For testing without models, see the test suite for mocking examples
    engine = LLMEngine(config)

    # Get model info (before initialization)
    info = await engine.get_model_info()
    print(f"Model status: {info['status']}")

    # In production, you would:
    # await engine.initialize()
    # response = await engine.generate("Hello, how are you?")

asyncio.run(main())
```

### 4. RAG System

```python
import asyncio
from pebblemind.config import RAGConfig
from pebblemind.rag.system import RAGSystem

async def main():
    # Create configuration
    config = RAGConfig(
        embedding_model="BAAI/bge-small-en-v1.5",
        embedding_dim=384,
        vector_db_path="./data/test_vectors.db",
        chunk_size=512,
        chunk_overlap=50
    )

    rag = RAGSystem(config)

    # Note: Requires sentence-transformers
    # For testing without heavy dependencies, see test_rag_system.py

    # In production:
    # await rag.initialize()
    #
    # # Add documents
    # documents = [
    #     {"content": "Python is a programming language", "metadata": {"source": "wiki"}},
    #     {"content": "AI is transforming technology", "metadata": {"source": "article"}}
    # ]
    # await rag.add_documents(documents)
    #
    # # Search
    # results = await rag.search("programming", k=5)
    # print(f"Found {len(results)} results")

asyncio.run(main())
```

### 5. Plugin System

```python
from pebblemind.plugins import PluginManager, Plugin, PluginType

# Define a custom plugin
class GreetingPlugin(Plugin):
    def __init__(self):
        super().__init__(
            name="greeter",
            version="1.0.0",
            plugin_type=PluginType.UTILITY
        )

    def execute(self, name: str) -> str:
        return f"Hello, {name}!"

# Use the plugin
manager = PluginManager()
plugin = GreetingPlugin()

# Load plugin
manager.load_plugin(plugin)

# Execute plugin
result = plugin.execute("World")
print(result)  # Output: Hello, World!

# List all plugins
plugins = manager.list_plugins()
print(f"Loaded plugins: {plugins}")
```

### 6. Using the Cached Decorator

```python
import asyncio
from pebblemind.cache import ResponseCache, cached

# Create global cache instance
cache = ResponseCache(max_size=100)

@cached(cache=cache, ttl=60)
async def expensive_computation(x: int) -> int:
    """This function will be cached"""
    print(f"Computing for {x}...")
    await asyncio.sleep(1)  # Simulate expensive operation
    return x * x

async def main():
    await cache.start()

    # First call - will compute
    result1 = await expensive_computation(5)
    print(f"Result 1: {result1}")  # Prints "Computing for 5..." and result

    # Second call - will use cache
    result2 = await expensive_computation(5)
    print(f"Result 2: {result2}")  # Instantly returns cached result

    await cache.stop()

asyncio.run(main())
```

## Configuration

PebbleMind uses a YAML configuration file. Create `pebblemind.yaml`:

```yaml
# LLM Configuration
llm:
  model_size: "1.5b"  # Options: 1.5b, 3b, 7b
  context_length: 2048
  max_tokens: 256
  temperature: 0.7
  enable_blas: true
  blas_vendor: "OpenBLAS"
  threads: -1  # Auto-detect

# Voice Configuration (optional)
voice:
  stt_model: "base.en"
  tts_model: "amy-low"
  sample_rate: 22050

# RAG Configuration
rag:
  embedding_model: "BAAI/bge-small-en-v1.5"
  vector_db_path: "./data/vectors.db"
  chunk_size: 512
  chunk_overlap: 32

# Cache Configuration
cache:
  enabled: true
  max_size: 1000
  default_ttl: 300  # 5 minutes
```

## Verifying Installation

Run this quick verification script:

```python
import sys
print(f"Python version: {sys.version}")

# Test imports
try:
    from pebblemind.config import Config
    print("✅ Config imported successfully")

    from pebblemind.cache import ResponseCache
    print("✅ Cache imported successfully")

    from pebblemind.utils.error_handler import ErrorHandler
    print("✅ Error handler imported successfully")

    from pebblemind.plugins import PluginManager
    print("✅ Plugin system imported successfully")

    print("\n🎉 PebbleMind core modules loaded successfully!")

except ImportError as e:
    print(f"❌ Import error: {e}")
```

Save as `verify.py` and run:
```bash
python verify.py
```

## Next Steps

1. **Explore the test suite** - See `tests/` for comprehensive examples
2. **Read the architecture** - Check `docs/` for detailed documentation
3. **Try the examples** - See `examples/` for real-world use cases
4. **Run benchmarks** - Test performance on your hardware

## Troubleshooting

### Common Issues

**1. Import errors for llama_cpp or sentence_transformers:**
```bash
# These are optional dependencies
# For testing, they're mocked - see test files for examples
pip install llama-cpp-python  # Heavy dependency ~500MB
pip install sentence-transformers  # Heavy dependency ~2GB
```

**2. Tests failing:**
```bash
# Ensure you're in a clean environment
pip install -e ".[dev]"
python -m pytest tests/ -v
```

**3. BLAS optimization:**
```bash
# macOS
brew install openblas

# Ubuntu/Debian
sudo apt-get install libopenblas-dev

# Then reinstall with BLAS support
CMAKE_ARGS="-DGGML_BLAS=ON" pip install llama-cpp-python --force-reinstall
```

## Getting Help

- **Documentation:** See `README.md` and `docs/`
- **Tests:** Check `tests/` for usage examples
- **Issues:** Report bugs on GitHub
- **Testing Report:** See `TESTING_REPORT.md` for quality metrics

## Success!

You now have PebbleMind set up and ready to use. Start exploring the codebase and building amazing AI applications! 🚀
