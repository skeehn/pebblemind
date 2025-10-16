# PebbleMind Efficiency Guide

## Overview

PebbleMind is designed to be the world's smallest intelligent reasoning model, optimized specifically for lightweight devices like MacBook Air. This guide details the efficiency optimizations that make PebbleMind run exceptionally well on resource-constrained hardware.

## Key Efficiency Features

### 1. Model Optimization

PebbleMind utilizes quantized models (Q4_K_M) which significantly reduce memory footprint while maintaining reasoning capabilities:

- **1.5B Model**: Ultra-light, optimized for MacBook Air and similar devices
- **3B Model**: Balanced quality/speed ratio
- **7B Model**: High quality with optional GPU offloading

The 1.5B model is specifically recommended for MacBook Air users due to its optimal performance-to-resource ratio.

### 2. CPU-Only Architecture

- No GPU dependency, ensuring consistent performance across all hardware
- BLAS acceleration for optimal CPU performance
- Conservative thread usage to prevent overheating on lightweight devices
- Memory mapping for efficient model loading

### 3. Memory Efficiency

- Reduced default context length (2048 tokens vs 4096)
- Conservative batch sizes (256 vs 512) to reduce memory pressure
- Automatic memory optimization with garbage collection
- Context truncation to prevent memory accumulation

### 4. MacBook Air Optimized Defaults

The default configuration is optimized for MacBook Air:

```yaml
# LLM Configuration optimized for MacBook Air
llm:
  model_size: "1.5b"  # Ultra-light, MacBook Air optimized
  context_length: 2048  # Reduced for memory efficiency
  max_tokens: 256  # Conservative limit for efficiency
  threads: -1  # Auto-detect optimal thread count (conservative for lightweight devices)
  batch_size: 256  # Reduced for memory efficiency
  enable_gpu_offload: false  # CPU-only by default for consistency
```

## Performance Recommendations

### For MacBook Air Users:

1. **Use the 1.5B model** for optimal performance
2. **Enable BLAS acceleration** for best CPU performance
3. **Limit context usage** to reduce memory consumption
4. **Monitor thermal performance** and adjust thread count if needed

### Switching to MacBook Air Optimized Settings:

```bash
# Switch to the ultra-light 1.5B model (recommended for MacBook Air)
pebblemind switch-model 1.5b

# Start with optimized settings
pebblemind init
```

## Intelligent Reasoning Capabilities

Despite its small size, PebbleMind includes advanced reasoning features:

- Chain of thought prompting
- Multi-step reasoning processes
- Context-aware responses
- Problem-solving frameworks

These are enabled by default to ensure high-quality reasoning output even on lightweight hardware.

## Performance Monitoring

PebbleMind includes built-in performance monitoring:

```bash
# Check current system status
pebblemind status

# Monitor performance over time
# Performance metrics are automatically tracked and optimized
```

## Configuration for Different Hardware

### MacBook Air (Recommended Settings):
```yaml
llm:
  model_size: "1.5b"
  context_length: 2048
  threads: 4  # Conservative for thermal management
```

### More Powerful MacBooks:
```yaml
llm:
  model_size: "3b"  # Or "7b" with GPU offloading
  context_length: 4096
  threads: -1  # Auto-detect
  enable_gpu_offload: true  # If GPU available
```

## Best Practices for Lightweight Devices

1. **Start with 1.5B model** - Best balance for MacBook Air
2. **Use RAG judiciously** - Limit context documents to maintain efficiency
3. **Monitor memory usage** - Use `pebblemind status` to check resource usage
4. **Optimize conversation length** - Shorter conversations use less memory
5. **Consider task complexity** - Very complex reasoning tasks may benefit from the 3B model

## Efficiency Metrics

PebbleMind automatically tracks and optimizes:

- Tokens per second (target: 15-25 on MacBook Air with 1.5B model)
- Memory usage (target: < 60% on 8GB systems)
- CPU utilization (balanced to prevent thermal throttling)
- Context management (automatic optimization)

## Troubleshooting on Lightweight Hardware

### If experiencing slowdown:
1. Switch to 1.5B model: `pebblemind switch-model 1.5b`
2. Reduce context length in configuration
3. Close other memory-intensive applications

### If running out of memory:
1. Use fewer context documents in RAG
2. Reduce conversation history
3. Ensure sufficient swap space

### For best MacBook Air performance:
1. Keep macOS updated for optimal thermal management
2. Ensure adequate ventilation
3. Use the 1.5B model for everyday tasks
4. Consider the 3B model for complex reasoning tasks only

## Continuous Efficiency Improvements

PebbleMind continuously optimizes for lightweight devices through:
- Automatic performance monitoring
- Dynamic context management
- Memory-efficient processing
- Conservative resource usage

The system learns from usage patterns to further optimize performance for your specific hardware over time.

---

*This documentation reflects PebbleMind's commitment to providing world-class AI capabilities on lightweight hardware without compromise.*