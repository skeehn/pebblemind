"""
Dynamic parameter selection for optimal model performance.

Automatically adjusts sampling parameters based on task type for best results.
Based on research and empirical testing across different task categories.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from .prompt_templates import TaskType

logger = logging.getLogger(__name__)


@dataclass
class SamplingParameters:
    """Model sampling parameters"""
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    max_tokens: Optional[int] = None
    stop_sequences: Optional[list] = None


class ParameterPreset(Enum):
    """Pre-configured parameter presets"""
    PRECISE = "precise"  # Factual, deterministic tasks
    BALANCED = "balanced"  # General purpose
    CREATIVE = "creative"  # Creative, diverse outputs
    CODING = "coding"  # Code generation
    REASONING = "reasoning"  # Logical reasoning tasks


class DynamicParameterSelector:
    """
    Intelligently select sampling parameters based on task type.

    Research-backed parameter selection:
    - Low temperature (0.1-0.3) for factual/precise tasks
    - Medium temperature (0.6-0.8) for balanced tasks
    - High temperature (0.8-1.0) for creative tasks
    - Higher top_k for diverse outputs
    - Repeat penalty to avoid loops
    """

    def __init__(self):
        """Initialize parameter selector"""
        self._presets = self._build_presets()
        self._task_mappings = self._build_task_mappings()

    def _build_presets(self) -> Dict[ParameterPreset, SamplingParameters]:
        """Build parameter presets based on research"""

        return {
            # PRECISE - For factual, deterministic tasks
            # Low temperature for focused, accurate outputs
            ParameterPreset.PRECISE: SamplingParameters(
                temperature=0.2,
                top_p=0.9,
                top_k=20,
                repeat_penalty=1.05,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                max_tokens=None,
                stop_sequences=None
            ),

            # BALANCED - General purpose, conversational
            # Medium temperature for natural outputs
            ParameterPreset.BALANCED: SamplingParameters(
                temperature=0.7,
                top_p=0.9,
                top_k=40,
                repeat_penalty=1.1,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                max_tokens=None,
                stop_sequences=None
            ),

            # CREATIVE - For creative, diverse outputs
            # High temperature for variety and creativity
            ParameterPreset.CREATIVE: SamplingParameters(
                temperature=0.9,
                top_p=0.95,
                top_k=50,
                repeat_penalty=1.15,
                frequency_penalty=0.3,
                presence_penalty=0.3,
                max_tokens=None,
                stop_sequences=None
            ),

            # CODING - Code generation and technical tasks
            # Lower temperature for correctness, higher top_p for idioms
            ParameterPreset.CODING: SamplingParameters(
                temperature=0.3,
                top_p=0.95,
                top_k=30,
                repeat_penalty=1.05,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                max_tokens=None,
                stop_sequences=["```\n\n", "---", "###"]
            ),

            # REASONING - Logical, step-by-step reasoning
            # Low temperature for logical consistency
            ParameterPreset.REASONING: SamplingParameters(
                temperature=0.3,
                top_p=0.9,
                top_k=25,
                repeat_penalty=1.1,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                max_tokens=None,
                stop_sequences=None
            ),
        }

    def _build_task_mappings(self) -> Dict[TaskType, ParameterPreset]:
        """Map task types to optimal parameter presets"""

        return {
            # Precise tasks
            TaskType.MATH: ParameterPreset.REASONING,
            TaskType.REASONING: ParameterPreset.REASONING,
            TaskType.QUESTION_ANSWERING: ParameterPreset.PRECISE,
            TaskType.CLASSIFICATION: ParameterPreset.PRECISE,
            TaskType.EXTRACTION: ParameterPreset.PRECISE,
            TaskType.SUMMARIZATION: ParameterPreset.PRECISE,

            # Coding tasks
            TaskType.CODE_GENERATION: ParameterPreset.CODING,
            TaskType.CODE_EXPLANATION: ParameterPreset.CODING,
            TaskType.CODE_REVIEW: ParameterPreset.CODING,
            TaskType.DEBUGGING: ParameterPreset.CODING,

            # Creative tasks
            TaskType.CREATIVE_WRITING: ParameterPreset.CREATIVE,
            TaskType.BRAINSTORMING: ParameterPreset.CREATIVE,

            # Balanced tasks
            TaskType.CONVERSATION: ParameterPreset.BALANCED,
            TaskType.ANALYSIS: ParameterPreset.BALANCED,
            TaskType.TECHNICAL_WRITING: ParameterPreset.BALANCED,
            TaskType.INSTRUCTION_FOLLOWING: ParameterPreset.BALANCED,
            TaskType.TRANSLATION: ParameterPreset.BALANCED,
        }

    def get_parameters(
        self,
        task_type: Optional[TaskType] = None,
        preset: Optional[ParameterPreset] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> SamplingParameters:
        """
        Get optimal sampling parameters

        Args:
            task_type: Type of task (auto-selects preset)
            preset: Explicit preset to use
            overrides: Manual parameter overrides

        Returns:
            Optimized sampling parameters
        """

        # Determine preset
        if preset:
            selected_preset = preset
        elif task_type:
            selected_preset = self._task_mappings.get(
                task_type,
                ParameterPreset.BALANCED
            )
        else:
            selected_preset = ParameterPreset.BALANCED

        # Get base parameters
        params = self._presets[selected_preset]

        # Apply overrides if provided
        if overrides:
            params_dict = {
                "temperature": overrides.get("temperature", params.temperature),
                "top_p": overrides.get("top_p", params.top_p),
                "top_k": overrides.get("top_k", params.top_k),
                "repeat_penalty": overrides.get("repeat_penalty", params.repeat_penalty),
                "frequency_penalty": overrides.get("frequency_penalty", params.frequency_penalty),
                "presence_penalty": overrides.get("presence_penalty", params.presence_penalty),
                "max_tokens": overrides.get("max_tokens", params.max_tokens),
                "stop_sequences": overrides.get("stop_sequences", params.stop_sequences),
            }
            params = SamplingParameters(**params_dict)

        logger.debug(
            f"Selected parameters for {task_type or preset}: "
            f"temp={params.temperature}, top_p={params.top_p}"
        )

        return params

    def get_parameters_dict(
        self,
        task_type: Optional[TaskType] = None,
        preset: Optional[ParameterPreset] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get parameters as dictionary for LLM API

        Args:
            task_type: Type of task
            preset: Explicit preset
            overrides: Manual overrides

        Returns:
            Parameters as dict
        """
        params = self.get_parameters(task_type, preset, overrides)

        result = {
            "temperature": params.temperature,
            "top_p": params.top_p,
            "top_k": params.top_k,
            "repeat_penalty": params.repeat_penalty,
        }

        # Add optional parameters if set
        if params.frequency_penalty != 0.0:
            result["frequency_penalty"] = params.frequency_penalty

        if params.presence_penalty != 0.0:
            result["presence_penalty"] = params.presence_penalty

        if params.max_tokens:
            result["max_tokens"] = params.max_tokens

        if params.stop_sequences:
            result["stop"] = params.stop_sequences

        return result

    def explain_parameters(
        self,
        task_type: Optional[TaskType] = None,
        preset: Optional[ParameterPreset] = None
    ) -> str:
        """
        Get human-readable explanation of parameter choices

        Args:
            task_type: Type of task
            preset: Explicit preset

        Returns:
            Explanation string
        """
        params = self.get_parameters(task_type, preset)

        selected_preset = preset or self._task_mappings.get(
            task_type,
            ParameterPreset.BALANCED
        )

        explanations = {
            ParameterPreset.PRECISE: (
                "Using PRECISE parameters:\n"
                f"- Low temperature ({params.temperature}) for accurate, focused outputs\n"
                f"- Moderate top_p ({params.top_p}) for controlled randomness\n"
                f"- Small top_k ({params.top_k}) for consistency\n"
                "Best for: factual tasks, Q&A, extraction"
            ),
            ParameterPreset.BALANCED: (
                "Using BALANCED parameters:\n"
                f"- Medium temperature ({params.temperature}) for natural outputs\n"
                f"- Standard top_p ({params.top_p}) for good variety\n"
                f"- Moderate top_k ({params.top_k}) for balance\n"
                "Best for: conversation, general tasks"
            ),
            ParameterPreset.CREATIVE: (
                "Using CREATIVE parameters:\n"
                f"- High temperature ({params.temperature}) for diverse outputs\n"
                f"- High top_p ({params.top_p}) for creativity\n"
                f"- Large top_k ({params.top_k}) for variety\n"
                f"- Penalties ({params.frequency_penalty}/{params.presence_penalty}) to reduce repetition\n"
                "Best for: creative writing, brainstorming"
            ),
            ParameterPreset.CODING: (
                "Using CODING parameters:\n"
                f"- Low-medium temperature ({params.temperature}) for correct code\n"
                f"- High top_p ({params.top_p}) to capture idiomatic patterns\n"
                f"- Moderate top_k ({params.top_k}) for consistency\n"
                "Best for: code generation, debugging"
            ),
            ParameterPreset.REASONING: (
                "Using REASONING parameters:\n"
                f"- Low temperature ({params.temperature}) for logical consistency\n"
                f"- Standard top_p ({params.top_p}) for focused reasoning\n"
                f"- Small top_k ({params.top_k}) for deterministic steps\n"
                "Best for: math, logic, step-by-step reasoning"
            ),
        }

        return explanations.get(selected_preset, "Using default parameters")


# Global parameter selector
_parameter_selector: Optional[DynamicParameterSelector] = None


def get_parameter_selector() -> DynamicParameterSelector:
    """Get global parameter selector instance"""
    global _parameter_selector
    if _parameter_selector is None:
        _parameter_selector = DynamicParameterSelector()
    return _parameter_selector
