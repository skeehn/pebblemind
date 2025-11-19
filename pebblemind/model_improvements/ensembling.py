"""
Model ensembling for improved quality through multiple model collaboration.

Combines outputs from multiple models to achieve better results than any single model.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging
from collections import Counter

logger = logging.getLogger(__name__)


class EnsembleStrategy(Enum):
    """Ensemble combination strategies"""
    VOTING = "voting"  # Majority vote
    WEIGHTED_VOTING = "weighted_voting"  # Vote with model weights
    BEST_OF_N = "best_of_n"  # Select best by quality metric
    MIXTURE_OF_EXPERTS = "mixture_of_experts"  # Route to specialist
    AVERAGING = "averaging"  # Average probabilities


@dataclass
class ModelConfig:
    """Configuration for a model in the ensemble"""
    name: str
    model_size: str  # "1.5b", "3b", "7b"
    weight: float = 1.0
    specialty: Optional[str] = None  # "code", "math", "creative"


@dataclass
class EnsembleResult:
    """Result from ensemble"""
    final_answer: str
    confidence: float
    individual_results: List[Dict[str, Any]]
    strategy_used: EnsembleStrategy


class ModelEnsemble:
    """
    Ensemble multiple models for better performance.

    Features:
    - Multiple voting strategies
    - Weighted combinations
    - Specialist routing
    - Confidence scoring
    """

    def __init__(self, models: List[ModelConfig]):
        """
        Initialize ensemble

        Args:
            models: List of model configurations
        """
        self.models = models
        logger.info(f"Initialized ensemble with {len(models)} models")

    async def generate(
        self,
        prompt: str,
        generate_funcs: Dict[str, Callable],
        strategy: EnsembleStrategy = EnsembleStrategy.VOTING,
        **kwargs
    ) -> EnsembleResult:
        """
        Generate response using ensemble

        Args:
            prompt: Input prompt
            generate_funcs: Dict mapping model names to generate functions
            strategy: Ensemble strategy
            **kwargs: Additional generation parameters

        Returns:
            Ensemble result
        """
        logger.info(f"Generating with ensemble ({strategy.value})")

        # Generate from all models in parallel
        tasks = []
        for model in self.models:
            if model.name in generate_funcs:
                task = generate_funcs[model.name](prompt, **kwargs)
                tasks.append((model, task))

        results = await asyncio.gather(*[task for _, task in tasks])

        # Combine results using strategy
        individual_results = []
        for (model, _), result in zip(tasks, results):
            individual_results.append({
                "model": model.name,
                "result": result,
                "weight": model.weight
            })

        if strategy == EnsembleStrategy.VOTING:
            final_result = self._voting(individual_results)
        elif strategy == EnsembleStrategy.WEIGHTED_VOTING:
            final_result = self._weighted_voting(individual_results)
        elif strategy == EnsembleStrategy.BEST_OF_N:
            final_result = self._best_of_n(individual_results, prompt)
        else:
            final_result = self._voting(individual_results)

        return EnsembleResult(
            final_answer=final_result["answer"],
            confidence=final_result["confidence"],
            individual_results=individual_results,
            strategy_used=strategy
        )

    def _voting(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simple majority voting"""
        answers = [r["result"] for r in results]

        # Count votes
        vote_counts = Counter(answers)
        best_answer, count = vote_counts.most_common(1)[0]

        confidence = count / len(answers)

        return {
            "answer": best_answer,
            "confidence": confidence
        }

    def _weighted_voting(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Voting with model weights"""
        vote_scores = {}

        for result in results:
            answer = result["result"]
            weight = result["weight"]

            if answer not in vote_scores:
                vote_scores[answer] = 0
            vote_scores[answer] += weight

        # Select answer with highest weighted score
        best_answer = max(vote_scores.keys(), key=lambda k: vote_scores[k])
        total_weight = sum(r["weight"] for r in results)
        confidence = vote_scores[best_answer] / total_weight

        return {
            "answer": best_answer,
            "confidence": confidence
        }

    def _best_of_n(
        self,
        results: List[Dict[str, Any]],
        prompt: str
    ) -> Dict[str, Any]:
        """Select best result by quality heuristic"""
        # Score each result
        scored = []
        for result in results:
            answer = result["result"]
            score = self._quality_score(prompt, answer)
            scored.append((answer, score))

        # Select best
        best_answer, best_score = max(scored, key=lambda x: x[1])

        return {
            "answer": best_answer,
            "confidence": best_score
        }

    def _quality_score(self, prompt: str, answer: str) -> float:
        """
        Heuristic quality score for an answer

        Args:
            prompt: Original prompt
            answer: Generated answer

        Returns:
            Quality score (0.0 to 1.0)
        """
        score = 0.5  # Baseline

        # Longer answers might be more detailed (up to a point)
        if 50 < len(answer) < 500:
            score += 0.1
        elif len(answer) >= 500:
            score += 0.05

        # Contains code blocks (for technical questions)
        if "```" in answer:
            score += 0.1

        # Well-structured (has paragraphs)
        if answer.count('\n\n') > 0:
            score += 0.1

        # Answers question words from prompt
        question_words = ["what", "how", "why", "when", "where", "who"]
        if any(word in prompt.lower() for word in question_words):
            # Check if answer is substantive
            if len(answer) > 100:
                score += 0.15

        return min(score, 1.0)

    async def route_to_specialist(
        self,
        prompt: str,
        task_type: str,
        generate_funcs: Dict[str, Callable],
        **kwargs
    ) -> str:
        """
        Route prompt to specialist model

        Args:
            prompt: Input prompt
            task_type: Type of task (code, math, creative, etc.)
            generate_funcs: Generate functions
            **kwargs: Generation parameters

        Returns:
            Generated response
        """
        # Find specialist for this task
        specialist = None
        for model in self.models:
            if model.specialty == task_type:
                specialist = model
                break

        # Fallback to largest model
        if not specialist:
            specialist = max(self.models, key=lambda m: m.model_size)

        logger.info(f"Routing {task_type} task to {specialist.name}")

        # Generate
        if specialist.name in generate_funcs:
            return await generate_funcs[specialist.name](prompt, **kwargs)
        else:
            raise ValueError(f"No generate function for {specialist.name}")


# Global ensemble
_ensemble: Optional[ModelEnsemble] = None


def get_ensemble(models: List[ModelConfig]) -> ModelEnsemble:
    """Get model ensemble instance"""
    global _ensemble
    if _ensemble is None:
        _ensemble = ModelEnsemble(models)
    return _ensemble
