# Groq Backend Integration

PebbleMind now supports **Groq's ultra-fast cloud API** as an alternative to local llama.cpp inference!

## Overview

Groq provides blazing-fast LLM inference using specialized LPU (Language Processing Unit) hardware, offering:

- ⚡ **Ultra-fast inference** - Up to 10x faster than traditional GPUs
- 🚀 **High throughput** - Handle more requests per second
- 🌐 **Cloud-based** - No local model downloads required
- 🔄 **Streaming support** - Real-time response generation
- 🎯 **Multiple models** - Access to Llama, Mixtral, and Gemma models

## Quick Start

### 1. Get Groq API Key

Sign up at [https://console.groq.com/](https://console.groq.com/) and get your API key.

### 2. Set Environment Variable

```bash
export GROQ_API_KEY="your_api_key_here"
```

### 3. Use Groq Backend

```python
from pebblemind.backends import GroqLLMBackend

# Initialize Groq backend
backend = GroqLLMBackend()

# Generate text
response = await backend.generate("Explain quantum computing")
print(response)

# Stream responses
async for chunk in backend.generate_stream("Write a story"):
    print(chunk, end="", flush=True)

# Clean up
await backend.close()
```

## Available Models

| Model | Context | Speed | Best For |
|-------|---------|-------|----------|
| `llama-3.1-70b-versatile` | 131K | ⚡⚡⚡ | General tasks, reasoning |
| `llama-3.1-8b-instant` | 131K | ⚡⚡⚡⚡ | Quick responses, simple tasks |
| `llama-3.2-90b-vision-preview` | 8K | ⚡⚡ | Vision tasks (preview) |
| `mixtral-8x7b-32768` | 33K | ⚡⚡⚡ | Complex reasoning |
| `gemma2-9b-it` | 8K | ⚡⚡⚡ | Balanced performance |

### Selecting a Model

```python
# Use ultra-fast 8B model
backend = GroqLLMBackend(model="llama-3.1-8b-instant")

# Use powerful 70B model (default)
backend = GroqLLMBackend(model="llama-3.1-70b-versatile")

# Use Mixtral
backend = GroqLLMBackend(model="mixtral-8x7b-32768")
```

## Configuration

### Via Config File

Update `pebblemind.yaml`:

```yaml
llm:
  backend: "groq"  # Use Groq instead of local

groq:
  api_key: null  # Or set GROQ_API_KEY env var
  model: "llama-3.1-70b-versatile"
  base_url: "https://api.groq.com/openai/v1"
  timeout: 30.0
```

### Via Code

```python
from pebblemind.backends import GroqLLMBackend

backend = GroqLLMBackend(
    api_key="your_key",  # Or use GROQ_API_KEY env var
    model="llama-3.1-70b-versatile"
)
```

## Features

### 1. Basic Generation

```python
response = await backend.generate(
    prompt="What is machine learning?",
    max_tokens=200,
    temperature=0.7,
    top_p=0.9
)
```

### 2. Streaming

```python
async for chunk in backend.generate_stream(
    prompt="Write a technical blog post intro",
    max_tokens=300
):
    print(chunk, end="", flush=True)
```

### 3. System Prompts

```python
response = await backend.generate(
    prompt="Explain recursion",
    system_prompt="You are a computer science professor. Explain clearly.",
    max_tokens=200
)
```

### 4. Parameter Control

```python
# Creative writing (high temperature)
creative = await backend.generate(
    prompt="Write a poem",
    temperature=1.0,
    max_tokens=150
)

# Factual answers (low temperature)
factual = await backend.generate(
    prompt="What is the capital of France?",
    temperature=0.0,
    max_tokens=20
)
```

## Testing

### Basic Test

```bash
export GROQ_API_KEY="your_key"
python scripts/test_groq_backend.py
```

### Comprehensive Test

Run full integration test with agents and benchmarks:

```bash
python scripts/comprehensive_test.py
```

This tests:
- ✅ Basic generation
- ✅ Streaming
- ✅ Multiple models
- ✅ Specialized agents
- ✅ Performance benchmarks
- ✅ Concurrent requests

## Performance Benchmarks

Typical performance with Groq (llama-3.1-70b-versatile):

| Metric | Value |
|--------|-------|
| Average inference time | 0.3-0.8s |
| Tokens per second | 100-300+ |
| Throughput | 2-5 req/sec |
| Time to first token | 50-150ms |
| Streaming chunks | Real-time |

**Note:** Performance varies by model, prompt length, and API load.

## Use Cases

### 1. Development & Testing

Use Groq for fast iteration during development:

```python
# Quick prototyping without local model downloads
backend = GroqLLMBackend()
response = await backend.generate("Test prompt")
```

### 2. Production Inference

Deploy with Groq for high-throughput workloads:

```python
# Handle many concurrent users
backend = GroqLLMBackend(model="llama-3.1-8b-instant")

# Process requests concurrently
tasks = [backend.generate(prompt) for prompt in user_prompts]
responses = await asyncio.gather(*tasks)
```

### 3. Hybrid Deployment

Use Groq for some tasks, local for others:

```python
# Fast responses with Groq
groq_backend = GroqLLMBackend()

# Privacy-sensitive with local
from pebblemind.core.llm import LLMEngine
local_backend = LLMEngine(config)

# Route based on requirements
if task.requires_privacy:
    response = await local_backend.generate(prompt)
else:
    response = await groq_backend.generate(prompt)
```

## Integration with Agents

Specialized agents work seamlessly with Groq:

```python
from pebblemind.backends import GroqLLMBackend
from pebblemind.specialized_agents import AgentOrchestrator

# Agents use tools, Groq enhances responses
orchestrator = AgentOrchestrator()
groq = GroqLLMBackend()

# Agent processes task
result = await orchestrator.route_task("Research quantum computing")

# Groq summarizes findings
summary = await groq.generate(
    f"Summarize: {result['synthesis']}",
    max_tokens=100
)
```

## Cost Considerations

Groq API is currently in preview with generous free tier:

- **Free tier**: Sufficient for development and testing
- **Rate limits**: Check [Groq documentation](https://console.groq.com/docs/rate-limits)
- **Future pricing**: May be introduced when leaving preview

### Cost Optimization Tips

1. **Use appropriate models**
   - Use `llama-3.1-8b-instant` for simple tasks
   - Reserve `70b` for complex reasoning

2. **Limit max_tokens**
   ```python
   response = await backend.generate(prompt, max_tokens=100)
   ```

3. **Batch requests**
   ```python
   responses = await asyncio.gather(*tasks)  # Concurrent, not sequential
   ```

4. **Cache responses**
   ```python
   # Cache common queries
   if prompt in cache:
       return cache[prompt]
   ```

## Comparison: Groq vs Local

| Aspect | Groq Cloud | Local llama.cpp |
|--------|------------|-----------------|
| **Speed** | ⚡⚡⚡⚡ Very fast | ⚡⚡ Moderate |
| **Setup** | ✅ Instant (API key) | ⏳ Model downloads required |
| **Privacy** | 🌐 Cloud-based | 🔒 Fully local |
| **Cost** | 💰 API costs | 🆓 Free (after setup) |
| **Latency** | 🌐 Network dependent | ⚡ No network latency |
| **Models** | 🎯 Curated selection | 🗂️ Any GGUF model |
| **Scaling** | 📈 Auto-scaling | 💻 Limited by hardware |
| **Offline** | ❌ Requires internet | ✅ Works offline |

### When to Use Groq

✅ **Use Groq when:**
- Rapid prototyping and development
- High throughput requirements
- Limited local hardware
- Need fastest possible responses
- Don't need offline operation
- Latency to cloud is acceptable

### When to Use Local

✅ **Use Local when:**
- Privacy is critical
- Offline operation required
- No ongoing costs desired
- Full control over models needed
- Low/no network connectivity
- On-device processing required

## Troubleshooting

### API Key Not Found

```
Error: GROQ_API_KEY environment variable not set
```

**Solution:**
```bash
export GROQ_API_KEY="your_api_key_here"
```

### Rate Limit Exceeded

```
Error: 429 Too Many Requests
```

**Solution:**
- Wait before retrying
- Reduce request frequency
- Upgrade Groq plan (when available)

### Model Not Available

```
Error: Model 'xxx' not found
```

**Solution:**
- Check available models: `GROQ_MODELS` dict
- Use default: `llama-3.1-70b-versatile`

### Connection Timeout

```
Error: Request timeout
```

**Solution:**
- Increase timeout:
  ```python
  backend = GroqLLMBackend()
  backend.client.timeout = 60.0
  ```

## Advanced Usage

### Custom Base URL

```python
# Use different Groq endpoint
backend = GroqLLMBackend(
    base_url="https://custom.groq.endpoint/v1"
)
```

### Error Handling

```python
try:
    response = await backend.generate(prompt)
except httpx.HTTPStatusError as e:
    print(f"HTTP error: {e.response.status_code}")
except Exception as e:
    print(f"Error: {e}")
```

### Concurrent Requests

```python
# Process multiple prompts concurrently
prompts = ["Question 1", "Question 2", "Question 3"]

async def process_all():
    tasks = [backend.generate(p) for p in prompts]
    return await asyncio.gather(*tasks)

responses = await process_all()
```

## Examples

### Example 1: Research Assistant

```python
from pebblemind.backends import GroqLLMBackend

backend = GroqLLMBackend(model="llama-3.1-70b-versatile")

# Research query
response = await backend.generate(
    "Explain the latest developments in quantum computing",
    system_prompt="You are a research assistant. Provide detailed, accurate information.",
    max_tokens=500
)

print(response)
await backend.close()
```

### Example 2: Code Helper

```python
backend = GroqLLMBackend(model="llama-3.1-8b-instant")

# Quick code question
code_help = await backend.generate(
    "How do I reverse a list in Python?",
    max_tokens=100,
    temperature=0.3  # More deterministic for code
)

print(code_help)
```

### Example 3: Creative Writing

```python
backend = GroqLLMBackend(model="llama-3.1-70b-versatile")

# Creative storytelling with streaming
print("Story: ", end="")
async for chunk in backend.generate_stream(
    "Write a short science fiction story about AI",
    temperature=0.9,  # More creative
    max_tokens=300
):
    print(chunk, end="", flush=True)

print()
```

## Resources

- 🌐 [Groq Console](https://console.groq.com/)
- 📚 [Groq Documentation](https://console.groq.com/docs)
- 🔑 [Get API Key](https://console.groq.com/keys)
- 📊 [Rate Limits](https://console.groq.com/docs/rate-limits)
- 🏃 [Groq Playground](https://console.groq.com/playground)

## Summary

Groq integration gives PebbleMind:
- ⚡ **Ultra-fast inference** without local model setup
- 🚀 **Easy deployment** with just an API key
- 🌐 **Cloud scalability** for high-throughput workloads
- 🔄 **Flexibility** to choose between cloud and local based on needs

Perfect for development, testing, and production deployments that prioritize speed and ease of use!

---

**Ready to try it?**

```bash
export GROQ_API_KEY="your_key"
python scripts/comprehensive_test.py
```
