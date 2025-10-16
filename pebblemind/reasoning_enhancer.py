"""Enhanced reasoning capabilities for PebbleMind"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from enum import Enum


logger = logging.getLogger(__name__)


class ReasoningType(Enum):
    """Types of reasoning capabilities"""
    LOGICAL = "logical"
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    PROBLEM_SOLVING = "problem_solving"
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"


class ReasoningEnhancer:
    """Enhances the intelligent reasoning capabilities of PebbleMind"""
    
    def __init__(self):
        self.reasoning_prompts = {
            ReasoningType.LOGICAL: (
                "Analyze this logically step by step. Identify premises, assumptions, and conclusions. "
                "Ensure each step follows logically from the previous one."
            ),
            ReasoningType.ANALYTICAL: (
                "Break this down into smaller components. Examine each part systematically. "
                "Consider different perspectives and factors that influence the situation."
            ),
            ReasoningType.CREATIVE: (
                "Think outside the box. Consider unconventional approaches and perspectives. "
                "Brainstorm multiple possibilities and connections."
            ),
            ReasoningType.PROBLEM_SOLVING: (
                "Identify the core problem. Generate potential solutions. "
                "Evaluate each solution based on feasibility and effectiveness. "
                "Recommend the best approach with reasoning."
            ),
            ReasoningType.DEDUCTIVE: (
                "Apply general rules or principles to this specific case. "
                "Derive specific conclusions from general premises."
            ),
            ReasoningType.INDUCTIVE: (
                "Draw general principles from specific examples or observations. "
                "Identify patterns and trends to form broader conclusions."
            )
        }
        
        self.reasoning_chain_templates = {
            "basic": [
                "First, let's understand what is being asked.",
                "Next, analyze the relevant information.",
                "Then, apply appropriate reasoning techniques.",
                "Finally, draw a conclusion or provide an answer."
            ],
            "complex": [
                "1. Define the problem or question clearly.",
                "2. Gather and analyze relevant information.",
                "3. Consider different approaches and perspectives.",
                "4. Apply logical frameworks and reasoning techniques.",
                "5. Evaluate potential solutions or conclusions.",
                "6. Synthesize findings into a coherent response.",
                "7. Consider limitations and potential alternatives."
            ]
        }

    def enhance_prompt(self, 
                      original_prompt: str, 
                      reasoning_type: ReasoningType = ReasoningType.ANALYTICAL,
                      use_chain_of_thought: bool = True) -> str:
        """Enhance a prompt with reasoning directives"""
        enhanced_parts = []
        
        # Add reasoning directive
        enhanced_parts.append(self.reasoning_prompts[reasoning_type])
        
        # Add chain of thought if requested
        if use_chain_of_thought:
            chain_template = self.reasoning_chain_templates["complex"]
            chain_text = "Please think through this step by step:\n" + "\n".join([f"{i+1}. {step}" for i, step in enumerate(chain_template)])
            enhanced_parts.append(chain_text)
        
        # Add original prompt
        enhanced_parts.append(f"Question: {original_prompt}")
        
        # Add request for explicit reasoning
        enhanced_parts.append(
            "Think aloud as you work through this problem. "
            "Explain your reasoning process clearly so that others can follow your logic."
        )
        
        return "\n\n".join(enhanced_parts)

    async def apply_reasoning_pipeline(self, 
                                     query: str, 
                                     context: Optional[List[str]] = None,
                                     reasoning_type: ReasoningType = ReasoningType.ANALYTICAL) -> Dict[str, Any]:
        """Apply a comprehensive reasoning pipeline to a query"""
        
        # Structure the reasoning process
        structured_query = self.enhance_prompt(query, reasoning_type)
        
        # Add any provided context
        if context:
            structured_query = f"Context:\n{' '.join(context)}\n\n{structured_query}"
        
        # Return the enhanced query and reasoning metadata
        return {
            "enhanced_query": structured_query,
            "reasoning_type": reasoning_type.value,
            "applied_techniques": ["chain_of_thought", reasoning_type.value],
            "context_included": bool(context)
        }

    def evaluate_reasoning_quality(self, response: str) -> Dict[str, float]:
        """Evaluate the quality of reasoning in a response"""
        metrics = {
            "coherence": 0.0,
            "logical_flow": 0.0,
            "evidence_support": 0.0,
            "completeness": 0.0
        }
        
        # Simple heuristics for reasoning quality
        # Look for reasoning indicators
        response_lower = response.lower()
        
        # Check for logical connectors and structure
        logical_indicators = [
            "because", "therefore", "consequently", "thus", "hence",
            "first", "second", "finally", "next", "then", "also",
            "however", "but", "although", "on the other hand",
            "this means", "this suggests", "this implies"
        ]
        
        coherence_score = sum(1 for indicator in logical_indicators if indicator in response_lower)
        metrics["coherence"] = min(1.0, coherence_score / 10.0)
        
        # Check for step-by-step structure
        step_indicators = ["step", "first", "second", "third", "finally", "next"]
        logical_flow_score = sum(1 for indicator in step_indicators if indicator in response_lower)
        metrics["logical_flow"] = min(1.0, logical_flow_score / 5.0)
        
        # Check for completeness
        avg_sentence_length = len(response.split()) / max(1, len(response.split('.')))
        if avg_sentence_length > 8:  # More detailed responses tend to be more complete
            metrics["completeness"] = min(1.0, len(response) / 1000)
        
        return metrics

    def explain_reasoning(self, input_text: str, response: str) -> str:
        """Generate an explanation of the reasoning process"""
        explanation_parts = [
            "## Reasoning Process Explanation",
            f"**Input:** {input_text}",
            f"**Response:** {response[:200]}{'...' if len(response) > 200 else ''}",
            "",
            "**Applied Reasoning Techniques:**",
            "- Chain of thought reasoning",
            f"- {self._get_reasoning_type_from_response(response).value} approach",
            "",
            "**Quality Assessment:**",
            f"- Coherence: {self.evaluate_reasoning_quality(response)['coherence']:.2f}",
            f"- Logical Flow: {self.evaluate_reasoning_quality(response)['logical_flow']:.2f}",
            f"- Completeness: {self.evaluate_reasoning_quality(response)['completeness']:.2f}",
        ]
        
        return "\n".join(explanation_parts)

    def _get_reasoning_type_from_response(self, response: str) -> ReasoningType:
        """Attempt to determine the reasoning type from the response"""
        response_lower = response.lower()
        
        # Look for keywords that indicate specific reasoning types
        if any(word in response_lower for word in ["analyze", "break down", "components", "parts"]):
            return ReasoningType.ANALYTICAL
        elif any(word in response_lower for word in ["solve", "solution", "approach", "method"]):
            return ReasoningType.PROBLEM_SOLVING
        elif any(word in response_lower for word in ["logical", "reason", "follows", "implies"]):
            return ReasoningType.LOGICAL
        elif any(word in response_lower for word in ["alternative", "creative", "innovative", "think outside"]):
            return ReasoningType.CREATIVE
        else:
            # Default to analytical for general reasoning
            return ReasoningType.ANALYTICAL