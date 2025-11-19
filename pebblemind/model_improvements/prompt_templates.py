"""
Advanced prompt template system with task-specific optimization.

Research-backed prompt engineering for maximum model performance across different task types.
Based on research from OpenAI, Anthropic, and academic papers on prompt optimization.
"""

from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of tasks with optimized prompts"""
    CODE_GENERATION = "code_generation"
    CODE_EXPLANATION = "code_explanation"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    CREATIVE_WRITING = "creative_writing"
    TECHNICAL_WRITING = "technical_writing"
    SUMMARIZATION = "summarization"
    QUESTION_ANSWERING = "question_answering"
    REASONING = "reasoning"
    MATH = "math"
    ANALYSIS = "analysis"
    TRANSLATION = "translation"
    CONVERSATION = "conversation"
    INSTRUCTION_FOLLOWING = "instruction_following"
    BRAINSTORMING = "brainstorming"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"


@dataclass
class PromptTemplate:
    """Structured prompt template"""
    system_prompt: str
    user_template: str
    assistant_prefix: Optional[str] = None
    few_shot_examples: Optional[List[Dict[str, str]]] = None
    constraints: Optional[List[str]] = None
    output_format: Optional[str] = None


class PromptTemplateLibrary:
    """
    Library of research-backed optimized prompts for different tasks.

    Based on findings from:
    - "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models" (Wei et al., 2022)
    - "Large Language Models are Zero-Shot Reasoners" (Kojima et al., 2022)
    - "Self-Consistency Improves Chain of Thought Reasoning" (Wang et al., 2022)
    - OpenAI and Anthropic prompt engineering guides
    """

    def __init__(self):
        """Initialize template library"""
        self._templates = self._build_templates()

    def _build_templates(self) -> Dict[TaskType, PromptTemplate]:
        """Build optimized templates for each task type"""

        templates = {
            # CODE GENERATION - Optimized for clarity and best practices
            TaskType.CODE_GENERATION: PromptTemplate(
                system_prompt="""You are an expert software engineer with deep knowledge of best practices, design patterns, and clean code principles.

Your code should be:
- Clean and readable with clear variable names
- Well-documented with docstrings
- Type-annotated where applicable
- Following language-specific best practices
- Handling edge cases appropriately
- Efficient and optimized

Always explain your approach before writing code.""",
                user_template="""Task: {task}

Requirements:
{requirements}

Language: {language}

Please think through the approach, then provide clean, production-ready code.""",
                assistant_prefix="Let me break down the approach:\n\n",
                few_shot_examples=[
                    {
                        "user": "Write a function to check if a string is a palindrome in Python",
                        "assistant": """Let me break down the approach:

1. We'll normalize the string (lowercase, remove non-alphanumeric)
2. Compare the string with its reverse
3. Return boolean result

Here's the implementation:

```python
def is_palindrome(s: str) -> bool:
    \"\"\"
    Check if a string is a palindrome.

    Args:
        s: Input string to check

    Returns:
        True if palindrome, False otherwise

    Examples:
        >>> is_palindrome("A man a plan a canal Panama")
        True
        >>> is_palindrome("hello")
        False
    \"\"\"
    # Normalize: lowercase and keep only alphanumeric
    normalized = ''.join(c.lower() for c in s if c.isalnum())

    # Check if equal to reverse
    return normalized == normalized[::-1]
```

This handles edge cases like empty strings, mixed case, and punctuation."""
                    }
                ]
            ),

            # REASONING - Chain-of-Thought optimization
            TaskType.REASONING: PromptTemplate(
                system_prompt="""You are a logical reasoning expert. When solving problems:

1. Break down complex problems into smaller steps
2. State your assumptions clearly
3. Show your reasoning process
4. Verify your conclusions
5. Consider alternative approaches

Always think step-by-step and explain your reasoning.""",
                user_template="""Problem: {problem}

Let's approach this step-by-step:""",
                assistant_prefix="Let me think through this carefully:\n\nStep 1: ",
                constraints=[
                    "Show all reasoning steps",
                    "State assumptions explicitly",
                    "Verify the final answer"
                ]
            ),

            # MATH - Optimized for accuracy
            TaskType.MATH: PromptTemplate(
                system_prompt="""You are a mathematics expert. When solving math problems:

1. Read the problem carefully and identify what's being asked
2. List known values and unknowns
3. Show each step of your calculation
4. Verify your answer makes sense
5. State the final answer clearly

Always work step-by-step and check your work.""",
                user_template="""Math Problem: {problem}

Please solve this step-by-step, showing all work:""",
                assistant_prefix="Let me solve this step-by-step:\n\nGiven:\n",
                output_format="End with 'Final Answer: [answer]'"
            ),

            # SUMMARIZATION - Concise and comprehensive
            TaskType.SUMMARIZATION: PromptTemplate(
                system_prompt="""You are an expert at creating clear, concise summaries that capture the most important information.

Your summaries should:
- Identify and include key points
- Maintain factual accuracy
- Be well-organized
- Match the requested length
- Preserve essential context""",
                user_template="""Text to summarize:

{text}

Length: {length} (brief/medium/detailed)

Please provide a {length} summary focusing on the main points:""",
                constraints=[
                    "Stay factual - don't add information not in the source",
                    "Prioritize the most important information",
                    "Use clear, concise language"
                ]
            ),

            # QUESTION ANSWERING - Accurate and sourced
            TaskType.QUESTION_ANSWERING: PromptTemplate(
                system_prompt="""You are a knowledgeable assistant providing accurate, helpful answers.

Guidelines:
- Answer based on the provided context when available
- Be clear when you're uncertain
- Provide specific examples when helpful
- Cite sources or context when answering
- Admit knowledge limitations

Always prioritize accuracy over speculation.""",
                user_template="""Context:
{context}

Question: {question}

Based on the context above, please provide a clear, accurate answer:""",
                constraints=[
                    "Base answer on provided context",
                    "Clearly indicate if information is not in context",
                    "Be concise but complete"
                ]
            ),

            # CREATIVE WRITING - Engaging and original
            TaskType.CREATIVE_WRITING: PromptTemplate(
                system_prompt="""You are a creative writer skilled at crafting engaging, original content.

Your writing should:
- Be imaginative and original
- Have strong narrative flow
- Use vivid, descriptive language
- Engage the reader's emotions
- Match the requested style and tone

Let your creativity flow while maintaining coherence.""",
                user_template="""Writing Task: {task}

Style/Tone: {style}
Length: {length}

Additional requirements:
{requirements}

Please write engaging, original content:""",
                assistant_prefix=""  # No prefix for creative tasks
            ),

            # CODE REVIEW - Thorough and constructive
            TaskType.CODE_REVIEW: PromptTemplate(
                system_prompt="""You are an experienced code reviewer focused on helping developers improve their code.

Review for:
- Correctness and bugs
- Performance issues
- Security vulnerabilities
- Code style and readability
- Best practices
- Edge cases

Be constructive and specific in your feedback.""",
                user_template="""Please review this code:

```{language}
{code}
```

Provide a thorough review covering correctness, performance, security, and style:""",
                output_format="""Format as:
✅ Strengths: [list]
⚠️ Issues: [list with severity]
💡 Suggestions: [specific improvements]
🔧 Revised code: [if needed]"""
            ),

            # ANALYSIS - Deep and structured
            TaskType.ANALYSIS: PromptTemplate(
                system_prompt="""You are an analytical expert skilled at deep analysis and insight extraction.

Your analysis should:
- Identify patterns and trends
- Examine multiple perspectives
- Consider implications
- Support claims with evidence
- Organize findings logically

Provide thorough, well-structured analysis.""",
                user_template="""Data/Topic to analyze:

{content}

Analysis focus: {focus}

Please provide a comprehensive analysis:""",
                output_format="""Structure as:
1. Overview
2. Key Findings
3. Detailed Analysis
4. Implications
5. Conclusions"""
            ),

            # CONVERSATION - Natural and helpful
            TaskType.CONVERSATION: PromptTemplate(
                system_prompt="""You are a helpful, friendly AI assistant.

Conversation style:
- Natural and conversational
- Helpful and informative
- Respectful and professional
- Adaptive to user's tone
- Clear and concise

Maintain context and provide useful responses.""",
                user_template="{message}",
                assistant_prefix=""
            ),

            # BRAINSTORMING - Creative and diverse
            TaskType.BRAINSTORMING: PromptTemplate(
                system_prompt="""You are a creative brainstorming partner excellent at generating diverse, innovative ideas.

Brainstorming approach:
- Generate many ideas (quantity breeds quality)
- Think outside the box
- Build on concepts
- Consider different perspectives
- No idea is too wild initially

Let's explore possibilities together.""",
                user_template="""Brainstorming topic: {topic}

Context: {context}

Let's generate creative ideas for this. Please provide diverse approaches:""",
                constraints=[
                    "Generate at least 5-10 distinct ideas",
                    "Vary the approaches",
                    "Include both conventional and unconventional ideas"
                ]
            ),

            # DEBUGGING - Systematic problem solving
            TaskType.DEBUGGING: PromptTemplate(
                system_prompt="""You are a debugging expert who systematically identifies and fixes issues.

Debugging process:
1. Understand the problem and expected behavior
2. Analyze the code for potential issues
3. Identify the root cause
4. Propose a fix
5. Explain why the fix works

Be methodical and thorough.""",
                user_template="""Code with issue:

```{language}
{code}
```

Error/Problem: {error}

Please help debug this issue:""",
                assistant_prefix="Let me analyze this systematically:\n\n1. Understanding the issue:\n",
                output_format="""Format as:
🔍 Root Cause: [explanation]
🔧 Fix: [code changes]
✅ Why this works: [explanation]
🧪 How to test: [verification steps]"""
            ),

            # CLASSIFICATION - Accurate categorization
            TaskType.CLASSIFICATION: PromptTemplate(
                system_prompt="""You are a classification expert skilled at accurate categorization.

Classification approach:
- Analyze key features carefully
- Consider all categories
- Apply consistent criteria
- Provide confidence levels when appropriate
- Explain your reasoning

Be precise and consistent.""",
                user_template="""Content to classify:

{content}

Categories: {categories}

Please classify this content and explain your reasoning:""",
                output_format="""Format as:
Category: [chosen category]
Confidence: [high/medium/low]
Reasoning: [explanation]
Alternative categories: [if applicable]"""
            ),

            # EXTRACTION - Precise information extraction
            TaskType.EXTRACTION: PromptTemplate(
                system_prompt="""You are an information extraction expert skilled at identifying and extracting specific data.

Extraction guidelines:
- Find exactly what's requested
- Maintain original formatting when relevant
- Preserve accuracy
- Indicate if information is not found
- Be systematic and thorough

Extract precisely what's needed.""",
                user_template="""Source text:

{text}

Extract: {targets}

Please extract the requested information:""",
                output_format="""Format as structured data:
{
  "field1": "extracted value",
  "field2": "extracted value",
  ...
}"""
            ),
        }

        return templates

    def get_template(self, task_type: TaskType) -> PromptTemplate:
        """
        Get optimized template for task type

        Args:
            task_type: Type of task

        Returns:
            Optimized prompt template
        """
        template = self._templates.get(task_type)
        if not template:
            logger.warning(f"No template found for {task_type}, using conversation default")
            return self._templates[TaskType.CONVERSATION]
        return template

    def format_prompt(
        self,
        task_type: TaskType,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Format a complete prompt from template

        Args:
            task_type: Type of task
            **kwargs: Variables to fill in template

        Returns:
            Formatted prompt components
        """
        template = self.get_template(task_type)

        # Format user message
        try:
            user_message = template.user_template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing required variable for template: {e}")
            user_message = template.user_template

        result = {
            "system_prompt": template.system_prompt,
            "user_message": user_message,
            "assistant_prefix": template.assistant_prefix,
            "few_shot_examples": template.few_shot_examples,
            "constraints": template.constraints,
            "output_format": template.output_format
        }

        return result

    def build_messages(
        self,
        task_type: TaskType,
        include_examples: bool = True,
        **kwargs
    ) -> List[Dict[str, str]]:
        """
        Build complete message list for LLM

        Args:
            task_type: Type of task
            include_examples: Include few-shot examples
            **kwargs: Template variables

        Returns:
            List of messages in chat format
        """
        formatted = self.format_prompt(task_type, **kwargs)

        messages = []

        # Add system message
        messages.append({
            "role": "system",
            "content": formatted["system_prompt"]
        })

        # Add few-shot examples if available and requested
        if include_examples and formatted["few_shot_examples"]:
            for example in formatted["few_shot_examples"]:
                messages.append({
                    "role": "user",
                    "content": example["user"]
                })
                messages.append({
                    "role": "assistant",
                    "content": example["assistant"]
                })

        # Add user message
        messages.append({
            "role": "user",
            "content": formatted["user_message"]
        })

        return messages


# Global template library
_template_library: Optional[PromptTemplateLibrary] = None


def get_template_library() -> PromptTemplateLibrary:
    """Get global template library instance"""
    global _template_library
    if _template_library is None:
        _template_library = PromptTemplateLibrary()
    return _template_library
