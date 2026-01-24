# Installation Guide

## What This Project Does

PebbleMind lets you run AI chat models on your own computer - **no internet required, no data sent anywhere**. Once set up, it's like having ChatGPT running entirely on your machine.

Think of it as: *"Your own private ChatGPT that runs offline"*

### Why This Matters

1. **Privacy**: Your conversations never leave your computer
2. **Cost**: No API fees once you have the models
3. **Offline**: Works without internet
4. **Control**: You own everything, no service can shut you down
5. **Learning**: Great for understanding how AI systems work

### Current Status

✅ **Working:** Core code, caching, error handling, plugins, RAG, testing
⚠️ **Setup Required:** Model downloads, dependency installation
🚧 **In Progress:** Simpler installation process

---

## Quick Install (For Testing)

Want to try the code without the full AI models? This works for testing:

```bash
# 1. Clone and enter directory
git clone https://github.com/yourusername/pebblemind.git
cd pebblemind

# 2. Install for testing (without heavy ML dependencies)
pip install pytest pytest-asyncio pydantic pyyaml click rich numpy scipy

# 3. Run tests to verify everything works
python -m pytest tests/ -v

# You should see: 79 passed in ~5 seconds ✅
```

This verifies the code works, but won't actually run AI models yet.

---

## Full Install (For Actually Using It)

This lets you actually chat with AI models locally.

### Step 1: Install Python Packages

```bash
# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install PebbleMind
pip install -e .
```

**Note:** This will try to compile `llama-cpp-python` which needs a C++ compiler.

#### If llama-cpp-python install fails:

**On macOS:**
```bash
brew install cmake
pip install llama-cpp-python
```

**On Ubuntu/Debian:**
```bash
sudo apt-get install build-essential cmake
pip install llama-cpp-python
```

**On Windows:**
- Install Visual Studio Build Tools
- Or use pre-built wheels: `pip install llama-cpp-python --prefer-binary`

### Step 2: Download AI Models

You need model files (GGUF format). These are large:

**Option A: Quick Start (1.5GB model - recommended)**
```bash
mkdir -p models
cd models

# Download Qwen2.5-1.5B (small, fast, good for testing)
wget https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf

cd ..
```

**Option B: Better Quality (3GB model)**
```bash
# Download Qwen2.5-3B (balanced quality/speed)
wget https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf
```

**Option C: Best Quality (7GB model)**
```bash
# Download Qwen2.5-7B (slower but higher quality)
wget https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf
```

### Step 3: Configure

Create a `pebblemind.yaml` file:

```yaml
llm:
  model_size: "1.5b"  # Match the model you downloaded
  model_path: "models/qwen2.5-1.5b-instruct-q4_k_m.gguf"
  context_length: 2048
  max_tokens: 256
  threads: 4  # Adjust based on your CPU
  enable_blas: true
```

### Step 4: Try It Out

```bash
# Test that everything works
python -c "from pebblemind.core.llm import LLMEngine; print('✅ Ready!')"
```

**Note:** The full interactive CLI (`pebblemind chat`) is still being finalized. For now, you can use the Python API directly (see examples below).

---

## Using It

### Basic Python Usage

```python
import asyncio
from pebblemind.config import LLMConfig
from pebblemind.core.llm import LLMEngine

async def chat():
    config = LLMConfig(
        model_path="models/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        model_size="1.5b",
        context_length=2048
    )

    engine = LLMEngine(config)
    await engine.initialize()

    # Chat!
    response = await engine.generate("Hello! Tell me a joke.")
    print(response)

    await engine.cleanup()

asyncio.run(chat())
```

### What You Can Build

With the working components:

1. **Simple Chatbot**
   ```python
   while True:
       user_input = input("You: ")
       response = await engine.generate(user_input)
       print(f"AI: {response}")
   ```

2. **Document Q&A** (using RAG)
   ```python
   # Add your documents
   await rag.add_documents(documents)

   # Ask questions about them
   results = await rag.search("What does the document say about X?")
   ```

3. **Cached Responses** (save computation)
   ```python
   @cached(cache=cache, ttl=300)
   async def smart_search(query):
       results = await rag.search(query)
       response = await engine.generate(query, context=results)
       return response
   ```

---

## What Makes This Different

Here's what PebbleMind actually brings to the table (no hype):

### 1. **Privacy-First Design**
Most AI tools send your data to servers. This keeps everything local. Useful if you're:
- Working with sensitive data
- In a country with internet restrictions
- Want to learn without being tracked

### 2. **Production-Ready Code**
Unlike many AI demos, this has:
- Real error handling (with automatic retries)
- Proper caching (LRU + TTL)
- Comprehensive tests (79 passing)
- Clean architecture you can actually maintain

### 3. **Optimized for Regular Computers**
Specifically tuned for running on:
- MacBook Air (yes, even the fanless one)
- Regular laptops without GPUs
- Consumer desktops
- Servers without expensive hardware

### 4. **Actually Extensible**
The plugin system isn't just for show - you can genuinely:
- Add custom tools
- Modify behavior with hooks
- Build on top of it

### 5. **Real RAG System**
Retrieval-Augmented Generation that actually works:
- Uses proper embeddings (BGE-small)
- Vector database (SQLite-vec)
- Handles document chunking smartly

---

## Limitations (Being Honest)

1. **Initial Setup**: Not one-click yet. You need to download models and install deps
2. **Model Quality**: Local models aren't as good as GPT-4 (but getting close!)
3. **Speed**: 15-50 tokens/sec depending on hardware (slower than cloud APIs)
4. **RAM**: Needs 4-16GB depending on model size
5. **CLI**: Still being polished - Python API works great though

---

## Troubleshooting

### "llama-cpp-python won't install"
Try pre-built wheels:
```bash
pip install llama-cpp-python --prefer-binary
```

### "Out of memory"
Use the smaller 1.5B model, or reduce context length:
```yaml
llm:
  context_length: 1024  # Instead of 2048
```

### "It's slow"
1. Use the 1.5B model
2. Enable BLAS: `enable_blas: true`
3. Reduce `max_tokens: 128`

### "Model file not found"
Make sure the path in `pebblemind.yaml` matches where you downloaded it:
```bash
ls -lh models/*.gguf  # Should show your model file
```

---

## For Developers

Want to contribute or build on this?

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=pebblemind --cov-report=html
```

See `PROJECT_SHOWCASE.md` for the full technical overview.

---

## What's Next

Working on:
- [ ] One-command installer
- [ ] Better CLI interface
- [ ] Automatic model downloads
- [ ] Web UI
- [ ] More examples

---

## Questions?

**"Can I actually use this?"**
Yes, but expect some setup. The code is solid, the install process is being simplified.

**"Is it better than ChatGPT?"**
No, but it's private and free to run. Different use case.

**"Why would I use this?"**
Privacy, learning, offline access, no API costs, full control.

**"Is this production-ready?"**
The core code? Yes (79 tests passing). The end-user experience? Getting there.

---

## Support

- Issues: GitHub issue tracker
- Docs: This directory
- Tests: See `tests/` for usage examples
- Examples: See `examples/` for code samples

---

Built to be useful, not just impressive. Contributions welcome! 🚀
