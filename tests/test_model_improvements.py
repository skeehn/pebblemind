"""Comprehensive tests for model improvement features"""

import pytest
import asyncio
from pathlib import Path

from pebblemind.model_improvements import (
    # Prompt templates
    TaskType,
    get_template_library,

    # Dynamic parameters
    ParameterPreset,
    get_parameter_selector,

    # Chain-of-thought
    CoTStrategy,
    get_cot_engine,

    # Context optimization
    CompressionStrategy,
    get_context_optimizer,

    # RAG reranking
    RerankingStrategy,
    get_reranker,

    # Fine-tuning
    TrainingExample,
    get_finetuning_pipeline,

    # Ensembling
    ModelConfig,
    EnsembleStrategy,
    get_ensemble,

    # Auto-evaluation
    EvaluationExample,
    get_evaluator,
)


# ========== Prompt Templates Tests ==========

def test_prompt_template_library():
    """Test prompt template library"""
    library = get_template_library()
    assert library is not None

    # Test getting template
    code_template = library.get_template(TaskType.CODE_GENERATION)
    assert code_template is not None
    assert "expert" in code_template.system_prompt.lower()


def test_format_prompt():
    """Test prompt formatting"""
    library = get_template_library()

    formatted = library.format_prompt(
        TaskType.CODE_GENERATION,
        task="Write a function",
        requirements="Must handle edge cases",
        language="Python"
    )

    assert "task" in formatted["user_message"].lower()
    assert "python" in formatted["user_message"].lower()


def test_build_messages():
    """Test building complete message list"""
    library = get_template_library()

    messages = library.build_messages(
        TaskType.MATH,
        problem="Solve: 2x + 5 = 15",
        include_examples=False
    )

    assert len(messages) >= 2  # System + user
    assert messages[0]["role"] == "system"
    assert messages[-1]["role"] == "user"


# ========== Dynamic Parameters Tests ==========

def test_parameter_selector():
    """Test dynamic parameter selection"""
    selector = get_parameter_selector()
    assert selector is not None


def test_get_parameters_for_task():
    """Test getting parameters for different tasks"""
    selector = get_parameter_selector()

    # Code task should have lower temperature
    code_params = selector.get_parameters(task_type=TaskType.CODE_GENERATION)
    assert code_params.temperature < 0.5

    # Creative task should have higher temperature
    creative_params = selector.get_parameters(task_type=TaskType.CREATIVE_WRITING)
    assert creative_params.temperature > 0.7


def test_parameter_overrides():
    """Test parameter overrides"""
    selector = get_parameter_selector()

    params = selector.get_parameters(
        task_type=TaskType.CODE_GENERATION,
        overrides={"temperature": 0.5, "max_tokens": 1000}
    )

    assert params.temperature == 0.5
    assert params.max_tokens == 1000


def test_parameters_dict():
    """Test getting parameters as dict"""
    selector = get_parameter_selector()

    params_dict = selector.get_parameters_dict(task_type=TaskType.MATH)

    assert "temperature" in params_dict
    assert "top_p" in params_dict
    assert isinstance(params_dict["temperature"], float)


# ========== Chain-of-Thought Tests ==========

def test_cot_engine():
    """Test CoT engine initialization"""
    engine = get_cot_engine()
    assert engine is not None


def test_zero_shot_enhancement():
    """Test zero-shot CoT enhancement"""
    engine = get_cot_engine()

    question = "What is 15 + 27?"
    enhanced = engine.enhance_prompt_zero_shot(question)

    assert "step" in enhanced.lower()
    assert question in enhanced


def test_few_shot_enhancement():
    """Test few-shot CoT enhancement"""
    engine = get_cot_engine()

    question = "Roger has 5 tennis balls. He buys 2 cans with 3 balls each. How many total?"
    messages = engine.enhance_prompt_few_shot(question, domain="math")

    assert len(messages) >= 3  # Should have examples + question
    assert any("step" in msg["content"].lower() for msg in messages)


def test_parse_reasoning_steps():
    """Test parsing reasoning steps"""
    engine = get_cot_engine()

    text = """Step 1: First, let's identify what we know.
Step 2: Calculate the intermediate result.
Step 3: Get the final answer.

Final Answer: 42"""

    steps = engine.parse_reasoning_steps(text)
    assert len(steps) >= 3


def test_extract_final_answer():
    """Test extracting final answer"""
    engine = get_cot_engine()

    text = "Let's solve this step by step. Final Answer: 42"
    answer = engine.extract_final_answer(text)

    assert "42" in answer


@pytest.mark.asyncio
async def test_self_consistency():
    """Test self-consistency reasoning"""
    engine = get_cot_engine()

    async def mock_generate(prompt, **kwargs):
        return "Step 1: Calculate. Final Answer: 42"

    result = await engine.reason_with_self_consistency(
        "What is 2 + 2?",
        mock_generate,
        num_paths=3
    )

    assert result.final_answer is not None
    assert result.confidence > 0


# ========== Context Optimization Tests ==========

def test_context_optimizer():
    """Test context optimizer initialization"""
    optimizer = get_context_optimizer(max_context_tokens=2048)
    assert optimizer is not None
    assert optimizer.max_context_tokens == 2048


def test_count_tokens():
    """Test token counting"""
    optimizer = get_context_optimizer()

    text = "Hello, world! This is a test."
    tokens = optimizer.count_tokens(text)

    assert tokens > 0
    assert tokens < len(text)  # Should be less than character count


def test_optimize_context_sliding_window():
    """Test sliding window context optimization"""
    optimizer = get_context_optimizer(max_context_tokens=100)

    messages = [
        {"role": "user", "content": "Message 1" * 20},
        {"role": "assistant", "content": "Response 1" * 20},
        {"role": "user", "content": "Message 2" * 20},
        {"role": "assistant", "content": "Response 2" * 20},
    ]

    context = optimizer.optimize_context(
        messages,
        max_tokens=100,
        strategy=CompressionStrategy.SLIDING_WINDOW
    )

    assert context.total_tokens <= 100
    assert len(context.messages) > 0


def test_format_messages_for_llm():
    """Test formatting optimized context"""
    optimizer = get_context_optimizer()

    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]

    context = optimizer.optimize_context(messages)
    formatted = optimizer.format_messages_for_llm(
        context,
        system_message="You are a helpful assistant"
    )

    assert formatted[0]["role"] == "system"
    assert len(formatted) > 1


# ========== RAG Reranking Tests ==========

def test_reranker():
    """Test reranker initialization"""
    reranker = get_reranker()
    assert reranker is not None


@pytest.mark.asyncio
async def test_simple_rerank():
    """Test simple reranking"""
    reranker = get_reranker()

    query = "machine learning"
    documents = [
        {"content": "Deep learning is a subset of machine learning", "score": 0.7},
        {"content": "Python is a programming language", "score": 0.3},
        {"content": "Machine learning uses algorithms to learn", "score": 0.8},
    ]

    result = await reranker.rerank(
        query,
        documents,
        top_k=2,
        strategy=RerankingStrategy.RECIPROCAL_RANK_FUSION
    )

    assert len(result.documents) == 2
    assert result.documents[0].rank == 1


@pytest.mark.asyncio
async def test_mmr_rerank():
    """Test MMR reranking for diversity"""
    reranker = get_reranker()

    query = "AI"
    documents = [
        {"content": "AI and machine learning" * 10, "score": 0.9},
        {"content": "AI and deep learning" * 10, "score": 0.85},  # Similar to first
        {"content": "Natural language processing" * 10, "score": 0.7},  # Different topic
    ]

    result = await reranker.rerank(
        query,
        documents,
        top_k=2,
        strategy=RerankingStrategy.MMR
    )

    assert len(result.documents) == 2


# ========== Fine-Tuning Tests ==========

def test_finetuning_pipeline(tmp_path):
    """Test fine-tuning pipeline initialization"""
    pipeline = get_finetuning_pipeline(
        base_model_path="models/test",
        output_dir=tmp_path / "finetuned"
    )

    assert pipeline is not None
    assert pipeline.output_dir.exists()


def test_prepare_training_dataset():
    """Test preparing training dataset"""
    pipeline = get_finetuning_pipeline("models/test", Path("output"))

    examples = [
        TrainingExample(
            instruction="Translate to French",
            input="Hello",
            output="Bonjour"
        ) for _ in range(10)
    ]

    datasets = pipeline.prepare_dataset(examples, validation_split=0.2)

    assert "train" in datasets
    assert "validation" in datasets
    assert len(datasets["train"]) == 8
    assert len(datasets["validation"]) == 2


def test_format_training_example():
    """Test formatting training examples"""
    pipeline = get_finetuning_pipeline("models/test", Path("output"))

    example = TrainingExample(
        instruction="Write a function",
        input="to add two numbers",
        output="def add(a, b): return a + b"
    )

    formatted = pipeline.format_example(example)

    assert "instruction" in formatted.lower()
    assert "input" in formatted.lower()
    assert "response" in formatted.lower()


# ========== Ensembling Tests ==========

def test_ensemble_initialization():
    """Test ensemble initialization"""
    models = [
        ModelConfig(name="model1", model_size="1.5b", weight=1.0),
        ModelConfig(name="model2", model_size="3b", weight=1.5),
    ]

    ensemble = get_ensemble(models)
    assert ensemble is not None
    assert len(ensemble.models) == 2


@pytest.mark.asyncio
async def test_ensemble_voting():
    """Test ensemble voting"""
    models = [
        ModelConfig(name="model1", model_size="1.5b"),
        ModelConfig(name="model2", model_size="3b"),
        ModelConfig(name="model3", model_size="7b"),
    ]

    ensemble = get_ensemble(models)

    async def gen1(prompt, **kwargs):
        return "Answer A"

    async def gen2(prompt, **kwargs):
        return "Answer A"

    async def gen3(prompt, **kwargs):
        return "Answer B"

    generate_funcs = {
        "model1": gen1,
        "model2": gen2,
        "model3": gen3,
    }

    result = await ensemble.generate(
        "Test question",
        generate_funcs,
        strategy=EnsembleStrategy.VOTING
    )

    assert result.final_answer == "Answer A"  # Majority
    assert result.confidence >= 0.5


# ========== Auto-Evaluation Tests ==========

def test_evaluator():
    """Test evaluator initialization"""
    evaluator = get_evaluator()
    assert evaluator is not None


def test_get_benchmarks():
    """Test getting available benchmarks"""
    evaluator = get_evaluator()

    benchmarks = evaluator.get_benchmark_names()

    assert "math" in benchmarks
    assert "reasoning" in benchmarks
    assert "code" in benchmarks


@pytest.mark.asyncio
async def test_evaluate():
    """Test model evaluation"""
    evaluator = get_evaluator()

    async def mock_generate(prompt, **kwargs):
        if "15 + 27" in prompt:
            return "42"
        elif "120 km" in prompt:
            return "60 km/h"
        return "Answer"

    result = await evaluator.evaluate(
        mock_generate,
        benchmark_name="math"
    )

    assert result.examples_tested > 0
    assert "accuracy" in result.metric_scores or "exact_match" in result.metric_scores


@pytest.mark.asyncio
async def test_compare_models():
    """Test comparing multiple models"""
    evaluator = get_evaluator()

    async def good_model(prompt, **kwargs):
        return "42" if "+" in prompt else "Answer"

    async def bad_model(prompt, **kwargs):
        return "Wrong answer"

    generate_funcs = {
        "good": good_model,
        "bad": bad_model,
    }

    results = await evaluator.compare_models(generate_funcs, benchmark_name="math")

    assert "good" in results
    assert "bad" in results
    # Good model should have higher exact_match score
    assert results["good"].metric_scores.get("exact_match", 0) > results["bad"].metric_scores.get("exact_match", 0)


def test_add_custom_benchmark():
    """Test adding custom benchmark"""
    evaluator = get_evaluator()

    custom_examples = [
        EvaluationExample(
            input="Test question",
            expected_output="Test answer",
            category="custom"
        )
    ]

    evaluator.add_benchmark("custom_test", custom_examples)

    assert "custom_test" in evaluator.get_benchmark_names()


# ========== Expanded Benchmark Tests ==========

def test_expanded_benchmarks():
    """Test that expanded benchmark suites have multiple examples"""
    evaluator = get_evaluator()

    benchmarks = evaluator.get_benchmark_names()

    # Verify new benchmark categories exist
    assert "knowledge" in benchmarks
    assert "reading_comprehension" in benchmarks

    # Verify expanded math benchmark has more examples
    math_examples = evaluator.benchmarks["math"]
    assert len(math_examples) >= 5, f"Expected >=5 math examples, got {len(math_examples)}"

    # Verify expanded reasoning benchmark has more examples
    reasoning_examples = evaluator.benchmarks["reasoning"]
    assert len(reasoning_examples) >= 3, f"Expected >=3 reasoning examples, got {len(reasoning_examples)}"

    # Verify knowledge benchmark
    knowledge_examples = evaluator.benchmarks["knowledge"]
    assert len(knowledge_examples) >= 3

    # Verify reading comprehension benchmark
    rc_examples = evaluator.benchmarks["reading_comprehension"]
    assert len(rc_examples) >= 2


@pytest.mark.asyncio
async def test_evaluate_knowledge_benchmark():
    """Test evaluation on knowledge benchmark"""
    evaluator = get_evaluator()

    async def mock_knowledge_model(prompt, **kwargs):
        if "chemical symbol" in prompt.lower():
            return "The chemical symbol for water is H2O."
        elif "closest to the sun" in prompt.lower():
            return "Mercury is the closest planet to the Sun."
        elif "capital of france" in prompt.lower():
            return "The capital of France is Paris."
        elif "hexagon" in prompt.lower():
            return "A hexagon has 6 sides."
        elif "web browsers" in prompt.lower():
            return "JavaScript is known for its use in web browsers."
        return "I don't know."

    result = await evaluator.evaluate(
        mock_knowledge_model,
        benchmark_name="knowledge"
    )

    assert result.examples_tested == 5
    assert result.passed >= 4  # Good mock should get most right


@pytest.mark.asyncio
async def test_evaluate_reading_comprehension():
    """Test evaluation on reading comprehension benchmark"""
    evaluator = get_evaluator()

    async def mock_rc_model(prompt, **kwargs):
        if "who created python" in prompt.lower():
            return "Guido van Rossum created Python."
        elif "deep learning" in prompt.lower() and "machine learning" in prompt.lower():
            return "Yes, deep learning is a type of machine learning."
        elif "how long" in prompt.lower() and "orbit" in prompt.lower():
            return "One orbit takes approximately 365.25 days."
        return "I don't know."

    result = await evaluator.evaluate(
        mock_rc_model,
        benchmark_name="reading_comprehension"
    )

    assert result.examples_tested == 3
    assert result.passed >= 2


# ========== AI Baseline Comparison Tests ==========

def test_ai_baseline_scores():
    """Test that AI baseline scores are available and well-structured"""
    evaluator = get_evaluator()

    baselines = evaluator.get_ai_baseline_scores()

    # Verify key models are present
    assert "GPT-4" in baselines
    assert "GPT-3.5-Turbo" in baselines
    assert "Llama-2-7B" in baselines

    # Verify scores are in valid range [0, 1]
    for model_name, scores in baselines.items():
        for bench_name, score in scores.items():
            assert 0.0 <= score <= 1.0, (
                f"{model_name}/{bench_name} score {score} out of range"
            )

    # Verify GPT-4 scores higher than Llama-2-7B across all benchmarks
    for bench_name in baselines["GPT-4"]:
        if bench_name in baselines["Llama-2-7B"]:
            assert baselines["GPT-4"][bench_name] > baselines["Llama-2-7B"][bench_name], (
                f"GPT-4 should beat Llama-2-7B on {bench_name}"
            )


@pytest.mark.asyncio
async def test_compare_against_ai_baselines():
    """Test comparing model output against AI baselines"""
    evaluator = get_evaluator()

    async def mock_model(prompt, **kwargs):
        # A decent mock model that gets some answers right
        if "15 + 27" in prompt:
            return "42"
        elif "17 * 23" in prompt:
            return "391"
        elif "120 km" in prompt:
            return "60 km/h"
        elif "48 apples" in prompt:
            return "21 apples"
        elif "144 / 12" in prompt:
            return "12"
        elif "area" in prompt.lower():
            return "40 square cm"
        elif "$25 per week" in prompt:
            return "$200"
        elif "3^4" in prompt or "3 to the power" in prompt:
            return "81"
        return "I don't know"

    comparison = await evaluator.compare_against_ai_baselines(
        mock_model,
        benchmark_names=["math"]
    )

    # Verify comparison structure
    assert "our_model" in comparison
    assert "baselines" in comparison
    assert "rankings" in comparison

    # Verify our model's scores are present
    assert "math" in comparison["our_model"]["scores"]
    our_math_score = comparison["our_model"]["scores"]["math"]
    assert 0.0 <= our_math_score <= 1.0

    # Verify ranking includes our model
    math_ranking = comparison["rankings"]["math"]
    our_entry = [r for r in math_ranking if r["model"] == "PebbleMind (ours)"]
    assert len(our_entry) == 1
    assert our_entry[0]["rank"] >= 1

    # Verify ranking includes baseline models
    model_names = [r["model"] for r in math_ranking]
    assert "GPT-4" in model_names


@pytest.mark.asyncio
async def test_compare_baselines_multiple_benchmarks():
    """Test AI baseline comparison across multiple benchmarks"""
    evaluator = get_evaluator()

    async def mock_model(prompt, **kwargs):
        if "15 + 27" in prompt:
            return "42"
        elif "roses" in prompt.lower():
            return "No, we cannot conclude that."
        elif "cats" in prompt.lower() and "water" in prompt.lower():
            return "Yes, all cats need water."
        return "I'm not sure"

    comparison = await evaluator.compare_against_ai_baselines(
        mock_model,
        benchmark_names=["math", "reasoning"]
    )

    # Both benchmarks should have rankings
    assert "math" in comparison["rankings"]
    assert "reasoning" in comparison["rankings"]


# ========== New CoT Domain Tests ==========

def test_science_few_shot_enhancement():
    """Test few-shot CoT enhancement with science domain"""
    engine = get_cot_engine()

    question = "Why does ice float on water?"
    messages = engine.enhance_prompt_few_shot(question, domain="science")

    assert len(messages) >= 3  # At least 2 examples + question
    # Verify science examples are used
    assert any("boil" in msg["content"].lower() or "temperature" in msg["content"].lower()
               for msg in messages)
    assert any("step" in msg["content"].lower() for msg in messages)


# ========== New Prompt Template Tests ==========

def test_code_explanation_template():
    """Test that CODE_EXPLANATION template exists and is well-formed"""
    library = get_template_library()

    template = library.get_template(TaskType.CODE_EXPLANATION)
    assert template is not None
    assert "explain" in template.system_prompt.lower() or "educator" in template.system_prompt.lower()

    messages = library.build_messages(
        TaskType.CODE_EXPLANATION,
        language="Python",
        code="x = 42",
        level="beginner",
        include_examples=False
    )
    assert len(messages) >= 2
    assert messages[0]["role"] == "system"
    assert "python" in messages[-1]["content"].lower()


def test_technical_writing_template():
    """Test that TECHNICAL_WRITING template exists and is well-formed"""
    library = get_template_library()

    template = library.get_template(TaskType.TECHNICAL_WRITING)
    assert template is not None
    assert "technical" in template.system_prompt.lower()

    messages = library.build_messages(
        TaskType.TECHNICAL_WRITING,
        topic="API Documentation",
        audience="developers",
        format="markdown",
        requirements="Include examples",
        include_examples=False
    )
    assert len(messages) >= 2


def test_translation_template():
    """Test that TRANSLATION template exists and is well-formed"""
    library = get_template_library()

    template = library.get_template(TaskType.TRANSLATION)
    assert template is not None
    assert "translat" in template.system_prompt.lower()


def test_instruction_following_template():
    """Test that INSTRUCTION_FOLLOWING template exists and is well-formed"""
    library = get_template_library()

    template = library.get_template(TaskType.INSTRUCTION_FOLLOWING)
    assert template is not None
    assert "instruction" in template.system_prompt.lower()


def test_all_task_types_have_templates():
    """Test that every TaskType enum value has a corresponding template"""
    library = get_template_library()

    for task_type in TaskType:
        template = library.get_template(task_type)
        assert template is not None, f"Missing template for {task_type.name}"
        assert len(template.system_prompt) > 0, f"Empty system prompt for {task_type.name}"
        assert len(template.user_template) > 0, f"Empty user template for {task_type.name}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
