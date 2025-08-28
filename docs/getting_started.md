# Getting Started with PebbleMind

Welcome to PebbleMind! This guide will help you get up and running with your CPU-first local AI assistant.

## 🚀 Quick Start

### 1. System Requirements

- **Python**: 3.9 or higher
- **RAM**: Minimum 4GB (8GB+ recommended)
- **Storage**: 2GB+ for models and data
- **OS**: Linux, macOS, or Windows

### 2. Installation

#### Option A: Automated Setup (Recommended)

```bash
# Clone repository
git clone https://github.com/yourusername/pebblemind.git
cd pebblemind

# Run complete setup
./scripts/setup.sh
```

#### Option B: Manual Installation

```bash
# Install Python dependencies
pip install -e .

# Install system dependencies
# Linux
sudo apt-get install build-essential cmake libopenblas-dev libomp-dev

# macOS
brew install llvm libomp openblas cmake

# Install BLAS-accelerated llama-cpp
CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS" pip install llama-cpp-python
```

### 3. Download Models

```bash
# Download all required models
./scripts/download_models.sh

# Or download individually
huggingface-cli download BAAI/bge-small-en-v1.5 --local-dir models/bge-small-en-v1.5
wget https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf -O models/qwen2.5-1.5b-instruct-q4_k_m.gguf
```

### 4. Configuration

Edit `pebblemind.yaml` to set correct model paths:

```yaml
llm:
  model_path: "models/qwen2.5-1.5b-instruct-q4_k_m.gguf"

rag:
  embedding_model: "BAAI/bge-small-en-v1.5"
```

### 5. Test Installation

```bash
# Check system status
pebblemind status

# Run basic test
pebblemind chat "Hello, PebbleMind!"

# Start interactive chat
pebblemind chat --interactive
```

## 🎯 Core Features

### Chat Interface

```bash
# Simple query
pebblemind chat "What is artificial intelligence?"

# Interactive mode
pebblemind chat --interactive

# With custom config
pebblemind --config my_config.yaml chat "Hello!"
```

### Voice Processing

```bash
# Transcribe audio
pebblemind transcribe recording.wav

# Text to speech
pebblemind speak "Hello world" --output hello.wav
```

### Document Indexing

```bash
# Add documents to knowledge base
pebblemind add-docs documents/ --recursive

# Check RAG statistics
pebblemind stats
```

### API Server

```bash
# Start OpenAI-compatible API
pebblemind serve

# Test API
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "pebblemind-chat", "messages": [{"role": "user", "content": "Hello!"}]}'
```

## 🔧 Performance Tuning

### Memory Optimization

```bash
# Reduce context for lower memory usage
export GGML_CTX_SIZE=2048

# Use smaller batch sizes
export GGML_N_BATCH=256
```

### CPU Optimization

```bash
# Set optimal thread count
export OMP_NUM_THREADS=$(nproc)
export OPENBLAS_NUM_THREADS=$(nproc)
```

### Model Selection

- **Qwen2.5-1.5B Q4_K_M**: Balanced quality/speed (recommended)
- **Qwen2.5-1.5B Q3_K_L**: Faster, lower quality
- **Qwen2.5-1.5B Q5_K_M**: Higher quality, slower

## 🧪 Benchmarking

```bash
# Run performance benchmarks
python scripts/benchmark.py

# Custom benchmark with config
python scripts/benchmark.py --config my_config.yaml --iterations 10
```

## 🐛 Troubleshooting

### Common Issues

1. **BLAS not found**
   ```bash
   # Reinstall with BLAS support
   pip uninstall llama-cpp-python
   CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS" pip install llama-cpp-python
   ```

2. **Model loading fails**
   ```bash
   # Check model path
   ls -la models/
   # Verify file integrity
   file models/qwen2.5-1.5b-instruct-q4_k_m.gguf
   ```

3. **Memory issues**
   ```bash
   # Reduce context size
   pebblemind --config <(echo 'llm: {context_length: 2048}') chat "test"
   ```

4. **Voice processing fails**
   ```bash
   # Check voice models
   ls -la models/ggml-base.en.bin
   ls -la models/en_US-amy-low.onnx
   ```

### Debug Mode

```bash
# Enable verbose logging
pebblemind --verbose status

# Check detailed logs
tail -f cache/pebblemind.log
```

## 📚 Next Steps

- 📖 Read the [full documentation](README.md)
- 🚀 Try the [examples](examples/)
- ⚡ Run [performance benchmarks](scripts/benchmark.py)
- 🤝 Join our [community](https://github.com/yourusername/pebblemind/discussions)

## 🎉 You're Ready!

PebbleMind is now ready to assist you with:
- ✅ Local AI conversations
- ✅ Document analysis and Q&A
- ✅ Voice input/output
- ✅ OpenAI-compatible API
- ✅ Privacy-first operation

Enjoy your CPU-powered AI assistant! 🤖✨
