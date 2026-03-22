"""Tool Integration System for PebbleMind"""

import asyncio
import json
import re
from typing import Dict, Any, List, Optional, Callable, Union
from pathlib import Path
import subprocess
import os
from datetime import datetime

try:
    import aiohttp
except ImportError:
    aiohttp = None


class ToolManager:
    """Manages external tools and API integrations for PebbleMind"""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self._init_default_tools()
    
    def _init_default_tools(self):
        """Initialize default tools that are safe and useful"""
        self.register_tool("calculator", self._calculator_tool)
        self.register_tool("web_search", self._web_search_tool)
        self.register_tool("datetime", self._datetime_tool) 
        self.register_tool("file_reader", self._file_reader_tool)
        self.register_tool("code_executor", self._code_executor_tool)
        self.register_tool("wikipedia", self._wikipedia_tool)
    
    def register_tool(self, name: str, func: Callable):
        """Register a new tool with the tool manager"""
        self.tools[name] = func
    
    async def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a registered tool with the provided arguments"""
        if tool_name not in self.tools:
            return {
                "error": f"Tool '{tool_name}' not found",
                "available_tools": list(self.tools.keys())
            }
        
        try:
            result = await self.tools[tool_name](**tool_args)
            return {
                "tool_name": tool_name,
                "result": result,
                "success": True
            }
        except Exception as e:
            return {
                "tool_name": tool_name,
                "error": str(e),
                "success": False
            }
    
    async def parse_and_execute_tools(self, text: str) -> List[Dict[str, Any]]:
        """Parse a text for tool calls and execute them"""
        # Look for tool call patterns: [[tool_name: {"arg1": "value1", "arg2": "value2"}]]
        pattern = r'\[\[(\w+):\s*({.*?})\]\]'
        matches = re.findall(pattern, text, re.DOTALL)
        
        results = []
        for tool_name, args_str in matches:
            try:
                args = json.loads(args_str)
                result = await self.execute_tool(tool_name, args)
                results.append(result)
            except json.JSONDecodeError:
                results.append({
                    "tool_name": tool_name,
                    "error": "Invalid JSON arguments",
                    "success": False
                })
        
        return results
    
    # Default tools implementation
    async def _calculator_tool(self, expression: str) -> str:
        """Safely evaluate mathematical expressions"""
        # Only allow safe mathematical operations
        allowed_chars = set('0123456789+-*/().% ')
        if not all(c in allowed_chars for c in expression):
            raise ValueError("Invalid characters in expression")
        
        try:
            # Use eval safely by restricting to mathematical operations
            result = eval(expression, {"__builtins__": {}}, {})
            return f"Result: {result}"
        except Exception as e:
            raise ValueError(f"Calculation error: {e}")
    
    async def _web_search_tool(self, query: str, num_results: int = 3) -> List[Dict[str, str]]:
        """Perform a web search (using a safe search API)"""
        # This is a placeholder - in a real implementation, you would use
        # a search API like SerpAPI, DuckDuckGo, or Google Custom Search
        # For now, return a mock response
        return [
            {
                "title": f"Mock result for: {query}",
                "url": "https://example.com",
                "snippet": f"Mock search result snippet for query: {query}"
            }
            for _ in range(min(num_results, 3))  # Limit for safety
        ]
    
    async def _datetime_tool(self) -> str:
        """Get current date and time"""
        now = datetime.now()
        return f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    
    async def _file_reader_tool(self, file_path: str) -> str:
        """Read a text file (with safety restrictions)"""
        path = Path(file_path)
        
        # Safety checks
        if not path.is_absolute():
            path = Path.cwd() / path
        else:
            # Prevent directory traversal
            if '..' in str(path) or str(path).startswith('/etc') or str(path).startswith('/usr/bin'):
                raise ValueError("Invalid file path")
        
        # Check if file exists and is in a safe location
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"File does not exist: {path}")
        
        # Check file size (limit to 1MB for safety)
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("File too large to read")
        
        # Check file extension (only text files)
        safe_extensions = {'.txt', '.md', '.py', '.json', '.yaml', '.yml', '.csv', '.log'}
        if path.suffix.lower() not in safe_extensions:
            raise ValueError(f"File type not allowed: {path.suffix}")
        
        try:
            content = path.read_text(encoding='utf-8')
            # Limit content length for safety
            if len(content) > 10000:
                content = content[:10000] + "... [truncated]"
            return content
        except Exception as e:
            raise ValueError(f"Error reading file: {e}")
    
    async def _code_executor_tool(self, language: str, code: str) -> str:
        """Execute code in a safe environment"""
        if language.lower() != "python":
            raise ValueError("Only Python code execution is supported")
        
        # Safety: Only allow specific safe operations
        unsafe_patterns = [
            'import os', 'import sys', 'import subprocess', 'import shutil',
            'open(', 'exec(', 'eval(', 'compile(', '__import__',
            'file', 'input', 'raw_input'
        ]
        
        code_lower = code.lower()
        for pattern in unsafe_patterns:
            if pattern in code_lower:
                raise ValueError(f"Potentially unsafe code detected: {pattern}")
        
        # Create a safe execution environment
        safe_globals = {
            "__builtins__": {
                'len': len, 'str': str, 'int': int, 'float': float,
                'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
                'min': min, 'max': max, 'sum': sum, 'abs': abs,
                'round': round, 'range': range, 'enumerate': enumerate,
                'zip': zip, 'map': map, 'filter': filter, 'sorted': sorted,
                'print': lambda *args: f"Output: {' '.join(map(str, args))}"
            }
        }
        
        try:
            # Execute in a restricted environment
            exec_result = exec(code, safe_globals, {})
            return "Code executed successfully"
        except Exception as e:
            return f"Execution error: {e}"
    
    async def _wikipedia_tool(self, query: str, sentences: int = 3) -> str:
        """Get information from Wikipedia"""
        try:
            if aiohttp is None:
                raise ImportError("aiohttp is required for Wikipedia lookups")
            # Use requests to access Wikipedia API
            # This is a simplified example; a full implementation would need proper error handling
            search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        extract = data.get('extract', 'No summary available')
                        return extract[:500] + "..." if len(extract) > 500 else extract
                    else:
                        return f"Could not find Wikipedia page for '{query}'"
        except Exception as e:
            return f"Error accessing Wikipedia: {e}"


class FunctionCallingManager:
    """Manages function calling capabilities for complex task execution"""
    
    def __init__(self, tool_manager: ToolManager):
        self.tool_manager = tool_manager
    
    async def plan_and_execute(self, task: str) -> Dict[str, Any]:
        """Plan and execute a complex task using multiple tools"""
        # Simple planning: break down the task and call relevant tools
        steps = await self._analyze_task(task)
        results = []
        
        for step in steps:
            tool_result = await self.tool_manager.execute_tool(step["tool"], step["args"])
            results.append({
                "step": step["description"],
                "tool_result": tool_result
            })
        
        return {
            "original_task": task,
            "steps_executed": results,
            "summary": self._summarize_results(results)
        }
    
    async def _analyze_task(self, task: str) -> List[Dict[str, Any]]:
        """Analyze a task and break it down into tool calls"""
        # This is a simplified analysis - in practice, you'd use more sophisticated NLP
        task_lower = task.lower()
        
        steps = []
        
        # Example analysis patterns
        if any(word in task_lower for word in ["time", "date", "now"]):
            steps.append({
                "description": "Get current time",
                "tool": "datetime",
                "args": {}
            })
        
        if any(word in task_lower for word in ["calculate", "compute", "math", "+", "-", "*", "/"]):
            # Try to extract calculation
            calc_pattern = r'([\d\+\-\*\/\(\)\.\s]+)'
            matches = re.findall(calc_pattern, task)
            if matches:
                for expr in matches:
                    if any(op in expr for op in ['+', '-', '*', '/']):
                        steps.append({
                            "description": f"Calculate {expr}",
                            "tool": "calculator",
                            "args": {"expression": expr.strip()}
                        })
                        break  # Only do first calculation found for safety
        
        if any(word in task_lower for word in ["read", "file", "document"]):
            # Extract potential file path (simplified)
            file_pattern = r'["\']([^"\']+\.(txt|md|py|json|yaml|yml|csv))["\']'
            matches = re.findall(file_pattern, task)
            if matches:
                file_path = matches[0][0]  # Get first file found
                steps.append({
                    "description": f"Read file {file_path}",
                    "tool": "file_reader",
                    "args": {"file_path": file_path}
                })
        
        # If no specific tools identified but task seems complex, add web search
        if not steps and len(task.split()) > 5:
            steps.append({
                "description": f"Search web for: {task[:50]}",
                "tool": "web_search",
                "args": {"query": task[:100]}
            })
        
        # Default to at least one step if nothing else found
        if not steps:
            steps.append({
                "description": "Get current time",
                "tool": "datetime",
                "args": {}
            })
        
        return steps
    
    def _summarize_results(self, results: List[Dict[str, Any]]) -> str:
        """Summarize the results of tool execution"""
        summary_parts = []
        for result in results:
            step_desc = result["step"]
            tool_result = result["tool_result"]
            
            if tool_result["success"]:
                summary_parts.append(f"{step_desc}: {tool_result.get('result', 'Completed')}")
            else:
                summary_parts.append(f"{step_desc}: Error - {tool_result.get('error', 'Unknown error')}")
        
        return " | ".join(summary_parts)


# Example usage functions that could be integrated into PebbleMind
async def process_tool_calls(text: str, tool_manager: ToolManager) -> str:
    """Process text that contains embedded tool calls"""
    results = await tool_manager.parse_and_execute_tools(text)
    
    output_parts = []
    for result in results:
        if result["success"]:
            output_parts.append(f"[Tool: {result['tool_name']}] {result['result']}")
        else:
            output_parts.append(f"[Tool: {result['tool_name']}] Error: {result['error']}")
    
    return "\n".join(output_parts)
