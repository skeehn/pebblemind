"""Unit tests for Tool Integration System"""

import pytest

from pebblemind.tool_integration import FunctionCallingManager, ToolManager


@pytest.mark.unit
class TestToolManager:
    """Test suite for ToolManager"""

    def test_initialization(self):
        """Test ToolManager initialization"""
        manager = ToolManager()
        assert len(manager.tools) > 0
        assert "calculator" in manager.tools
        assert "datetime" in manager.tools
        assert "file_reader" in manager.tools
        assert "code_executor" in manager.tools
        assert "web_search" in manager.tools
        assert "wikipedia" in manager.tools

    def test_register_tool(self):
        """Test registering a new tool"""
        manager = ToolManager()

        async def custom_tool(**kwargs):
            return "custom result"

        manager.register_tool("custom", custom_tool)
        assert "custom" in manager.tools
        assert manager.tools["custom"] == custom_tool

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self):
        """Test executing a tool that doesn't exist"""
        manager = ToolManager()
        result = await manager.execute_tool("nonexistent", {})

        assert "error" in result
        assert "not found" in result["error"].lower()
        assert "available_tools" in result


@pytest.mark.unit
class TestCalculatorTool:
    """Test suite for Calculator Tool (Security Critical)"""

    @pytest.mark.asyncio
    async def test_calculator_basic_operations(self, calculator_expressions):
        """Test basic calculator operations"""
        manager = ToolManager()

        for expression, expected in calculator_expressions["valid"]:
            result = await manager.execute_tool(
                "calculator", {"expression": expression}
            )
            assert result["success"]
            assert "result" in result["result"].lower()
            # Extract the numeric result and verify
            result_str = result["result"]
            assert str(expected) in result_str or str(float(expected)) in result_str

    @pytest.mark.asyncio
    async def test_calculator_safe_eval_replaces_eval(self):
        """Test that calculator uses AST-based safe_eval instead of eval"""
        manager = ToolManager()

        # These should work with safe_eval
        safe_expressions = ["2 + 2", "10 * 5", "(3 + 4) * 2", "2 ** 3"]

        for expr in safe_expressions:
            result = await manager.execute_tool("calculator", {"expression": expr})
            assert result["success"], f"Expression '{expr}' should be safe"

    @pytest.mark.asyncio
    async def test_calculator_rejects_malicious_code(self):
        """Test that calculator rejects malicious code (security fix verification)"""
        manager = ToolManager()

        malicious_expressions = [
            "__import__('os').system('ls')",
            "exec('print(1)')",
            "eval('1+1')",
            "open('/etc/passwd')",
            "__builtins__",
            "globals()",
            "locals()",
        ]

        for expr in malicious_expressions:
            result = await manager.execute_tool("calculator", {"expression": expr})
            # Should fail - either not successful or raise an error
            assert (
                not result.get("success", False)
                or "error" in result.get("result", "").lower()
            ), f"Malicious expression '{expr}' should be rejected"

    @pytest.mark.asyncio
    async def test_calculator_prevents_attribute_access(self):
        """Test that calculator prevents attribute access attempts"""
        manager = ToolManager()

        dangerous_expressions = [
            "().__class__.__bases__[0].__subclasses__()",
            "''.__class__.__mro__[1].__subclasses__()",
        ]

        for expr in dangerous_expressions:
            result = await manager.execute_tool("calculator", {"expression": expr})
            assert not result.get(
                "success", False
            ), f"Attribute access '{expr}' should be prevented"


@pytest.mark.unit
class TestCodeExecutorTool:
    """Test suite for Code Executor Tool (Security Critical)"""

    @pytest.mark.asyncio
    async def test_code_executor_safe_code(self, safe_code_samples):
        """Test that safe code executes successfully"""
        manager = ToolManager()

        for code in safe_code_samples["safe"]:
            result = await manager.execute_tool(
                "code_executor", {"language": "python", "code": code}
            )
            # Should execute without raising security errors
            assert "result" in result
            # Check for output or success message
            result_text = result["result"]
            assert (
                "error" not in result_text.lower()
                or "execution error" in result_text.lower()
            )

    @pytest.mark.asyncio
    async def test_code_executor_blocks_unsafe_code(self, safe_code_samples):
        """Test that unsafe code is blocked"""
        manager = ToolManager()

        for code in safe_code_samples["unsafe"]:
            result = await manager.execute_tool(
                "code_executor", {"language": "python", "code": code}
            )
            # Should be rejected
            result_text = result.get("result", "")
            assert (
                "unsafe" in result_text.lower() or "not allowed" in result_text.lower()
            ), f"Unsafe code should be rejected: {code[:50]}"

    @pytest.mark.asyncio
    async def test_code_executor_blocks_imports(self):
        """Test that import statements are blocked"""
        manager = ToolManager()

        import_tests = [
            "import os",
            "from sys import exit",
            "import subprocess",
            "__import__('os')",
        ]

        for code in import_tests:
            result = await manager.execute_tool(
                "code_executor", {"language": "python", "code": code}
            )
            result_text = result.get("result", "")
            assert (
                "import" in result_text.lower() and "not allowed" in result_text.lower()
            ), f"Import should be blocked: {code}"

    @pytest.mark.asyncio
    async def test_code_executor_length_limit(self):
        """Test that code length is limited"""
        manager = ToolManager()

        # Generate code longer than 1000 characters
        long_code = "x = 1\n" * 500  # ~3000 characters

        result = await manager.execute_tool(
            "code_executor", {"language": "python", "code": long_code}
        )
        result_text = result.get("result", "")
        assert "too long" in result_text.lower(), "Long code should be rejected"

    @pytest.mark.asyncio
    async def test_code_executor_only_python(self):
        """Test that only Python is supported"""
        manager = ToolManager()

        result = await manager.execute_tool(
            "code_executor", {"language": "javascript", "code": "console.log('test')"}
        )
        result_text = result.get("result", "")
        assert (
            "only python" in result_text.lower()
        ), "Non-Python languages should be rejected"

    @pytest.mark.asyncio
    async def test_code_executor_captures_print(self):
        """Test that print output is captured"""
        manager = ToolManager()

        code = "print('Hello, World!')"
        result = await manager.execute_tool(
            "code_executor", {"language": "python", "code": code}
        )

        result_text = result.get("result", "")
        assert (
            "hello" in result_text.lower() and "world" in result_text.lower()
        ), "Print output should be captured"


@pytest.mark.unit
class TestFileReaderTool:
    """Test suite for File Reader Tool"""

    @pytest.mark.asyncio
    async def test_file_reader_reads_valid_file(self, temp_dir):
        """Test reading a valid text file"""
        manager = ToolManager()

        # Create a test file
        test_file = temp_dir / "test.txt"
        test_content = "This is a test file"
        test_file.write_text(test_content)

        result = await manager.execute_tool(
            "file_reader", {"file_path": str(test_file)}
        )

        assert result["success"]
        assert test_content in result["result"]

    @pytest.mark.asyncio
    async def test_file_reader_rejects_unsafe_paths(self):
        """Test that unsafe file paths are rejected"""
        manager = ToolManager()

        unsafe_paths = [
            "/etc/passwd",
            "/usr/bin/bash",
            "../../../etc/passwd",
        ]

        for path in unsafe_paths:
            result = await manager.execute_tool("file_reader", {"file_path": path})
            # Should fail
            assert (
                not result.get("success", False) or "error" in result
            ), f"Unsafe path should be rejected: {path}"

    @pytest.mark.asyncio
    async def test_file_reader_rejects_large_files(self, temp_dir):
        """Test that large files are rejected"""
        manager = ToolManager()

        # Create a file larger than 1MB
        large_file = temp_dir / "large.txt"
        large_file.write_text("x" * (1024 * 1024 + 1))

        result = await manager.execute_tool(
            "file_reader", {"file_path": str(large_file)}
        )

        # Should be rejected
        result_text = (
            str(result.get("result", ""))
            if "result" in result
            else str(result.get("error", ""))
        )
        assert "too large" in result_text.lower(), "Large files should be rejected"

    @pytest.mark.asyncio
    async def test_file_reader_rejects_unsafe_extensions(self, temp_dir):
        """Test that unsafe file extensions are rejected"""
        manager = ToolManager()

        # Create a file with unsafe extension
        unsafe_file = temp_dir / "test.exe"
        unsafe_file.write_text("test")

        result = await manager.execute_tool(
            "file_reader", {"file_path": str(unsafe_file)}
        )

        # Should be rejected
        assert not result.get("success", False), "Unsafe file type should be rejected"


@pytest.mark.unit
class TestDatetimeTool:
    """Test suite for Datetime Tool"""

    @pytest.mark.asyncio
    async def test_datetime_returns_current_time(self):
        """Test that datetime tool returns current time"""
        manager = ToolManager()

        result = await manager.execute_tool("datetime", {})

        assert result["success"]
        assert "current date and time" in result["result"].lower()
        # Check for date format components
        assert any(str(i) in result["result"] for i in range(2020, 2030))  # Year


@pytest.mark.unit
class TestFunctionCallingManager:
    """Test suite for Function Calling Manager"""

    @pytest.mark.asyncio
    async def test_plan_and_execute_with_datetime(self):
        """Test planning and executing a task with datetime"""
        tool_manager = ToolManager()
        fc_manager = FunctionCallingManager(tool_manager)

        result = await fc_manager.plan_and_execute("What time is it now?")

        assert "original_task" in result
        assert "steps_executed" in result
        assert len(result["steps_executed"]) > 0

    @pytest.mark.asyncio
    async def test_plan_and_execute_with_calculator(self):
        """Test planning and executing a calculation task"""
        tool_manager = ToolManager()
        fc_manager = FunctionCallingManager(tool_manager)

        result = await fc_manager.plan_and_execute("Calculate 15 * 24")

        assert "original_task" in result
        assert "steps_executed" in result
        # Should have used calculator
        assert any(
            "calculator" in str(step).lower() for step in result["steps_executed"]
        )

    @pytest.mark.asyncio
    async def test_analyze_task_extracts_calculation(self):
        """Test that task analysis extracts calculations correctly"""
        tool_manager = ToolManager()
        fc_manager = FunctionCallingManager(tool_manager)

        steps = await fc_manager._analyze_task("What is 10 + 5?")

        # Should identify calculator tool
        assert any(step["tool"] == "calculator" for step in steps)


@pytest.mark.unit
class TestToolParsing:
    """Test suite for tool call parsing"""

    @pytest.mark.asyncio
    async def test_parse_embedded_tool_calls(self):
        """Test parsing embedded tool calls from text"""
        manager = ToolManager()

        text = 'Please [[calculator: {"expression": "2+2"}]] for me'
        results = await manager.parse_and_execute_tools(text)

        assert len(results) > 0
        assert results[0]["tool_name"] == "calculator"
        assert results[0]["success"]

    @pytest.mark.asyncio
    async def test_parse_invalid_json(self):
        """Test handling of invalid JSON in tool calls"""
        manager = ToolManager()

        text = "[[calculator: {invalid json}]]"
        results = await manager.parse_and_execute_tools(text)

        assert len(results) > 0
        assert "error" in results[0]
        assert "invalid json" in results[0]["error"].lower()
