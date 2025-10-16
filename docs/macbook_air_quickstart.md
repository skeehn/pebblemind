# PebbleMind Quick Start Guide for MacBook Air

## Why PebbleMind on MacBook Air?

PebbleMind is specifically optimized for lightweight devices like MacBook Air, offering:
- World's smallest intelligent reasoning model
- No GPU dependency (runs on CPU only)
- Optimized for 8GB RAM systems
- High efficiency with minimal resource usage

## Installation

### Prerequisites
- macOS 10.15+ (Catalina or later)
- 8GB+ RAM (16GB recommended for multitasking)
- 4GB+ free disk space for models

### Install Dependencies
```bash
# Install system dependencies (macOS)
brew install llvm libomp openblas

# Install Python dependencies
pip install -e .
```

### Download Optimized Models
```bash
# Download models optimized for MacBook Air
bash scripts/download_models.sh

# Or download specific lightweight models
mkdir -p models
cd models

# Recommended: 1.5B model for optimal MacBook Air performance
# Available from: https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF
```

## Initial Setup

### Initialize Configuration
```bash
# Create optimized configuration for MacBook Air
pebblemind init

# The default config is already optimized for MacBook Air with:
# - 1.5B model (ultra-light)
# - Conservative thread usage 
# - Reduced context length
```

### First Run
```bash
# Test with the ultra-efficient 1.5B model
pebblemind status

# Start interactive chat (optimized for MacBook Air)
pebblemind chat --interactive
```

## MacBook Air Optimized Usage

### Recommended Commands
```bash
# Use ultra-light 1.5B model (default for MacBook Air)
pebblemind switch-model 1.5b

# Start interactive session
pebblemind chat --interactive

# Single query with efficiency
pebblemind chat "What are my options for reducing energy consumption?"

# Run API server optimized for MacBook Air
pebblemind serve
```

### Performance Optimization

#### Check System Status
```bash
# Monitor performance on MacBook Air
pebblemind status

# The system will show if you're using the optimal 1.5B model
```

#### Resource Management
- PebbleMind automatically manages memory for MacBook Air
- The 1.5B model typically uses 2-3GB RAM
- Conservative thread usage prevents thermal throttling

## Configuration for MacBook Air

The default configuration is already optimized, but you can customize:

```yaml
# pebblemind.yaml - MacBook Air optimized defaults
llm:
  model_size: "1.5b"  # Ultra-light, perfect for MacBook Air
  context_length: 2048  # Reduced for memory efficiency
  max_tokens: 256  # Conservative for speed
  threads: 4  # Conservative for thermal management
  batch_size: 256  # Reduced for memory
  enable_blas: true  # Essential for CPU performance
  enable_gpu_offload: false  # CPU-only for consistency

rag:
  max_results: 3  # Reduced for efficiency
  chunk_overlap: 32  # Reduced for efficiency

# Performance tip: These defaults are specifically tuned for MacBook Air
```

## Performance Expectations

### MacBook Air (M1/M2) with 1.5B Model:
- **Tokens/second**: 15-25 tokens/sec
- **Memory usage**: 2-3GB RAM
- **CPU usage**: 60-80% during generation
- **Thermal performance**: Minimal fan activity

### When to use larger models:
- Use 3B model for complex reasoning tasks
- Only consider 7B model if you have MacBook Pro with additional cooling

## Troubleshooting MacBook Air Issues

### If experiencing high CPU usage:
```bash
# Check if using 1.5B model
pebblemind status

# Switch back if needed
pebblemind switch-model 1.5b
```

### If running out of memory:
- Reduce the number of documents in RAG system
- Close other applications to free memory
- Stick with 1.5B model for daily use

### For best thermal performance:
- Ensure MacBook Air vents are not blocked
- Close other intensive applications
- Use the 1.5B model for regular tasks

## API Usage on MacBook Air

PebbleMind's API is also optimized:

```bash
# Start API server
pebblemind serve --host localhost --port 8000

# Example API call (uses MacBook Air optimized defaults)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "pebblemind-chat",
    "messages": [{"role": "user", "content": "How can I optimize my MacBook Air for performance?"}]
  }'
```

## Tips for MacBook Air Users

1. **Start with 1.5B model** - It's specifically optimized for your hardware
2. **Use during low-load periods** - For best thermal performance
3. **Monitor Activity Monitor** - Check memory and CPU usage
4. **Keep macOS updated** - For best thermal management
5. **Close other apps** - When doing intensive reasoning tasks

## Getting the Most Out of PebbleMind on MacBook Air

PebbleMind's efficiency optimizations mean you get:
- High-quality reasoning in a small package
- Consistent performance across all Mac hardware
- No need for expensive GPU upgrades
- Privacy-first processing (all local)
- World-class efficiency for lightweight devices

Enjoy your optimized AI experience on MacBook Air!