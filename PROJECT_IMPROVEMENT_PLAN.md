# PebbleMind Project Improvement Plan

**Version:** 1.0
**Date:** October 24, 2025
**Status:** Draft
**Estimated Timeline:** 6-8 weeks to production-ready

---

## Executive Summary

PebbleMind is an ambitious CPU-first AI assistant project that is **60-70% implemented**. The core functionality (LLM inference, RAG, API) works well, but there are critical gaps in testing, security, and advanced features. The README promises significantly more functionality than currently exists.

**Key Issues:**
- ❌ Zero test coverage
- 🔴 Critical security vulnerabilities (unsafe `eval()` usage)
- ⚠️ Desktop application incomplete (Rust backend is a stub)
- ⚠️ Voice processing untested and may not work
- ⚠️ Gap between documentation and implementation

**Project Goal:** Transform PebbleMind from an MVP to a production-ready, secure, well-tested local AI assistant.

---

## Phase 1: Critical Fixes (Week 1-2)

### Priority: CRITICAL

#### 1.1 Security Vulnerabilities

**Issue:** Unsafe `eval()` usage in multiple files could execute arbitrary code.

**Files to Fix:**
- `/home/user/pebblemind/pebblemind/rag/system.py:253, 272`
- `/home/user/pebblemind/pebblemind/tool_integration.py`

**Actions:**
```python
# BEFORE (UNSAFE):
"metadata": eval(metadata) if metadata else {}

# AFTER (SAFE):
import json
"metadata": json.loads(metadata) if metadata else {}
```

**Tasks:**
- [ ] Replace all `eval()` with `json.loads()` or `ast.literal_eval()`
- [ ] Replace calculator `eval()` with safe expression parser (use `numexpr` or `simpleeval`)
- [ ] Add input sanitization to code executor
- [ ] Run security audit with `bandit` tool

**Estimated Time:** 1 day

---

#### 1.2 Testing Infrastructure

**Issue:** Zero tests make it impossible to refactor safely or verify functionality.

**Actions:**
- [ ] Create `tests/` directory structure
- [ ] Set up pytest configuration
- [ ] Add pytest plugins (pytest-asyncio, pytest-cov, pytest-mock)
- [ ] Create test fixtures for common objects (config, llm mock, etc.)

**Initial Test Coverage Target: 60%+**

**Directory Structure:**
```
tests/
├── unit/
│   ├── test_core_llm.py
│   ├── test_rag_system.py
│   ├── test_tool_integration.py
│   ├── test_memory.py
│   └── test_config.py
├── integration/
│   ├── test_api_endpoints.py
│   ├── test_cli_commands.py
│   └── test_streaming.py
├── fixtures/
│   └── common.py
└── conftest.py
```

**Critical Tests to Write:**
1. **Core LLM** (test_core_llm.py)
   - Model loading with different sizes
   - Token generation
   - Streaming responses
   - GPU detection
   - Error handling

2. **RAG System** (test_rag_system.py)
   - Document ingestion
   - Vector search
   - Chunking algorithms
   - Metadata handling (test the json.loads fix)

3. **API Server** (test_api_endpoints.py)
   - Chat completions
   - Streaming responses
   - OpenAI compatibility
   - Error responses

4. **Tool Integration** (test_tool_integration.py)
   - Calculator (with safe expressions)
   - File reader
   - Web search
   - Code executor safety

5. **Memory System** (test_memory.py)
   - Memory storage/retrieval
   - Consolidation
   - Forgetting mechanism

**Estimated Time:** 1 week

---

#### 1.3 Input Validation

**Issue:** Missing validation allows malformed inputs to cause crashes.

**Actions:**
- [ ] Add Pydantic models for all API endpoints
- [ ] Validate file paths before file operations
- [ ] Validate model names before loading
- [ ] Add length limits to text inputs
- [ ] Sanitize SQL queries in RAG system

**Example:**
```python
from pydantic import BaseModel, Field, validator

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    model: str = Field(default="3b", regex="^(1.5b|3b|7b)$")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    @validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v
```

**Estimated Time:** 2 days

---

## Phase 2: Core Feature Completion (Week 3-4)

### Priority: HIGH

#### 2.1 Desktop Application Backend

**Issue:** Rust backend is a stub. TypeScript frontend cannot communicate with Python.

**Current State:**
```rust
// src-tauri/src/lib.rs - Only a greet() function
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}
```

**Required Implementation:**
1. **IPC Layer**: Rust commands to call Python backend
2. **Model Management**: Switch models, check status
3. **Chat Interface**: Send messages, receive streaming responses
4. **Configuration**: Update settings from UI

**Tasks:**
- [ ] Design IPC protocol (JSON-RPC over stdin/stdout or HTTP)
- [ ] Implement Python subprocess management in Rust
- [ ] Add Tauri commands:
  - `start_chat(message: String) -> Stream<String>`
  - `switch_model(size: String) -> Result<()>`
  - `get_status() -> Status`
  - `update_config(config: Config) -> Result<()>`
- [ ] Handle streaming responses in TypeScript
- [ ] Add error handling and retries

**Example Implementation:**
```rust
use tauri::State;
use tokio::process::Command;

#[tauri::command]
async fn chat(message: String, state: State<'_, AppState>) -> Result<String, String> {
    let output = Command::new("pebblemind")
        .arg("chat")
        .arg(&message)
        .output()
        .await
        .map_err(|e| e.to_string())?;

    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}
```

**Estimated Time:** 1 week

---

#### 2.2 Voice Processing Verification

**Issue:** Voice code exists but is untested and requires external dependencies.

**Actions:**
- [ ] Document required dependencies (whisper.cpp, Piper)
- [ ] Create installation scripts for each platform
- [ ] Add graceful degradation when voice unavailable
- [ ] Test with actual audio files
- [ ] Add voice tests (with mocked dependencies)

**Tasks:**
- [ ] Create `scripts/install_voice_deps.sh`
- [ ] Add voice capability detection at startup
- [ ] Implement fallback messages when voice disabled
- [ ] Test transcription with various audio formats
- [ ] Test TTS with different languages

**Example Graceful Degradation:**
```python
class VoiceProcessor:
    def __init__(self):
        self.available = self._check_dependencies()
        if not self.available:
            logger.warning("Voice features unavailable - missing whisper.cpp or Piper")

    def transcribe(self, audio_path: str) -> Optional[str]:
        if not self.available:
            raise RuntimeError("Voice features not available. Install dependencies.")
        # ... existing code
```

**Estimated Time:** 3 days

---

#### 2.3 Model Download Automation

**Issue:** README claims automatic model downloading, but no implementation exists.

**Actions:**
- [ ] Create `scripts/download_models.py`
- [ ] Add Hugging Face Hub integration
- [ ] Implement progress bars for downloads
- [ ] Add checksum verification
- [ ] Support resumable downloads

**Example:**
```python
from huggingface_hub import hf_hub_download
from tqdm import tqdm

def download_model(model_size: str, output_dir: str):
    """Download Qwen2.5 model from HuggingFace"""
    model_ids = {
        "1.5b": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        "3b": "Qwen/Qwen2.5-3B-Instruct-GGUF",
        "7b": "Qwen/Qwen2.5-7B-Instruct-GGUF"
    }
    filename = f"qwen2.5-{model_size}-instruct-q4_k_m.gguf"

    print(f"Downloading {model_size} model...")
    hf_hub_download(
        repo_id=model_ids[model_size],
        filename=filename,
        local_dir=output_dir,
        resume_download=True
    )
```

**CLI Integration:**
```bash
pebblemind download-model 3b
pebblemind download-model all
pebblemind download-model --embedding
```

**Estimated Time:** 2 days

---

#### 2.4 Documentation Update

**Issue:** README promises features that don't exist or don't work.

**Actions:**
- [ ] Create FEATURES.md with actual implementation status
- [ ] Update README with accurate feature list
- [ ] Add ARCHITECTURE.md explaining system design
- [ ] Create SECURITY.md with security best practices
- [ ] Add API.md with complete API documentation
- [ ] Create CONTRIBUTING.md with development guide

**Feature Status Matrix:**
```markdown
## Feature Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Local LLM Inference | ✅ Complete | Tested with Qwen2.5 |
| RAG System | ✅ Complete | Vector search working |
| Voice Input/Output | ⚠️ Partial | Requires external deps |
| Advanced Memory | ✅ Complete | SQLite-based |
| Tool Integration | ✅ Complete | 6 tools available |
| Specialized Agents | ⚠️ Beta | Basic functionality |
| Multi-modal | ❌ Planned | Image analysis only |
| Desktop App | ⚠️ Beta | UI complete, backend in progress |
```

**Estimated Time:** 2 days

---

## Phase 3: Advanced Features (Week 5-6)

### Priority: MEDIUM

#### 3.1 Specialized Agents Enhancement

**Current State:** Base classes exist but limited functionality.

**Actions:**
- [ ] Implement full ResearchAgent with web search
- [ ] Implement CodeAgent with syntax highlighting
- [ ] Implement MathAgent with symbolic computation
- [ ] Implement WritingAgent with style detection
- [ ] Add agent memory and context management
- [ ] Create agent orchestration tests

**Example Enhancement:**
```python
class ResearchAgent(BaseAgent):
    async def research(self, query: str) -> ResearchResult:
        """Conduct comprehensive research on a topic"""
        # 1. Search web for current information
        search_results = await self.tools.web_search(query, limit=10)

        # 2. Retrieve relevant documents from RAG
        rag_results = await self.rag.search(query, k=5)

        # 3. Synthesize information
        context = self._build_context(search_results, rag_results)

        # 4. Generate comprehensive report
        report = await self.llm.generate(
            prompt=self._build_research_prompt(query, context),
            temperature=0.7
        )

        # 5. Store in memory for future reference
        await self.memory.store(query, report, tags=["research"])

        return ResearchResult(query=query, report=report, sources=context)
```

**Estimated Time:** 1 week

---

#### 3.2 External Service Integration

**Current State:** Only SQLite stub exists.

**Actions:**
- [ ] Implement Weather API integration (OpenWeatherMap)
- [ ] Add PostgreSQL database support
- [ ] Add MySQL database support
- [ ] Add REST API client builder
- [ ] Create service registry and discovery

**Example:**
```python
class WeatherService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"

    async def get_weather(self, location: str) -> WeatherData:
        """Get current weather for location"""
        url = f"{self.base_url}/weather"
        params = {"q": location, "appid": self.api_key, "units": "metric"}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        return WeatherData(
            location=location,
            temperature=data["main"]["temp"],
            conditions=data["weather"][0]["description"],
            humidity=data["main"]["humidity"]
        )
```

**Estimated Time:** 3 days

---

#### 3.3 Software 3.0 Integration

**Current State:** Self-learning module exists but not deeply integrated.

**Actions:**
- [ ] Connect self-learning to actual queries
- [ ] Implement performance tracking per query
- [ ] Add automatic parameter tuning
- [ ] Create learning dashboard
- [ ] Add experience replay mechanism

**Example:**
```python
class Software30Manager:
    async def learn_from_interaction(
        self,
        query: str,
        response: str,
        feedback: Optional[float] = None
    ):
        """Learn from user interaction"""
        # Track performance
        metrics = self._compute_metrics(query, response)

        # Store experience
        await self.experience_buffer.add(
            query=query,
            response=response,
            metrics=metrics,
            feedback=feedback
        )

        # Periodically update parameters
        if self.experience_buffer.size() >= self.batch_size:
            await self._update_parameters()
```

**Estimated Time:** 4 days

---

#### 3.4 Performance Optimization

**Actions:**
- [ ] Add database indexing to RAG system
- [ ] Implement connection pooling
- [ ] Add caching layer for embeddings
- [ ] Optimize document chunking algorithm
- [ ] Add batch processing for multiple queries
- [ ] Profile and optimize hot paths

**Performance Targets:**
```
Metric               | Current | Target
---------------------|---------|--------
LLM tokens/sec       | Unknown | 20+ (MacBook Air M1)
RAG search time      | Unknown | <100ms
Memory retrieval     | Unknown | <50ms
API response time    | Unknown | <200ms (first token)
Embedding generation | Unknown | <500ms per document
```

**Estimated Time:** 4 days

---

## Phase 4: Production Readiness (Week 7-8)

### Priority: HIGH

#### 4.1 CI/CD Pipeline

**Actions:**
- [ ] Create GitHub Actions workflow
- [ ] Add automated testing on push
- [ ] Add code coverage reporting
- [ ] Add security scanning (bandit, safety)
- [ ] Add linting (black, isort, flake8, mypy)
- [ ] Add pre-commit hooks

**Example `.github/workflows/ci.yml`:**
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Run tests
        run: pytest --cov=pebblemind --cov-report=xml
      - name: Security scan
        run: bandit -r pebblemind/
      - name: Type check
        run: mypy pebblemind/
```

**Estimated Time:** 2 days

---

#### 4.2 Error Handling & Logging

**Actions:**
- [ ] Standardize error messages across modules
- [ ] Add structured logging with context
- [ ] Implement error recovery mechanisms
- [ ] Add telemetry (optional, local only)
- [ ] Create troubleshooting guide

**Example:**
```python
import structlog

logger = structlog.get_logger()

class LLMEngine:
    async def generate(self, prompt: str) -> str:
        try:
            logger.info("llm.generate.start", prompt_length=len(prompt))
            result = await self._generate_internal(prompt)
            logger.info("llm.generate.success", response_length=len(result))
            return result
        except Exception as e:
            logger.error(
                "llm.generate.failed",
                error=str(e),
                error_type=type(e).__name__,
                prompt_length=len(prompt)
            )
            raise LLMGenerationError(f"Failed to generate: {e}") from e
```

**Estimated Time:** 3 days

---

#### 4.3 Deployment & Packaging

**Actions:**
- [ ] Create Docker image for easy deployment
- [ ] Add docker-compose for full stack
- [ ] Create installation scripts for each platform
- [ ] Build standalone executables (PyInstaller)
- [ ] Create Homebrew formula (macOS)
- [ ] Create Snap package (Linux)

**Example Dockerfile (optimized):**
```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libopenblas-dev \
    libomp-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy application
COPY pebblemind/ ./pebblemind/

# Expose API port
EXPOSE 8000

CMD ["pebblemind", "serve"]
```

**Estimated Time:** 3 days

---

#### 4.4 Benchmarking & Performance Testing

**Actions:**
- [ ] Create benchmark suite
- [ ] Test on different hardware (M1, M2, AMD, Intel)
- [ ] Measure actual tokens/second
- [ ] Profile memory usage
- [ ] Test with different model sizes
- [ ] Create performance report

**Example Benchmark:**
```python
import time
import pytest

@pytest.mark.benchmark
def test_llm_inference_speed(llm_engine):
    """Benchmark LLM inference speed"""
    prompt = "Write a short story about AI."

    start = time.perf_counter()
    response = llm_engine.generate(prompt, max_tokens=100)
    duration = time.perf_counter() - start

    tokens = len(response.split())
    tokens_per_sec = tokens / duration

    print(f"Generated {tokens} tokens in {duration:.2f}s")
    print(f"Speed: {tokens_per_sec:.2f} tokens/sec")

    assert tokens_per_sec > 10  # Minimum acceptable speed
```

**Estimated Time:** 2 days

---

## Phase 5: Advanced Enhancements (Future)

### Priority: LOW

These are aspirational features that can be added after production release:

#### 5.1 Vision Model Integration
- Add actual vision model (e.g., LLaVA, CLIP)
- Image understanding capabilities
- OCR integration
- Visual question answering

**Estimated Time:** 2 weeks

---

#### 5.2 Multi-Agent Collaboration
- Agents working together on complex tasks
- Task decomposition and delegation
- Result synthesis
- Conflict resolution

**Estimated Time:** 1 week

---

#### 5.3 Plugin System
- Allow users to add custom tools
- Hot-reload plugins
- Plugin marketplace
- Sandboxed execution

**Estimated Time:** 2 weeks

---

#### 5.4 Mobile Apps
- iOS application
- Android application
- React Native or Flutter
- Sync with desktop

**Estimated Time:** 4 weeks

---

#### 5.5 Advanced RAG Features
- Multi-modal RAG (images, PDFs)
- Graph-based RAG
- Hybrid search (dense + sparse)
- Reranking models

**Estimated Time:** 2 weeks

---

## Implementation Priority Matrix

```
Priority | Phase | Tasks | Est. Time | Impact
---------|-------|-------|-----------|--------
🔴 P0    | 1     | Security fixes, Testing, Validation | 2 weeks | Critical
🟠 P1    | 2     | Desktop backend, Voice, Docs | 2 weeks | High
🟡 P2    | 3     | Agents, Services, Performance | 2 weeks | Medium
🟢 P3    | 4     | CI/CD, Deployment, Benchmarks | 2 weeks | High
⚪ P4    | 5     | Vision, Plugins, Mobile | Future | Low
```

---

## Success Metrics

### Phase 1 (Weeks 1-2)
- ✅ Zero security vulnerabilities (bandit scan passes)
- ✅ Test coverage > 60%
- ✅ All inputs validated

### Phase 2 (Weeks 3-4)
- ✅ Desktop app functional end-to-end
- ✅ Voice processing tested and working
- ✅ Model download automation working
- ✅ Documentation accurate

### Phase 3 (Weeks 5-6)
- ✅ All 4 specialized agents working
- ✅ External services integrated
- ✅ Performance benchmarks documented

### Phase 4 (Weeks 7-8)
- ✅ CI/CD pipeline running
- ✅ Docker image available
- ✅ Installation scripts for all platforms
- ✅ Production-ready release

---

## Resource Requirements

### Development Team
- 1 Backend Engineer (Python)
- 1 Frontend Engineer (TypeScript/Rust)
- 1 DevOps Engineer (part-time)
- 1 QA Engineer (testing)

### Infrastructure
- GitHub Actions (CI/CD)
- Docker Hub (image hosting)
- HuggingFace account (model downloads)
- Testing hardware (M1/M2 Mac, AMD/Intel PCs)

---

## Risk Assessment

### High Risk
1. **Voice dependencies** - May be difficult to install on some systems
   - Mitigation: Provide pre-built binaries, clear docs

2. **Model size** - 7B model may be too large for some devices
   - Mitigation: Recommend 1.5B/3B for lightweight devices

3. **Performance claims** - May not match real-world results
   - Mitigation: Benchmark on actual hardware, update claims

### Medium Risk
1. **Desktop app complexity** - Rust/Python IPC may be challenging
   - Mitigation: Use proven IPC patterns (HTTP or stdio)

2. **Test coverage** - Achieving 60%+ may take longer
   - Mitigation: Focus on critical paths first

### Low Risk
1. **External service APIs** - May change or become unavailable
   - Mitigation: Abstract behind interfaces, allow fallbacks

---

## Next Steps

### Immediate Actions (This Week)
1. Fix security vulnerabilities (eval → json.loads)
2. Set up testing infrastructure
3. Write first 20 tests for core functionality
4. Run security scan with bandit
5. Document current feature status

### Week 2
1. Complete test coverage to 60%
2. Add input validation everywhere
3. Begin desktop backend implementation
4. Create model download script

### Week 3-4
1. Finish desktop application
2. Test voice processing
3. Update documentation
4. Implement missing services

### Week 5-8
1. Enhance specialized agents
2. Optimize performance
3. Set up CI/CD
4. Prepare for production release

---

## Conclusion

PebbleMind has a solid foundation with good architectural decisions, but needs focused work on security, testing, and completing promised features. With 6-8 weeks of dedicated effort following this plan, the project can reach production quality.

**Key Takeaway:** Prioritize security and testing (Phase 1) before adding new features. A secure, well-tested system is more valuable than a feature-rich but unreliable one.

---

## Appendix A: File Structure (Proposed)

```
pebblemind/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── release.yml
│       └── security.yml
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── FEATURES.md
│   └── SECURITY.md
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── benchmarks/
│   └── fixtures/
├── scripts/
│   ├── download_models.py
│   ├── install_voice_deps.sh
│   └── setup_dev.sh
├── pebblemind/
│   └── [existing modules]
├── desktop/
│   └── [existing + enhanced Rust backend]
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── .pre-commit-config.yaml
├── pyproject.toml
└── README.md
```

---

## Appendix B: Technology Stack

### Core
- Python 3.9+ (async/await)
- llama.cpp (LLM inference)
- FastAPI (API server)
- SQLite (storage)

### Optional
- Tauri (desktop)
- whisper.cpp (speech-to-text)
- Piper TTS (text-to-speech)

### Development
- pytest (testing)
- black (formatting)
- mypy (type checking)
- bandit (security)

### Deployment
- Docker
- GitHub Actions

---

**End of Plan**

*For questions or suggestions, please open an issue on GitHub.*
