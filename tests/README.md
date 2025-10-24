# PebbleMind Test Suite

Comprehensive test suite for PebbleMind covering unit tests, integration tests, and security validation.

## Quick Start

### Install Test Dependencies

```bash
# Install all development dependencies including pytest
pip install -e ".[dev]"
```

### Run All Tests

```bash
# Run all tests with coverage
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_rag_system.py

# Run specific test
pytest tests/unit/test_rag_system.py::TestRAGSystem::test_metadata_security_fix
```

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures and configuration
├── unit/                 # Unit tests for individual components
│   ├── test_rag_system.py       # RAG system tests
│   ├── test_tool_integration.py # Tool integration tests
│   └── test_config.py           # Configuration tests
├── integration/          # Integration tests
│   └── (to be added)
└── fixtures/            # Test data and fixtures
```

## Test Coverage

Current coverage: **60%+**

### Coverage by Module
- ✅ RAG System: 80%+
- ✅ Tool Integration: 75%+
- ✅ Configuration: 70%+
- 🟡 API Server: 60%+
- 🟡 LLM Engine: 40%+

### View Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=pebblemind --cov-report=html

# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Test Markers

Tests are organized with markers for selective execution:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Skip tests requiring downloaded models
pytest -m "not requires_models"

# Skip tests requiring network
pytest -m "not requires_network"

# Run benchmark tests
pytest -m benchmark
```

### Available Markers
- `unit` - Unit tests for individual components
- `integration` - Integration tests for component interactions
- `slow` - Tests that take a long time to run
- `requires_models` - Tests that require downloaded models
- `requires_network` - Tests that require network access
- `benchmark` - Performance benchmark tests

## Key Test Files

### test_rag_system.py
Tests for the RAG (Retrieval-Augmented Generation) system including:
- ✅ Metadata security fix verification (json.loads vs eval)
- ✅ Document chunking
- ✅ Vector search
- ✅ Document management
- ✅ Database statistics

**Critical Test:**
```bash
# Verify security fix for metadata handling
pytest tests/unit/test_rag_system.py::TestRAGSystem::test_metadata_security_fix
```

### test_tool_integration.py
Tests for tool integration and function calling including:
- ✅ Calculator tool safety (AST-based evaluation)
- ✅ Code executor security
- ✅ File reader safety
- ✅ Tool registration and execution

**Critical Tests:**
```bash
# Verify calculator security fix
pytest tests/unit/test_tool_integration.py::TestCalculatorTool::test_calculator_safe_eval_replaces_eval

# Verify code executor blocks unsafe code
pytest tests/unit/test_tool_integration.py::TestCodeExecutorTool::test_code_executor_blocks_unsafe_code
```

### test_config.py
Tests for configuration management including:
- ✅ Config loading and saving
- ✅ Validation rules
- ✅ Default values
- ✅ YAML parsing

## Continuous Integration

Tests run automatically on every push/PR via GitHub Actions:
- ✅ Multiple OS (Ubuntu, macOS)
- ✅ Multiple Python versions (3.9, 3.10, 3.11)
- ✅ Coverage reporting to Codecov
- ✅ Security scanning with Bandit

See `.github/workflows/ci.yml` for details.

## Writing New Tests

### Basic Test Template

```python
import pytest
from pebblemind.your_module import YourClass

@pytest.mark.unit
class TestYourClass:
    """Test suite for YourClass"""

    def test_basic_functionality(self):
        """Test basic functionality"""
        obj = YourClass()
        result = obj.method()
        assert result == expected_value

    @pytest.mark.asyncio
    async def test_async_method(self):
        """Test async method"""
        obj = YourClass()
        result = await obj.async_method()
        assert result is not None
```

### Using Fixtures

Common fixtures are defined in `conftest.py`:

```python
def test_with_config(test_config):
    """Use the test_config fixture"""
    assert test_config.llm.model_size == "1.5b"

def test_with_temp_dir(temp_dir):
    """Use temporary directory"""
    test_file = temp_dir / "test.txt"
    test_file.write_text("test")
    assert test_file.exists()
```

### Security Testing

When testing security-sensitive code:

```python
@pytest.mark.unit
class TestSecurity:
    """Security-focused tests"""

    def test_rejects_malicious_input(self):
        """Test that malicious input is rejected"""
        malicious_input = "__import__('os').system('ls')"

        with pytest.raises(ValueError):
            unsafe_function(malicious_input)

    def test_validates_input_length(self):
        """Test input length validation"""
        too_long = "x" * 100000

        with pytest.raises(ValueError):
            function_with_limits(too_long)
```

## Debugging Tests

### Run Tests in Debug Mode

```bash
# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb

# Show local variables in tracebacks
pytest --showlocals

# More verbose output
pytest -vv
```

### Skip Tests

```python
@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature():
    pass

@pytest.mark.skipif(sys.platform == "win32", reason="Unix only")
def test_unix_feature():
    pass
```

## Performance Testing

```bash
# Run only benchmark tests
pytest -m benchmark

# Show slowest tests
pytest --durations=10
```

## Test Data

Sample test data is available via fixtures:

- `sample_documents` - Example documents for RAG testing
- `sample_chat_messages` - Chat message examples
- `calculator_expressions` - Valid and invalid calculator inputs
- `safe_code_samples` - Safe and unsafe code samples

## Troubleshooting

### Tests Fail Due to Missing Models

Some tests are marked with `@pytest.mark.requires_models` and are skipped by default. To run them:

1. Download models first: `python scripts/download_models.py --llm 3b --embedding`
2. Run: `pytest -m requires_models`

### Tests Fail Due to Network Issues

Tests marked with `@pytest.mark.requires_network` are skipped in CI. Run locally:

```bash
pytest -m requires_network
```

### Import Errors

Make sure PebbleMind is installed in development mode:

```bash
pip install -e ".[dev]"
```

### Coverage Issues

If coverage is below 60%, the CI will fail. To fix:

1. Run: `pytest --cov=pebblemind --cov-report=term-missing`
2. Identify untested code (lines marked with `!!!!`)
3. Add tests for those areas
4. Verify: `pytest --cov=pebblemind --cov-fail-under=60`

## Best Practices

1. **Write tests first** - TDD approach when adding new features
2. **Test security** - Always test for vulnerabilities in security-sensitive code
3. **Use fixtures** - Reuse common setup code via fixtures
4. **Mark tests** - Use markers to categorize tests
5. **Mock external dependencies** - Don't rely on network or large models in unit tests
6. **Test edge cases** - Empty inputs, large inputs, malformed data
7. **Keep tests fast** - Unit tests should run in milliseconds
8. **Document tests** - Clear docstrings explaining what's being tested

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [Writing good tests](https://docs.pytest.org/en/stable/goodpractices.html)

---

**Need help?** Open an issue on GitHub or check the PROJECT_IMPROVEMENT_PLAN.md for testing roadmap.
