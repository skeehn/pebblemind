"""Core PebbleMind AI Assistant"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from .config import Config, get_config
from .core.llm import LLMEngine
from .voice import VoiceProcessor
from .rag import RAGSystem
from .api import APIServer


logger = logging.getLogger(__name__)


class PebbleMind:
    """Main PebbleMind AI Assistant class"""

    def __init__(self, config: Optional[Config] = None):
        """Initialize PebbleMind with configuration"""
        self.config = config or get_config()
        self._setup_logging()

        # Initialize components
        self.llm_engine: Optional[LLMEngine] = None
        self.voice_processor: Optional[VoiceProcessor] = None
        self.rag_system: Optional[RAGSystem] = None
        self.api_server: Optional[APIServer] = None

        # Component status
        self._initialized = False
        self._running = False

    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config.cache_path / "pebblemind.log"),
                logging.StreamHandler()
            ]
        )

    async def initialize(self) -> None:
        """Initialize all components"""
        logger.info("Initializing PebbleMind...")

        try:
            # Create necessary directories
            self.config.data_path.mkdir(parents=True, exist_ok=True)
            self.config.cache_path.mkdir(parents=True, exist_ok=True)

            # Initialize LLM engine
            self.llm_engine = LLMEngine(self.config.llm)
            await self.llm_engine.initialize()

            # Initialize voice processor
            self.voice_processor = VoiceProcessor(self.config.voice)

            # Initialize RAG system
            self.rag_system = RAGSystem(self.config.rag)
            await self.rag_system.initialize()

            # Initialize API server
            self.api_server = APIServer(self.config.api, self)

            self._initialized = True
            logger.info("PebbleMind initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize PebbleMind: {e}")
            raise

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
        **kwargs
    ) -> str:
        """Process a text query and return response"""
        if not self._initialized:
            await self.initialize()

        try:
            # Retrieve relevant context if RAG is enabled
            if use_rag and self.rag_system and context:
                relevant_docs = await self.rag_system.search(message, k=self.config.rag.max_results)
                context = [doc["content"] for doc in relevant_docs]

            # Generate response using LLM
            if self.llm_engine:
                response = await self.llm_engine.generate(
                    message=message,
                    context=context,
                    **kwargs
                )
                return response
            else:
                raise RuntimeError("LLM engine not initialized")

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            raise

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
