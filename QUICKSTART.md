# PebbleMind Quick Start

Get PebbleMind running in **under 10 minutes**.

## One-Line Install (macOS/Linux)

```bash
curl -fsSL https://raw.githubusercontent.com/yourusername/pebblemind/main/install.sh | bash
```

Or clone and run:

```bash
git clone https://github.com/yourusername/pebblemind.git
cd pebblemind
./install.sh
```

The installer will:
- ✅ Create Python virtual environment
- ✅ Install dependencies
- ✅ Download default model (Qwen 2.5 1.5B, ~1GB)
- ✅ Set up `pebblemind` command
- ✅ Run health check

## First Chat

```bash
# One-shot question
pebblemind chat "What is machine learning?"

# Interactive mode
pebblemind chat --interactive
```

## Check System

```bash
# Health check
pebblemind doctor

# Show configuration
pebblemind config show

# System status
pebblemind status
```

## Configure Model

If you didn't download the default model or want to use a different one:

```bash
# Set model path
pebblemind config set llm.model_path /path/to/model.gguf

# Adjust model parameters
pebblemind config set llm.temperature 0.7
pebblemind config set llm.max_tokens 512
```

### Recommended Models

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| [Qwen2.5-1.5B](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF) | 1GB | ⚡⚡⚡ | ⭐⭐ | Quick responses, testing |
| [Qwen2.5-7B](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF) | 4GB | ⚡⚡ | ⭐⭐⭐⭐ | Default, balanced |
| [Llama-3-8B](https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct-GGUF) | 5GB | ⚡⚡ | ⭐⭐⭐⭐ | General purpose |
| [Mistral-7B](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3-GGUF) | 4GB | ⚡⚡ | ⭐⭐⭐⭐ | Coding, reasoning |

Download with:
```bash
# Example: Download Qwen 7B
curl -L -o ~/.pebblemind/models/qwen2.5-7b-q4.gguf \
  https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf

# Set it as active model
pebblemind config set llm.model_path ~/.pebblemind/models/qwen2.5-7b-q4.gguf
```

## Add Documents (RAG)

```bash
# Add a single document
pebblemind add-docs ~/Documents/report.pdf

# Add multiple files
pebblemind add-docs ~/Documents/*.txt

# Add directory recursively
pebblemind add-docs -r ~/Documents/project

# Check RAG stats
pebblemind stats
```

Then ask questions about your documents:
```bash
pebblemind chat "What does the Q3 report say about revenue?"
```

## Voice Commands

```bash
# Transcribe audio to text
pebblemind transcribe audio.wav

# Convert text to speech
pebblemind speak "Hello world" --output greeting.wav
```

## Start API Server

```bash
# Start server (default: http://localhost:8000)
pebblemind serve

# In another terminal, test it:
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}]}'
```

## Desktop App (Optional)

If you want the GUI instead of CLI:

```bash
cd ~/pebblemind/desktop
npm install
npm run tauri dev
```

## Troubleshooting

### Command not found: pebblemind

Add to your PATH:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### llama-cpp-python install fails

Install build tools:

**macOS:**
```bash
xcode-select --install
brew install cmake
```

**Linux:**
```bash
sudo apt install build-essential cmake python3-dev
```

Then reinstall:
```bash
pip install --upgrade --force-reinstall llama-cpp-python
```

### Model not loading

Check the path:
```bash
pebblemind doctor
ls -lh ~/.pebblemind/models/
```

Verify the file is a valid GGUF model:
```bash
file ~/.pebblemind/models/*.gguf
```

### Slow responses

Try a smaller model or adjust GPU layers:
```bash
# Increase GPU offload (if you have Metal/CUDA)
pebblemind config set llm.gpu_layers 32

# Use smaller model
pebblemind config set llm.model_size 1.5b
```

### Still stuck?

```bash
# Run comprehensive health check
pebblemind doctor

# Check logs
tail -f ~/.pebblemind/logs/pebblemind.log

# Get help
pebblemind --help
```

## Next Steps

- **[README.md](README.md)** - Full documentation
- **[INSTALLATION.md](INSTALLATION.md)** - Detailed setup
- **[docs/](docs/)** - Architecture, API reference, guides

## What Makes PebbleMind Different?

- 🔒 **100% Private** - Your data never leaves your machine
- ⚡ **Fast** - 2-5s responses on M1 Macs with 7B models
- 💰 **Zero Cost** - No API keys, no subscriptions
- 🌐 **Offline** - Works without internet
- 🔧 **Hackable** - Python codebase, easy to extend
- 🧪 **Production-Ready** - 142 passing tests, security hardened

## Support

- **GitHub Issues**: Report bugs, request features
- **Discussions**: Ask questions, share tips
- **Discord**: Join the community (coming soon)

---

**Ready to dive deeper?** Check out [README.md](README.md) for advanced features and customization.
