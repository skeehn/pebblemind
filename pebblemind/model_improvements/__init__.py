"""
Model improvement systems for PebbleMind.

Comprehensive model enhancement features:
- Prompt templates for different task types
- Dynamic parameter selection
- Chain-of-thought reasoning
- Context optimization
- RAG reranking
- Fine-tuning pipeline
- Model ensembling
- Auto-evaluation

These improvements make the models perform significantly better without
changing the underlying neural network weights.
"""

from .prompt_templates import (
    TaskType,
    PromptTemplate,
    PromptTemplateLibrary,
    get_template_library
)

from .dynamic_parameters import (
    SamplingParameters,
    ParameterPreset,
    DynamicParameterSelector,
    get_parameter_selector
)

from .chain_of_thought import (
    CoTStrategy,
    ReasoningStep,
    CoTResult,
    ChainOfThoughtEngine,
    get_cot_engine
)

from .context_optimizer import (
    CompressionStrategy,
    ContextWindow,
    ContextOptimizer,
    get_context_optimizer
)

from .rag_reranker import (
    RerankingStrategy,
    RankedDocument,
    RAGReranker,
    get_reranker
)

from .finetuning import (
    FineTuningMethod,
    LoRAConfig,
    TrainingConfig,
    TrainingExample,
    FineTuningPipeline,
    get_finetuning_pipeline
)

from .ensembling import (
    EnsembleStrategy,
    ModelConfig,
    EnsembleResult,
    ModelEnsemble,
    get_ensemble
)

from .auto_evaluation import (
    EvaluationMetric,
    EvaluationExample,
    EvaluationResult,
    AutoEvaluator,
    get_evaluator
)

__all__ = [
    # Prompt templates
    "TaskType",
    "PromptTemplate",
    "PromptTemplateLibrary",
    "get_template_library",

    # Dynamic parameters
    "SamplingParameters",
    "ParameterPreset",
    "DynamicParameterSelector",
    "get_parameter_selector",

    # Chain-of-thought
    "CoTStrategy",
    "ReasoningStep",
    "CoTResult",
    "ChainOfThoughtEngine",
    "get_cot_engine",

    # Context optimization
    "CompressionStrategy",
    "ContextWindow",
    "ContextOptimizer",
    "get_context_optimizer",

    # RAG reranking
    "RerankingStrategy",
    "RankedDocument",
    "RAGReranker",
    "get_reranker",

    # Fine-tuning
    "FineTuningMethod",
    "LoRAConfig",
    "TrainingConfig",
    "TrainingExample",
    "FineTuningPipeline",
    "get_finetuning_pipeline",

    # Ensembling
    "EnsembleStrategy",
    "ModelConfig",
    "EnsembleResult",
    "ModelEnsemble",
    "get_ensemble",

    # Auto-evaluation
    "EvaluationMetric",
    "EvaluationExample",
    "EvaluationResult",
    "AutoEvaluator",
    "get_evaluator",
]
