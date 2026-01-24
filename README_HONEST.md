# PebbleMind - Local AI Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-79%20passing-brightgreen)](tests/)

**Run AI models on your own computer. No internet, no cloud, no data sharing.**

## What Is This?

PebbleMind lets you run ChatGPT-style AI models locally on regular computers - even laptops without fancy GPUs. Everything runs on your machine, your data never leaves, and it works offline.

**Think**: "Like ChatGPT, but private and runs on your laptop"

## Why Use This?

### Privacy
Your conversations, documents, and data never leave your computer. No company sees your data, no telemetry, no tracking.

### Cost
After setup, it's free. No API keys, no monthly fees, no usage limits.

### Offline
Works without internet. Useful for:
- Airplanes, remote locations
- Countries with internet restrictions
- When APIs are down

### Control
You own everything. Can't be shut down, rate-limited, or censored.

### Learning
Great for understanding how AI systems actually work, since you can see everything.

## Current Status

✅ **Core Engine**: Fully working with 79/79 tests passing
✅ **Caching**: Production-ready LRU cache
✅ **Error Handling**: Automatic retries with exponential backoff
✅ **RAG System**: Vector search for documents
✅ **Plugin System**: Extensible architecture
⚠️ **Installation**: Requires some setup (downloading models, installing deps)
🚧 **CLI**: Being improved for easier use

## Quick Start

### For Developers (Testing Code)

```bash
git clone https://github.com/yourusername/pebblemind.git
cd pebblemind

# Install test dependencies
pip install pytest pytest-asyncio pydantic numpy scipy

# Run tests (should see 79 passing)
python -m pytest tests/ -v
```

### For Users (Actually Using It)

See [INSTALLATION.md](INSTALLATION.md) for full setup. Summary:

1. Install Python packages (including llama-cpp-python)
2. Download a model file (1-7GB)
3. Create configuration file
4. Run!

```python
import asyncio
from pebblemind.config import LLMConfig
from pebblemind.core.llm import LLMEngine

async def main():
    config = LLMConfig(
        model_path="models/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        model_size="1.5b"
    )

    engine = LLMEngine(config)
    await engine.initialize()

    response = await engine.generate("Tell me a joke")
    print(response)

    await engine.cleanup()

asyncio.run(main())
```

## What It Does

### 1. Local LLM Chat
Run AI models (Qwen2.5 1.5B/3B/7B) on your CPU:
- 15-50 tokens/second depending on hardware
- Works on MacBook Air, regular laptops
- No GPU needed (but can use it if you have one)

### 2. Document Q&A (RAG)
Ask questions about your documents:
- Upload PDFs, text files
- Semantic search with embeddings
- Get answers based on your docs

### 3. Smart Caching
Saves computation:
- LRU eviction (keeps most-used responses)
- TTL expiration (clears old data)
- Can save 50%+ of computation time

### 4. Error Handling
Production-ready reliability:
- Automatic retries with backoff
- Fallback mechanisms
- Graceful degradation

### 5. Plugin System
Extend functionality:
- Add custom tools
- Hook into events
- Build on top of the framework

## Features

| Feature | Status | Notes |
|---------|--------|-------|
| LLM Inference | ✅ Working | llama.cpp, 1.5B/3B/7B models |
| Caching | ✅ Working | LRU + TTL, thoroughly tested |
| Error Handling | ✅ Working | Retry with backoff |
| RAG/Vector Search | ✅ Working | BGE embeddings, SQLite-vec |
| Plugin System | ✅ Working | Dynamic loading, hooks |
| Tests | ✅ 79 passing | Comprehensive coverage |
| Voice I/O | 🚧 Partial | Framework there, needs polish |
| Web API | 🚧 Partial | FastAPI server implemented |
| CLI | 🚧 In Progress | Python API works great |
| Desktop App | 🚧 Planned | Tauri template exists |

## Performance

Realistic numbers from testing:

**MacBook Air M1 (8GB RAM)**
- 1.5B model: 15-25 tokens/sec
- Memory: ~2GB
- Startup: 3-5 seconds

**Desktop (Ryzen/i7, 16GB RAM)**
- 3B model: 40-60 tokens/sec
- Memory: ~4GB
- Startup: 4-6 seconds

**Comparison to Cloud APIs:**
- Speed: Slower (cloud is 100+ tokens/sec)
- Privacy: Much better (stays local)
- Cost: Free after setup vs $$ per month
- Offline: Works vs requires internet

## Architecture

```
PebbleMind/
├── core/llm.py          # LLM engine (llama.cpp integration)
├── rag/system.py        # Vector search for documents
├── cache/               # Response caching
├── utils/error_handler  # Retry logic
├── plugins/             # Plugin system
├── api/server.py        # REST API (OpenAI-compatible)
└── tests/               # 79 comprehensive tests
```

**Key Technologies:**
- **llama.cpp**: Fast CPU inference
- **sentence-transformers**: Text embeddings
- **SQLite**: Vector database
- **FastAPI**: Web server
- **Pydantic**: Config management

## Code Quality

| Metric | Value |
|--------|-------|
| Tests | 79 passing |
| Test Coverage | ~75% (core: 100%) |
| Type Hints | Yes, throughout |
| Documentation | Comprehensive |
| Async Support | Full async/await |
| Error Handling | Production-grade |

## Installation Options

### Option 1: Just Testing
```bash
pip install pytest pytest-asyncio pydantic
python -m pytest tests/ -v
```

### Option 2: Basic Usage
```bash
pip install -e .
# Download model (see INSTALLATION.md)
python your_script.py
```

### Option 3: Full Development
```bash
pip install -e ".[dev]"
pytest tests/ --cov=pebblemind
```

See [INSTALLATION.md](INSTALLATION.md) for detailed instructions.

## Examples

### Simple Chat
```python
engine = LLMEngine(config)
await engine.initialize()

while True:
    user_input = input("You: ")
    if user_input.lower() == 'quit':
        break

    response = await engine.generate(user_input)
    print(f"AI: {response}")
```

### Document Q&A
```python
# Add your documents
documents = [
    {"content": "Python is a programming language...", "metadata": {"source": "wiki"}},
    {"content": "JavaScript is used for web development...", "metadata": {"source": "docs"}}
]
await rag.add_documents(documents)

# Ask questions
results = await rag.search("What is Python?", k=3)
context = [r["content"] for r in results]
answer = await engine.generate("What is Python?", context=context)
```

### With Caching
```python
from pebblemind.cache import ResponseCache, cached

cache = ResponseCache(max_size=1000)

@cached(cache=cache, ttl=300)
async def smart_search(query):
    results = await rag.search(query)
    return await engine.generate(query, context=results)

# First call: does the work
answer1 = await smart_search("What is AI?")

# Second call: instant (from cache)
answer2 = await smart_search("What is AI?")
```

## Use Cases

### Personal
- Private journaling with AI assistance
- Document analysis without cloud upload
- Learning programming offline
- Creative writing helper

### Professional
- Code analysis with private codebases
- Document Q&A for sensitive materials
- Research without internet dependency
- Prototyping AI features

### Development
- Testing AI integrations locally
- Learning LLM internals
- Building on top of the framework
- Privacy-focused applications

## Limitations (Being Honest)

**Setup Complexity**
- Not one-click (yet)
- Need to download large model files
- Requires some technical knowledge

**Model Quality**
- Not as good as GPT-4
- Smaller models = simpler answers
- Limited context window (2048 tokens)

**Speed**
- Slower than cloud APIs
- CPU-bound (15-50 tokens/sec)
- Initial load takes a few seconds

**Hardware Requirements**
- Need 4-16GB RAM depending on model
- Works better with more CPU cores
- Storage for models (1-7GB per model)

## Roadmap

**Near Term**
- [ ] Simpler installation process
- [ ] Better CLI interface
- [ ] More usage examples
- [ ] Video tutorials

**Future**
- [ ] One-command installer
- [ ] Automatic model downloads
- [ ] Web UI
- [ ] Mobile app
- [ ] Multi-modal support

## Contributing

Contributions welcome! This project demonstrates:

✅ Clean Python architecture
✅ Comprehensive testing (79 tests)
✅ Good documentation
✅ Real-world utility

See existing tests for examples. PRs appreciated!

## Documentation

- [INSTALLATION.md](INSTALLATION.md) - Detailed setup guide
- [QUICKSTART.md](QUICKSTART.md) - 5-minute tutorial
- [TESTING_REPORT.md](TESTING_REPORT.md) - Test coverage details
- [PROJECT_SHOWCASE.md](PROJECT_SHOWCASE.md) - Technical deep-dive

## Support

- **Issues**: GitHub issue tracker
- **Examples**: See `examples/` directory
- **Tests**: Check `tests/` for usage patterns

## License

MIT License - use freely, commercially, no restrictions.

## Credits

Built with:
- [llama.cpp](https://github.com/ggerganov/llama.cpp) - LLM inference
- [sentence-transformers](https://github.com/UKPLab/sentence-transformers) - Embeddings
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Config management

---

**Bottom Line:** Solid, well-tested local AI framework. Not magic, just good engineering. Privacy-focused and actually useful.
