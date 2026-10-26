# PebbleMind - Local AI Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/skeehn/pebblemind/actions/workflows/ci.yml/badge.svg)](https://github.com/skeehn/pebblemind/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-152%20passing-brightgreen)](tests/)

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

✅ **Core Engine**: Fully working with 152/152 tests passing (incl. 7 real end-to-end robust tests)
✅ **Caching**: Production-ready LRU cache
✅ **Error Handling**: Automatic retries with exponential backoff
✅ **RAG System**: Vector search for documents
✅ **Plugin System**: Extensible architecture
✅ **MCP**: Expose PebbleMind over Model Context Protocol (`pebblemind mcp serve`) + call external MCP servers
✅ **Web Access**: Optional `web_search` / `web_fetch` tools (httpx, no API keys)
✅ **Multi-backend**: Ollama, llama.cpp (Metal), HuggingFace — auto-selected per machine
🚧 **Desktop App**: Tauri template exists, needs polish

## Quick Start

### For Developers (Testing Code)

```bash
git clone https://github.com/skeehn/pebblemind.git
cd pebblemind

# Install test dependencies
pip install pytest pytest-asyncio pydantic numpy scipy

# Run tests (should see 142 passing)
python -m pytest tests/ -v
```

### For Users (Actually Using It)

See [INSTALLATION.md](INSTALLATION.md) for full setup. Summary:

1. Install Python packages (including llama-cpp-python)
2. Download a model file (1-7GB)
3. Create configuration file
4. Run!

> **Python version:** `llama-cpp-python` ships prebuilt wheels for Python
> 3.10–3.12. On 3.13+, pip builds it from source, which needs a C/C++ toolchain
> (`cmake` + a compiler) — if the install fails, use Python 3.10–3.12 (or install
> the build tools first). The pure-Python core (CLI, RAG, cache, tests) runs on
> any 3.10+ without llama-cpp.

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

## ✨ Features

- 🔒 **100% Private** - Everything runs locally, no data leaves your machine
- ⚡ **Fast** - Optimized inference with llama.cpp (2-5s responses on M1)
- 🧠 **RAG System** - Add documents and get context-aware answers
- 🎙️ **Voice Interface** - Speak to your AI and hear responses (Whisper + TTS)
- 🤖 **Multi-Agent** - Orchestrate specialized agents for complex tasks
- 💾 **Model Management** - Built-in catalog with one-command downloads
- 🖥️ **Desktop App** - Beautiful Tauri-based UI (optional)
- 🌐 **API Server** - OpenAI-compatible HTTP API
- 🔧 **Extensible** - Python source, easy to hack and customize

## 🚀 Quick Start

### One-Line Install (macOS/Linux)

```bash
curl -fsSL https://raw.githubusercontent.com/skeehn/pebblemind/main/install.sh | bash
```

Or clone and install manually:

```bash
git clone https://github.com/skeehn/pebblemind.git
cd pebblemind
./install.sh
```

### Your First Chat

```bash
# One-shot question
pebblemind chat "What is the capital of France?"

# Interactive chat session
pebblemind chat

# Check system health
pebblemind doctor

# Browse and install models
pebblemind models recommend          # Get a recommendation
pebblemind models list --catalog     # Browse all models
pebblemind models install qwen2.5-7b-q4
```

Full guide: [QUICKSTART.md](QUICKSTART.md)

## 🔌 MCP (Model Context Protocol)

PebbleMind speaks MCP both ways — the standard protocol for connecting AI assistants to tools in 2026 (Claude Desktop, Cursor, editors, agents):

**Serve PebbleMind over MCP** (any MCP client can use your local model):

```bash
pebblemind mcp serve
```

Exposed tools: `chat`, `ask_documents`, `add_documents`, `get_status` + the `pebblemind://status` resource. Example Claude Desktop config:

```json
{
  "mcpServers": {
    "pebblemind": {"command": "pebblemind", "args": ["mcp", "serve"]}
  }
}
```

**Use external MCP servers** — add them to `pebblemind.yaml` and their tools become available to your local model automatically:

```yaml
mcp:
  servers:
    filesystem:
      command: ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    websearch:
      url: "http://localhost:8080/mcp"

tools:
  web_access: true   # built-in web_search / web_fetch (httpx, no API keys)
```

```bash
pebblemind mcp list   # inspect tools of configured servers
```

## 📦 Model Management

PebbleMind includes a built-in model catalog with one-command downloads:

```bash
# Get recommendation based on your RAM
pebblemind models recommend

# Browse available models
pebblemind models list --catalog

# Install a model
pebblemind models install qwen2.5-7b-q4

# View model details
pebblemind models info mistral-7b-q4

# List installed models
pebblemind models list
```

**Available Models:**
- **Qwen 2.5 1.5B** (1GB) - Fast, lightweight
- **Qwen 2.5 7B** (4.4GB) - Balanced (recommended)
- **Llama 3 8B** (4.7GB) - General purpose
- **Mistral 7B** (4.4GB) - Excellent for coding

All models are quantized (Q4) for optimal size/quality balance.

## 📋 Features

| Feature | Status | Notes |
|---------|--------|-------|
| LLM Inference | ✅ Working | Ollama / llama.cpp(Metal) / HuggingFace backends |
| Caching | ✅ Working | LRU + TTL, concurrency-tested |
| Error Handling | ✅ Working | Retry with backoff |
| RAG/Vector Search | ✅ Working | BGE embeddings, SQLite-vec, hash fallback |
| Plugin System | ✅ Working | Dynamic loading, hooks |
| MCP Server | ✅ Working | `pebblemind mcp serve` (stdio JSON-RPC) |
| MCP Client | ✅ Working | Call external MCP servers, tools auto-registered |
| Web Access | ✅ Working | Opt-in web_search / web_fetch |
| Tests | ✅ 152 passing | + 7 real-model robust tests (Oct 2026) |
| Voice I/O | 🚧 Partial | Framework there, needs polish |
| CLI | ✅ Working | chat, doctor, models, mcp, config, serve |
| Desktop App | 🚧 Planned | Tauri template exists |

## Performance (October 2026, Apple M3 8-core, 16GB RAM, measured)

Benchmarks run against the **same Qwen2.5 GGUF weights** in both engines:

| Path | Qwen2.5-1.5B | Qwen2.5-7B | Notes |
|------|--------------|------------|-------|
| Raw Ollama 0.40 (Metal) | 70.7 tok/s | 18.6 tok/s | engine-level |
| PebbleMind llama.cpp backend (Metal, full offload) | 65.5 tok/s | 12.8 tok/s | ~93% of Ollama at 1.5B |
| PebbleMind 1.5B CPU-only | 23.8 tok/s | — | no Metal needed |
| PebbleMind full pipeline (Ollama backend) | ~51 words/s | — | RAG+memory+tools overhead ~15% |

- TTFT: 0.12s (1.5B Metal) / 0.19s (Ollama); model init 0.2–3.9s
- On Mac, **both** paths are Metal-accelerated; llama-cpp-python now has no prebuilt macOS wheels, so PebbleMind builds it from source with `METAL=1` (the installer handles this).
- Honest take: for 7B+ models prefer the Ollama backend; for 0.5B–3B the bundled llama.cpp is within ~8% of Ollama.

### Real-world retrieval quality (October 2026 robust test suite)

- RAG top-3 hit rate with real BGE-small embeddings: **7/8** questions
- Concurrent safety: 6 parallel generations on one engine — queued, correct, no corruption
- MCP round-trip: chat + document Q&A over the protocol with the real model

## Architecture

```
PebbleMind/
├── core/llm.py          # LLM engine (multi-backend)
├── core/backends.py     # Ollama/llama.cpp/HF transports + model catalog
├── rag/system.py        # Vector search for documents
├── cache/               # Response caching
├── mcp_server.py        # MCP server (expose PebbleMind over MCP)
├── mcp_client.py        # MCP client (call external MCP servers)
├── web_tools.py         # web_search / web_fetch (opt-in)
├── api/server.py        # REST API (OpenAI-compatible)
└── tests/               # 152 comprehensive tests
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
| Tests | 142 passing |
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
- [HOW_IT_WORKS.md](HOW_IT_WORKS.md) - Architecture & technical deep-dive
- [SECURITY.md](SECURITY.md) - Security model

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
