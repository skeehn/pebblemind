"""
Chain-of-Thought (CoT) reasoning enhancement for better model performance.

Based on research:
- "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models" (Wei et al., 2022)
- "Large Language Models are Zero-Shot Reasoners" (Kojima et al., 2022)
- "Self-Consistency Improves Chain of Thought Reasoning" (Wang et al., 2022)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio
import re
import logging

logger = logging.getLogger(__name__)


class CoTStrategy(Enum):
    """Chain-of-thought strategies"""
    ZERO_SHOT = "zero_shot"  # "Let's think step by step"
    FEW_SHOT = "few_shot"  # Examples with reasoning
    SELF_CONSISTENCY = "self_consistency"  # Multiple paths, vote
    LEAST_TO_MOST = "least_to_most"  # Break down to simpler problems
    TREE_OF_THOUGHTS = "tree_of_thoughts"  # Explore multiple reasoning paths


@dataclass
class ReasoningStep:
    """Single step in reasoning chain"""
    step_number: int
    description: str
    reasoning: str
    result: Optional[str] = None


@dataclass
class CoTResult:
    """Chain-of-thought reasoning result"""
    final_answer: str
    reasoning_steps: List[ReasoningStep]
    confidence: float
    strategy_used: CoTStrategy
    raw_output: str


class ChainOfThoughtEngine:
    """
    Engine for enhanced reasoning using chain-of-thought techniques.

    Implements multiple CoT strategies to improve model reasoning on complex tasks.
    """

    def __init__(self):
        """Initialize CoT engine"""
        self._zero_shot_triggers = self._build_zero_shot_triggers()
        self._few_shot_examples = self._build_few_shot_examples()

    def _build_zero_shot_triggers(self) -> Dict[str, str]:
        """
        Build zero-shot CoT trigger phrases.

        Research shows simple phrases like "Let's think step by step"
        significantly improve reasoning performance.
        """
        return {
            "default": "Let's think step by step:",
            "detailed": "Let's break this down and think through it carefully, step by step:",
            "methodical": "Let's approach this methodically:\n\n1. First, let's understand what we're trying to solve\n2. Then, let's identify the key information\n3. Next, let's work through the solution\n4. Finally, let's verify our answer",
            "analytical": "Let's analyze this systematically:",
            "problem_solving": "Let's solve this problem step by step, showing all our work:",
        }

    def _build_few_shot_examples(self) -> Dict[str, List[Dict[str, str]]]:
        """Build few-shot CoT examples for different domains"""

        return {
            "math": [
                {
                    "question": "Roger has 5 tennis balls. He buys 2 more cans of tennis balls. Each can has 3 tennis balls. How many tennis balls does he have now?",
                    "reasoning": """Let's think step by step:

Step 1: Roger starts with 5 tennis balls.

Step 2: He buys 2 cans of tennis balls.

Step 3: Each can has 3 tennis balls, so 2 cans have 2 × 3 = 6 tennis balls.

Step 4: Total tennis balls = starting balls + new balls = 5 + 6 = 11

Final Answer: Roger has 11 tennis balls.""",
                    "answer": "11"
                },
                {
                    "question": "The cafeteria had 23 apples. If they used 20 to make lunch and bought 6 more, how many apples do they have?",
                    "reasoning": """Let's think step by step:

Step 1: The cafeteria started with 23 apples.

Step 2: They used 20 apples for lunch, so they have 23 - 20 = 3 apples left.

Step 3: They bought 6 more apples.

Step 4: Total apples = remaining apples + new apples = 3 + 6 = 9

Final Answer: They have 9 apples.""",
                    "answer": "9"
                }
            ],
            "logic": [
                {
                    "question": "If all roses are flowers and some flowers fade quickly, can we conclude that some roses fade quickly?",
                    "reasoning": """Let's think through this logically:

Step 1: Identify what we know:
- All roses are flowers (roses ⊂ flowers)
- Some flowers fade quickly

Step 2: Analyze the logical relationship:
- We know roses are a subset of flowers
- We know SOME flowers fade quickly, but we don't know WHICH flowers

Step 3: Consider what we can and cannot conclude:
- We cannot conclude that roses specifically are among the flowers that fade quickly
- The fading flowers could be roses, or they could be other types of flowers

Step 4: Conclusion:
We CANNOT validly conclude that some roses fade quickly. We would need additional information linking roses to the fading property.

Final Answer: No, this conclusion is not valid.""",
                    "answer": "No"
                }
            ],
            "coding": [
                {
                    "question": "What will this Python code output? x = [1, 2, 3]; y = x; y.append(4); print(x)",
                    "reasoning": """Let's trace through this step by step:

Step 1: x = [1, 2, 3]
- Creates a list and assigns it to variable x
- x now references the list [1, 2, 3]

Step 2: y = x
- This does NOT create a copy!
- y now references the SAME list as x
- Both x and y point to the same object in memory

Step 3: y.append(4)
- Appends 4 to the list that y references
- Since x and y reference the same list, this modifies that shared list
- The list is now [1, 2, 3, 4]

Step 4: print(x)
- Prints the list that x references
- Since x and y share the same list, x reflects the change

Final Answer: [1, 2, 3, 4]""",
                    "answer": "[1, 2, 3, 4]"
                }
            ],
            "science": [
                {
                    "question": "Water boils at 100°C at sea level. If you are on a mountain at high altitude, will water boil at a higher or lower temperature? Explain why.",
                    "reasoning": """Let's think through this step by step:

Step 1: Understand the relationship between pressure and boiling point.
- Boiling occurs when vapor pressure equals atmospheric pressure.
- At sea level, atmospheric pressure is about 101.3 kPa.

Step 2: Consider what happens at high altitude.
- At higher altitudes, there is less atmosphere above you.
- This means atmospheric pressure is lower.

Step 3: Apply the relationship.
- With lower atmospheric pressure, the vapor pressure needed to boil is lower.
- Therefore water reaches its boiling point at a lower temperature.

Step 4: Conclude.
- Water boils at a LOWER temperature at high altitude.
- For example, at the top of Mount Everest (~8,849m), water boils at about 70°C.

Final Answer: Water boils at a lower temperature at high altitude because atmospheric pressure is reduced.""",
                    "answer": "lower"
                },
                {
                    "question": "A ball is thrown straight up in the air. At the very top of its path, what is its speed?",
                    "reasoning": """Let's think through this step by step:

Step 1: Understand the motion.
- The ball is thrown upward with some initial speed.
- Gravity constantly decelerates it at ~9.8 m/s².

Step 2: Analyze what happens as it rises.
- As the ball goes up, gravity slows it down.
- Its upward speed decreases continuously.

Step 3: Consider the top of the path.
- At the very top, the ball momentarily stops before falling back down.
- Its speed has been fully reduced to zero by gravity.
- It has not yet started moving downward.

Step 4: State the answer.
- At the top of its path, the ball's speed is zero.

Final Answer: Zero (0 m/s). The ball momentarily stops at the peak.""",
                    "answer": "zero"
                }
            ],
        }

    def enhance_prompt_zero_shot(
        self,
        question: str,
        style: str = "default"
    ) -> str:
        """
        Add zero-shot CoT trigger to prompt

        Args:
            question: Original question
            style: CoT trigger style

        Returns:
            Enhanced prompt with CoT trigger
        """
        trigger = self._zero_shot_triggers.get(style, self._zero_shot_triggers["default"])

        enhanced = f"""{question}

{trigger}"""

        return enhanced

    def enhance_prompt_few_shot(
        self,
        question: str,
        domain: str = "math",
        num_examples: int = 2
    ) -> List[Dict[str, str]]:
        """
        Create few-shot CoT prompt with examples

        Args:
            question: Question to answer
            domain: Domain for examples (math, logic, coding)
            num_examples: Number of examples to include

        Returns:
            List of messages with examples
        """
        examples = self._few_shot_examples.get(domain, self._few_shot_examples["math"])
        examples = examples[:num_examples]

        messages = []

        # Add examples
        for example in examples:
            messages.append({
                "role": "user",
                "content": example["question"]
            })
            messages.append({
                "role": "assistant",
                "content": example["reasoning"]
            })

        # Add actual question
        messages.append({
            "role": "user",
            "content": f"{question}\n\nLet's think step by step:"
        })

        return messages

    def parse_reasoning_steps(self, text: str) -> List[ReasoningStep]:
        """
        Parse reasoning steps from model output

        Args:
            text: Model output with reasoning

        Returns:
            List of reasoning steps
        """
        steps = []

        # Match patterns like "Step 1:", "1.", "First,", etc.
        step_patterns = [
            r"Step (\d+):\s*(.+?)(?=Step \d+:|Final Answer:|$)",
            r"(\d+)\.\s*(.+?)(?=\d+\.|Final Answer:|$)",
        ]

        for pattern in step_patterns:
            matches = re.finditer(pattern, text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                step_num = int(match.group(1))
                step_content = match.group(2).strip()

                steps.append(ReasoningStep(
                    step_number=step_num,
                    description=step_content[:100] + "..." if len(step_content) > 100 else step_content,
                    reasoning=step_content
                ))

        # If no structured steps found, treat as single step
        if not steps:
            steps.append(ReasoningStep(
                step_number=1,
                description="Complete reasoning",
                reasoning=text
            ))

        return steps

    def extract_final_answer(self, text: str) -> Optional[str]:
        """
        Extract final answer from reasoning output

        Args:
            text: Model output

        Returns:
            Extracted answer or None
        """
        # Look for explicit "Final Answer:" or similar
        answer_patterns = [
            r"Final Answer:\s*(.+?)(?:\n|$)",
            r"Answer:\s*(.+?)(?:\n|$)",
            r"Therefore,\s*(.+?)(?:\n|$)",
            r"The answer is\s*(.+?)(?:\n|$)",
        ]

        for pattern in answer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # If no explicit answer marker, return last line
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if lines:
            return lines[-1]

        return None

    async def reason_with_self_consistency(
        self,
        question: str,
        generate_func,
        num_paths: int = 5,
        **kwargs
    ) -> CoTResult:
        """
        Use self-consistency to improve reasoning accuracy.

        Generates multiple reasoning paths and selects most consistent answer.

        Args:
            question: Question to answer
            generate_func: Async function to generate responses
            num_paths: Number of reasoning paths to explore
            **kwargs: Additional arguments for generate_func

        Returns:
            CoT result with highest confidence answer
        """
        logger.info(f"Reasoning with self-consistency ({num_paths} paths)")

        # Generate multiple reasoning paths
        enhanced_prompt = self.enhance_prompt_zero_shot(question, style="detailed")

        tasks = [
            generate_func(enhanced_prompt, **kwargs)
            for _ in range(num_paths)
        ]

        responses = await asyncio.gather(*tasks)

        # Extract answers from each path
        answers = []
        reasoning_outputs = []

        for response in responses:
            answer = self.extract_final_answer(response)
            if answer:
                answers.append(answer)
                reasoning_outputs.append(response)

        # Vote for most common answer
        if not answers:
            return CoTResult(
                final_answer="Unable to determine answer",
                reasoning_steps=[],
                confidence=0.0,
                strategy_used=CoTStrategy.SELF_CONSISTENCY,
                raw_output="No valid answers generated"
            )

        # Count votes
        vote_counts = {}
        for answer in answers:
            vote_counts[answer] = vote_counts.get(answer, 0) + 1

        # Select answer with most votes
        best_answer = max(vote_counts.keys(), key=lambda k: vote_counts[k])
        confidence = vote_counts[best_answer] / len(answers)

        # Find reasoning for best answer
        best_idx = answers.index(best_answer)
        best_reasoning = reasoning_outputs[best_idx]

        steps = self.parse_reasoning_steps(best_reasoning)

        logger.info(
            f"Self-consistency result: '{best_answer}' "
            f"({vote_counts[best_answer]}/{len(answers)} votes, "
            f"confidence: {confidence:.2%})"
        )

        return CoTResult(
            final_answer=best_answer,
            reasoning_steps=steps,
            confidence=confidence,
            strategy_used=CoTStrategy.SELF_CONSISTENCY,
            raw_output=best_reasoning
        )

    def create_least_to_most_prompt(
        self,
        complex_problem: str,
        subproblems: Optional[List[str]] = None
    ) -> str:
        """
        Create least-to-most decomposition prompt

        Args:
            complex_problem: Complex problem to solve
            subproblems: Optional pre-defined subproblems

        Returns:
            Enhanced prompt with decomposition
        """
        if subproblems:
            subproblem_list = "\n".join(
                f"{i+1}. {sub}" for i, sub in enumerate(subproblems)
            )
            prompt = f"""Complex Problem: {complex_problem}

Let's break this down into simpler subproblems and solve them one by one:

Subproblems:
{subproblem_list}

Now, let's solve each subproblem:"""
        else:
            prompt = f"""Complex Problem: {complex_problem}

Let's use the least-to-most prompting approach:

Step 1: Break down this complex problem into simpler subproblems.

Step 2: Solve each subproblem from simplest to most complex.

Step 3: Combine the solutions to solve the original problem.

Let's begin:"""

        return prompt


# Global CoT engine
_cot_engine: Optional[ChainOfThoughtEngine] = None


def get_cot_engine() -> ChainOfThoughtEngine:
    """Get global CoT engine instance"""
    global _cot_engine
    if _cot_engine is None:
        _cot_engine = ChainOfThoughtEngine()
    return _cot_engine
