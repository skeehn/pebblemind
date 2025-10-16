"""Specialized Agent Modules for PebbleMind"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod
from datetime import datetime


class BaseAgent(ABC):
    """Base class for specialized agents"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.execution_history: List[Dict[str, Any]] = []
    
    @abstractmethod
    async def execute(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute the agent's specialized task"""
        pass
    
    def add_to_history(self, task: str, result: Dict[str, Any]):
        """Add execution to history"""
        self.execution_history.append({
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "result": result
        })
    
    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get execution history"""
        return self.execution_history[-limit:]


class ResearchAgent(BaseAgent):
    """Agent specialized for research tasks"""
    
    def __init__(self):
        super().__init__(
            name="ResearchAgent", 
            description="Specialized in gathering and synthesizing information from various sources"
        )
    
    async def execute(self, task: str, search_query: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Execute a research task"""
        if not search_query:
            search_query = task
        
        # Use the tool manager to search
        from .tool_integration import ToolManager
        tool_manager = ToolManager()
        
        # Perform web search
        search_result = await tool_manager.execute_tool("web_search", {"query": search_query})
        
        # Perform Wikipedia search as well
        wiki_result = await tool_manager.execute_tool("wikipedia", {"query": search_query.split()[0] if search_query.split() else search_query})  # Use first word for Wikipedia
        
        # Synthesize results
        synthesis = self._synthesize_results(search_result.get("result", []), wiki_result.get("result", ""))
        
        result = {
            "task": task,
            "search_results": search_result.get("result", []),
            "wikipedia_result": wiki_result.get("result", ""),
            "synthesis": synthesis,
            "agent": self.name
        }
        
        self.add_to_history(task, result)
        return result
    
    def _synthesize_results(self, search_results: List[Dict], wiki_result: str) -> str:
        """Synthesize search and wiki results into a coherent summary"""
        summary_parts = []
        
        if wiki_result and "error" not in wiki_result.lower():
            summary_parts.append(f"From Wikipedia: {wiki_result}")
        
        if search_results:
            summary_parts.append("Key search findings:")
            for i, result in enumerate(search_results[:3]):  # Take top 3 results
                summary_parts.append(f"{i+1}. {result.get('title', 'No title')}: {result.get('snippet', 'No snippet')[:100]}...")
        
        return " | ".join(summary_parts)


class CodeAgent(BaseAgent):
    """Agent specialized for code-related tasks"""
    
    def __init__(self):
        super().__init__(
            name="CodeAgent", 
            description="Specialized in programming, code explanation, and debugging"
        )
    
    async def execute(self, task: str, code: str = "", language: str = "python", **kwargs) -> Dict[str, Any]:
        """Execute a code-related task"""
        from .tool_integration import ToolManager
        tool_manager = ToolManager()
        
        result_parts = []
        
        # If we have code, try to analyze or execute it
        if code:
            # Try to execute code if it's safe
            if language.lower() == "python":
                exec_result = await tool_manager.execute_tool("code_executor", {"language": language, "code": code})
                result_parts.append(f"Execution result: {exec_result}")
            
            # Add code explanation
            result_parts.append(f"Code analysis for {language} code: {self._explain_code(code, language)}")
        
        # For general coding tasks, provide assistance
        else:
            result_parts.append(f"Code assistance for task: {task}")
            result_parts.append(self._provide_coding_assistance(task))
        
        result = {
            "task": task,
            "code": code,
            "language": language,
            "result": " | ".join(result_parts),
            "agent": self.name
        }
        
        self.add_to_history(task, result)
        return result
    
    def _explain_code(self, code: str, language: str) -> str:
        """Provide a simple explanation of the code (simplified implementation)"""
        lines = code.split('\n')
        line_count = len([l for l in lines if l.strip()])
        char_count = len(code)
        return f"Code has {line_count} lines and {char_count} characters. Language: {language}."
    
    def _provide_coding_assistance(self, task: str) -> str:
        """Provide coding assistance based on the task"""
        if "debug" in task.lower() or "error" in task.lower():
            return "To debug, try checking syntax, variable names, and logic flow."
        elif "algorithm" in task.lower():
            return "Consider the time and space complexity of your algorithm."
        else:
            return "For programming tasks, consider breaking the problem into smaller functions."


class MathAgent(BaseAgent):
    """Agent specialized for mathematical calculations"""
    
    def __init__(self):
        super().__init__(
            name="MathAgent", 
            description="Specialized in mathematical calculations and problem solving"
        )
    
    async def execute(self, task: str, expression: str = "", **kwargs) -> Dict[str, Any]:
        """Execute a mathematical task"""
        from .tool_integration import ToolManager
        tool_manager = ToolManager()
        
        # Try to extract expression from task if not provided
        if not expression:
            expression = self._extract_math_expression(task)
        
        result_parts = []
        
        if expression:
            # Perform calculation
            calc_result = await tool_manager.execute_tool("calculator", {"expression": expression})
            result_parts.append(f"Calculation result: {calc_result.get('result', calc_result.get('error', 'Could not calculate'))}")
        
        # Add problem-solving approach
        result_parts.append(f"Mathematical approach: {self._solve_math_problem(task)}")
        
        result = {
            "task": task,
            "expression": expression,
            "result": " | ".join(result_parts),
            "agent": self.name
        }
        
        self.add_to_history(task, result)
        return result
    
    def _extract_math_expression(self, text: str) -> str:
        """Extract mathematical expressions from text"""
        import re
        # Look for mathematical expressions with numbers and operators
        patterns = [
            r'([\d\+\-\*\/\(\)\.\s]+)',  # Basic expressions
            r'(\d+\s*[\+\-\*\/]\s*\d+)',  # Simple operations
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Return the first valid-looking expression
                expr = matches[0].strip()
                # Filter to only include mathematical characters
                clean_expr = ''.join(c for c in expr if c in '0123456789+-*/().% ')
                if len(clean_expr) > 2:  # At least 2 characters
                    return clean_expr
        
        return ""
    
    def _solve_math_problem(self, task: str) -> str:
        """Provide a general approach to solving math problems"""
        if any(word in task.lower() for word in ["solve", "find", "calculate"]):
            return "Identify given values, apply appropriate formula, calculate result, verify answer."
        elif any(word in task.lower() for word in ["equation", "formula"]):
            return "Rearrange equation to isolate the variable, then solve step by step."
        else:
            return "Break the problem into smaller parts, identify what is being asked, and apply mathematical principles."


class WritingAgent(BaseAgent):
    """Agent specialized for writing and text editing tasks"""
    
    def __init__(self):
        super().__init__(
            name="WritingAgent", 
            description="Specialized in content creation, editing, and writing assistance"
        )
    
    async def execute(self, task: str, text: str = "", **kwargs) -> Dict[str, Any]:
        """Execute a writing-related task"""
        result_parts = []
        
        # If we have text to work with, process it
        if text:
            result_parts.append(f"Processed text: {self._process_text(text, task)}")
        
        # Provide writing assistance
        result_parts.append(f"Writing assistance: {self._provide_writing_help(task)}")
        
        result = {
            "task": task,
            "input_text": text,
            "result": " | ".join(result_parts),
            "agent": self.name
        }
        
        self.add_to_history(task, result)
        return result
    
    def _process_text(self, text: str, task: str) -> str:
        """Process text based on the task requested"""
        if "summarize" in task.lower() or "summary" in task.lower():
            words = text.split()
            if len(words) > 50:  # Only summarize if it's long enough
                return " ".join(words[:min(50, len(words))]) + " [truncated for summary]"
            else:
                return text
        elif "grammar" in task.lower() or "edit" in task.lower():
            return f"Text reviewed for grammar and style: {text[:100]}..."
        else:
            return text
    
    def _provide_writing_help(self, task: str) -> str:
        """Provide writing assistance based on the task"""
        if "outline" in task.lower():
            return "Start with main points, add supporting details, ensure logical flow."
        elif "improve" in task.lower() or "better" in task.lower():
            return "Consider your audience, be clear and concise, use active voice when possible."
        elif "tone" in task.lower():
            return "Match your tone to your purpose and audience - professional, casual, persuasive, etc."
        else:
            return "Focus on clarity, organization, and your intended message when writing."


class AgentOrchestrator:
    """Orchestrates specialized agents for complex tasks"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {
            "research": ResearchAgent(),
            "code": CodeAgent(),
            "math": MathAgent(),
            "writing": WritingAgent()
        }
        self.fallback_agent = CodeAgent()  # Default fallback agent
    
    async def route_task(self, task: str) -> Dict[str, Any]:
        """Route a task to the most appropriate specialized agent"""
        # Determine which agent is most appropriate based on task content
        task_lower = task.lower()
        
        # Determine the most appropriate agent
        if any(word in task_lower for word in ["research", "find", "search", "information", "lookup", "wikipedia"]):
            agent = self.agents["research"]
        elif any(word in task_lower for word in ["code", "program", "python", "javascript", "debug", "function", "algorithm"]):
            agent = self.agents["code"]
        elif any(word in task_lower for word in ["calculate", "math", "equation", "solve", "formula", "compute"]):
            agent = self.agents["math"]
        elif any(word in task_lower for word in ["write", "text", "outline", "edit", "improve", "draft", "summary"]):
            agent = self.agents["writing"]
        else:
            # Use a simple heuristic to choose the best agent
            if any(word in task_lower for word in ["data", "analyze", "study", "learn"]):
                agent = self.agents["research"]
            elif any(char in task_lower for char in ["=", "calculate", "+", "-", "*", "/"]):
                agent = self.agents["math"]
            else:
                # Default to code agent for general processing
                agent = self.fallback_agent
        
        # Execute the task with the chosen agent
        result = await agent.execute(task)
        return result
    
    def register_agent(self, name: str, agent: BaseAgent):
        """Register a new specialized agent"""
        self.agents[name] = agent
    
    def get_available_agents(self) -> List[str]:
        """Get list of available agents"""
        return list(self.agents.keys())
    
    async def execute_with_agent(self, agent_name: str, task: str, **kwargs) -> Dict[str, Any]:
        """Execute a task with a specific agent"""
        if agent_name not in self.agents:
            raise ValueError(f"Agent '{agent_name}' not found. Available: {list(self.agents.keys())}")
        
        return await self.agents[agent_name].execute(task, **kwargs)


# Example usage functions that could be integrated into PebbleMind
async def get_specialized_response(task: str, orchestrator: AgentOrchestrator) -> str:
    """Get response from the most appropriate specialized agent"""
    result = await orchestrator.route_task(task)
    return result["result"]