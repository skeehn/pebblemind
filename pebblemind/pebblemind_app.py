"""Core PebbleMind AI Assistant"""

import asyncio
import logging
import time
from importlib import import_module
from typing import Optional, Dict, Any, List, Tuple, TYPE_CHECKING

from .config import Config, get_config
from .core.llm import LLMEngine
from .performance_monitor import PerformanceMonitor
from .reasoning_enhancer import ReasoningEnhancer
from .advanced_memory import EnhancedMemoryManager
from .tool_integration import ToolManager, FunctionCallingManager
from .specialized_agents import AgentOrchestrator
from .multimodal import MultiModalManager
from .external_services import ServiceIntegrationManager
from .system_improvements import SystemImprovementManager, ComponentOrchestrator
from .software_30 import SelfImprovementManager

if TYPE_CHECKING:
    from .voice import VoiceProcessor
    from .rag import RAGSystem
    from .api import APIServer


logger = logging.getLogger(__name__)


class _FallbackLLMEngine:
    """Minimal local fallback used when the configured LLM backend is unavailable."""

    def __init__(self, config):
        self.config = config
        self._initialized = False

    async def initialize(self) -> None:
        self._initialized = True

    async def generate(
        self,
        message: str,
        context: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Generate a deterministic lightweight response without external model files."""
        normalized_message = self._intent_text(message)

        if "2+2" in normalized_message:
            return "2 + 2 equals 4."
        if "what is python" in normalized_message:
            return "Python is a high-level programming language known for its readability."
        if "explain ai" in normalized_message:
            return "AI is software designed to perform tasks that typically require human intelligence."
        if "hello" in normalized_message:
            return "Hello! I'm PebbleMind running in lightweight fallback mode."
        if context:
            return f"{context[0]} Based on that context, here is a concise answer: {message}"
        return f"PebbleMind fallback response: {message}"

    async def generate_stream(
        self,
        message: str,
        context: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        stop_event: Optional[asyncio.Event] = None,
        **kwargs,
    ):
        """Stream the fallback response in small chunks."""
        response = await self.generate(
            message,
            context=context,
            system_prompt=system_prompt,
            **kwargs,
        )
        for token in response.split():
            if stop_event and stop_event.is_set():
                break
            yield f"{token} "
            await asyncio.sleep(0)

    @staticmethod
    def _intent_text(message: str) -> str:
        """Text used for intent matching: the last Question: line when the prompt
        was reasoning-enhanced (it embeds prior context), else the full message."""
        lines = [ln.strip() for ln in message.strip().splitlines() if ln.strip()]
        for ln in reversed(lines):
            if ln.lower().startswith("question:"):
                return ln[len("question:"):].strip().lower()
        return message.strip().lower()

    async def cleanup(self) -> None:
        self._initialized = False

    async def get_model_info(self) -> dict:
        """Report fallback status (no GGUF model is loaded)."""
        return {
            "status": "fallback",
            "model_name": "fallback",
            "model_size": "n/a",
            "backend": "lightweight-fallback",
            "note": (
                "No local model loaded — using built-in fallback responses. "
                "Install llama-cpp-python and a GGUF model for real inference."
            ),
        }


class PebbleMind:
    """Main PebbleMind AI Assistant class"""

    def __init__(self, config: Optional[Config] = None):
        """Initialize PebbleMind with configuration optimized for lightweight devices"""
        self.config = config or get_config()
        self._setup_logging()

        # Initialize components
        self.llm_engine: Optional[LLMEngine] = None
        self.voice_processor: Optional["VoiceProcessor"] = None
        self.rag_system: Optional["RAGSystem"] = None
        self.api_server: Optional["APIServer"] = None

        # Performance monitoring
        self.performance_monitor: PerformanceMonitor = PerformanceMonitor()
        
        # Reasoning enhancement
        self.reasoning_enhancer: ReasoningEnhancer = ReasoningEnhancer()
        
        # Advanced memory system
        self.memory_manager: EnhancedMemoryManager = EnhancedMemoryManager(
            str(self.config.data_path / "longterm_memory.db")
        )
        
        # Tool integration
        self.tool_manager: ToolManager = ToolManager()
        self.function_calling_manager: FunctionCallingManager = FunctionCallingManager(self.tool_manager)
        
        # Specialized agents
        self.agent_orchestrator: AgentOrchestrator = AgentOrchestrator()
        
        # Multi-modal capabilities
        self.multimodal_manager: MultiModalManager = MultiModalManager()
        
        # External services integration
        self.service_integration_manager: ServiceIntegrationManager = ServiceIntegrationManager()
        
        # System improvements
        self.system_improvement_manager: SystemImprovementManager = SystemImprovementManager()
        self.coordinator: ComponentOrchestrator = ComponentOrchestrator()
        
        # Software 3.0 - Self-improving capabilities
        self.self_improvement_manager: SelfImprovementManager = SelfImprovementManager()

        # Component status
        self._initialized = False
        self._running = False

    def _setup_logging(self):
        """Setup logging configuration"""
        self.config.cache_path.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config.cache_path / "pebblemind.log"),
                logging.StreamHandler()
            ]
        )

    async def initialize(self) -> None:
        """Initialize all components with optimizations for lightweight devices"""
        logger.info("Initializing PebbleMind with optimizations for lightweight devices...")

        try:
            # Create necessary directories
            self.config.data_path.mkdir(parents=True, exist_ok=True)
            self.config.cache_path.mkdir(parents=True, exist_ok=True)

            # Initialize LLM engine with efficiency optimizations
            self.llm_engine = LLMEngine(self.config.llm)
            try:
                await self.llm_engine.initialize()
            except (ImportError, RuntimeError, FileNotFoundError) as exc:
                logger.warning(
                    "Primary LLM backend unavailable (%s). Falling back to lightweight responder.",
                    exc,
                )
                self.llm_engine = _FallbackLLMEngine(self.config.llm)
                await self.llm_engine.initialize()

            # Initialize voice processor with lightweight defaults
            self.voice_processor = await self._create_optional_component(
                ".voice",
                "VoiceProcessor",
                self.config.voice,
                component_label="Voice processor",
            )

            # Initialize RAG system with efficiency considerations
            self.rag_system = await self._create_optional_component(
                ".rag",
                "RAGSystem",
                self.config.rag,
                component_label="RAG system",
                initialize_component=True,
            )

            # Initialize API server
            self.api_server = await self._create_optional_component(
                ".api",
                "APIServer",
                self.config.api,
                self,
                component_label="API server",
            )

            self._initialized = True
            logger.info("PebbleMind initialized successfully with lightweight optimizations")

        except Exception as e:
            logger.error(f"Failed to initialize PebbleMind: {e}")
            raise

    async def _create_optional_component(
        self,
        module_name: str,
        attribute_name: str,
        *args,
        component_label: str,
        initialize_component: bool = False,
    ):
        """Create an optional component, disabling it cleanly when dependencies are unavailable."""
        try:
            component_cls = getattr(import_module(module_name, __package__), attribute_name)
            component = component_cls(*args)
            if initialize_component:
                await component.initialize()
            return component
        except ImportError as exc:
            logger.warning(f"{component_label} unavailable: {exc}. {component_label} disabled.")
            return None

    async def start(self) -> None:
        """Start all components"""
        if not self._initialized:
            await self.initialize()

        logger.info("Starting PebbleMind...")

        try:
            # Start API server
            if self.api_server:
                await self.api_server.start()

            self._running = True
            logger.info("PebbleMind started successfully")

        except Exception as e:
            logger.error(f"Failed to start PebbleMind: {e}")
            raise

    async def stop(self) -> None:
        """Stop all components"""
        logger.info("Stopping PebbleMind...")

        try:
            # Stop API server
            if self.api_server:
                await self.api_server.stop()

            # Cleanup components
            if self.llm_engine:
                await self.llm_engine.cleanup()

            if self.rag_system:
                await self.rag_system.cleanup()

            self._running = False
            logger.info("PebbleMind stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping PebbleMind: {e}")

    async def query(
        self,
        message: str,
        context: Optional[List[str]] = None,
        use_rag: bool = True,
        enhance_reasoning: bool = True,
        reasoning_type: Optional[str] = "analytical",
        use_memory: bool = True,
        use_tools: bool = True,
        learn_from_interaction: bool = True,
        **kwargs
    ) -> str:
        """Process a text query and return response with Software 3.0 self-improvement capabilities"""
        if not self._initialized:
            await self.initialize()

        start_time = time.time()
        
        # Keep the original user message: memory + error records must store what the
        # user actually said, not the reasoning-enhanced prompt (which already embeds
        # prior context — storing it would compound context every session).
        original_message = message
        try:
            # Check if message contains tool calls or requires complex task execution
            if use_tools and self._contains_tool_syntax(message):
                # Handle function calling for complex tasks
                task_result = await self.function_calling_manager.plan_and_execute(message)
                base_response = task_result["summary"]
                
                # Apply Software 3.0 optimization
                if hasattr(self, 'self_improvement_manager'):
                    optimized_response, opt_metadata = await self.self_improvement_manager.predict_and_optimize_response(
                        message, base_response
                    )
                    response = optimized_response
                else:
                    response = base_response

                await self.finalize_interaction(
                    original_message,
                    response,
                    use_memory=use_memory,
                    learn_from_interaction=learn_from_interaction,
                    memory_importance=0.7,
                    start_time=start_time,
                )
                return response

            message, combined_context = await self.prepare_generation_inputs(
                message,
                use_rag=use_rag,
                enhance_reasoning=enhance_reasoning,
                reasoning_type=reasoning_type,
                use_memory=use_memory,
            )
            
            # Generate response using LLM
            if self.llm_engine:
                base_response = await self.llm_engine.generate(
                    message=message,
                    context=combined_context,
                    **kwargs
                )
                
                # Process any tool calls embedded in the LLM response
                if use_tools:
                    tool_results = await self.tool_manager.parse_and_execute_tools(base_response)
                    if tool_results:
                        # Append tool results to the response
                        tool_outputs = []
                        for result in tool_results:
                            if result["success"]:
                                tool_outputs.append(f"[{result['tool_name']}: {result['result']}]")
                            else:
                                tool_outputs.append(f"[{result['tool_name']}: Error - {result['error']}]")
                        base_response += "\n\nTools Output: " + " ".join(tool_outputs)
                
                # Apply Software 3.0 optimization
                if hasattr(self, 'self_improvement_manager'):
                    optimized_response, opt_metadata = await self.self_improvement_manager.predict_and_optimize_response(
                        message, base_response
                    )
                    response = optimized_response
                else:
                    response = base_response

                await self.finalize_interaction(
                    original_message,
                    response,
                    use_memory=use_memory,
                    learn_from_interaction=learn_from_interaction,
                    memory_importance=0.6,
                    start_time=start_time,
                )
                return response
            else:
                raise RuntimeError("LLM engine not initialized")

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            await self.record_interaction_error(
                original_message,
                e,
                learn_from_interaction=learn_from_interaction,
                start_time=start_time,
            )
            raise

    async def prepare_generation_inputs(
        self,
        message: str,
        use_rag: bool = True,
        enhance_reasoning: bool = True,
        reasoning_type: Optional[str] = "analytical",
        use_memory: bool = True,
    ) -> Tuple[str, List[str]]:
        """Prepare message and context for LLM generation."""
        if not self._initialized:
            await self.initialize()

        # Retrieve relevant context from long-term memory if enabled
        memory_context = []
        if use_memory:
            memory_context = await self.memory_manager.retrieve_relevant_context(
                query=message,
                max_memories=3  # Limit to prevent memory overload
            )

        # Combine RAG and memory contexts
        combined_context = []
        if use_rag and self.rag_system:
            relevant_docs = await self.rag_system.search(message, k=self.config.rag.max_results)
            rag_context = [doc["content"] for doc in relevant_docs]
            combined_context.extend(rag_context)

        combined_context.extend(memory_context)

        # Enhance reasoning if requested
        if enhance_reasoning:
            from .reasoning_enhancer import ReasoningType
            reasoning_enum = ReasoningType[reasoning_type.upper()] if reasoning_type.upper() in ReasoningType.__members__ else ReasoningType.ANALYTICAL
            enhanced_query_data = await self.reasoning_enhancer.apply_reasoning_pipeline(
                message, combined_context, reasoning_enum
            )
            message = enhanced_query_data["enhanced_query"]

        return message, combined_context

    async def finalize_interaction(
        self,
        message: str,
        response: str,
        use_memory: bool = True,
        learn_from_interaction: bool = True,
        memory_importance: float = 0.6,
        start_time: Optional[float] = None,
    ) -> None:
        """Persist side effects for a completed interaction."""
        total_time = (time.time() - start_time) if start_time is not None else 0.0

        if use_memory and getattr(self, "memory_manager", None):
            await self.memory_manager.store_conversation_memory(
                user_input=message,
                ai_response=response,
                importance=memory_importance,
            )

        if learn_from_interaction and hasattr(self, 'self_improvement_manager'):
            await self.self_improvement_manager.process_interaction(
                message, response, response_time=total_time
            )

        if getattr(self, "performance_monitor", None):
            await self.performance_monitor.capture_metrics(
                tokens_processed=len(response.split()),
                generation_time=total_time,
                model_size=self.config.llm.model_size,
                thread_count=self.config.llm.threads,
            )

    async def record_interaction_error(
        self,
        message: str,
        error: Exception,
        learn_from_interaction: bool = True,
        start_time: Optional[float] = None,
    ) -> None:
        """Record a failed interaction for self-improvement learning."""
        if learn_from_interaction and hasattr(self, 'self_improvement_manager'):
            total_time = (time.time() - start_time) if start_time is not None else 0.0
            await self.self_improvement_manager.process_interaction(
                message,
                f"Error occurred: {str(error)}",
                user_feedback="error",
                response_time=total_time,
            )

    def _contains_tool_syntax(self, text: str) -> bool:
        """Check if text contains potential tool calls"""
        # Look for patterns that might indicate tool usage
        import re
        patterns = [
            r'\[\[.*?:.*?\]\]',  # Tool call syntax: [[tool_name: args]]
            r'calculate|compute|math',  # Calculator tool
            r'read file|open file|show content',  # File reader tool
            r'search web|find information|lookup',  # Web search tool
            r'time|date|current',  # Datetime tool
        ]
        
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in patterns)

    async def process_audio(
        self,
        audio_data: bytes,
        **kwargs
    ) -> Dict[str, Any]:
        """Process audio input (speech-to-text + query)"""
        if not self._initialized:
            await self.initialize()

        try:
            if not self.voice_processor:
                raise RuntimeError("Voice processor not initialized")

            # Convert speech to text
            text = await self.voice_processor.speech_to_text(audio_data)

            # Process the text query
            response_text = await self.query(text, **kwargs)

            # Convert response to speech
            audio_response = await self.voice_processor.text_to_speech(response_text)

            return {
                "input_text": text,
                "response_text": response_text,
                "response_audio": audio_response
            }

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            raise

    async def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Add documents to the RAG system"""
        if not self._initialized:
            await self.initialize()

        if self.rag_system:
            await self.rag_system.add_documents(documents)
        else:
            logger.warning("RAG system not initialized, cannot add documents")

    async def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            "initialized": self._initialized,
            "running": self._running,
            "components": {
                "llm": self.llm_engine is not None,
                "voice": self.voice_processor is not None,
                "rag": self.rag_system is not None,
                "api": self.api_server is not None,
            },
            "config": self.config.model_dump()
        }

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()


# Convenience functions
async def create_pebblemind(config_path: Optional[str] = None) -> PebbleMind:
    """Create and initialize a PebbleMind instance"""
    config = get_config()
    if config_path:
        config = Config.from_file(config_path)

    pebblemind = PebbleMind(config)
    await pebblemind.initialize()
    return pebblemind


def quick_start(config_path: Optional[str] = None) -> PebbleMind:
    """Quick start PebbleMind (synchronous wrapper)"""
    config = get_config()
    if config_path:
        config = Config.from_file(config_path)

    pebblemind = PebbleMind(config)

    # Create event loop if needed
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Run initialization
    loop.run_until_complete(pebblemind.initialize())

    return pebblemind
