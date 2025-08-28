#!/usr/bin/env python3
"""Basic PebbleMind Usage Examples

Simple examples showing how to use PebbleMind for common tasks.
"""

import asyncio
from pebblemind.core import PebbleMind, quick_start


async def basic_chat_example():
    """Basic chat example"""
    print("🤖 Basic Chat Example")
    print("=" * 30)

    # Initialize PebbleMind
    pebblemind = quick_start()

    # Simple query
    response = await pebblemind.query("Hello! How are you today?")
    print(f"Response: {response}")

    # Query with context
    context_messages = ["I love programming", "Python is my favorite language"]
    response = await pebblemind.query(
        "What programming language should I learn?",
        context=context_messages
    )
    print(f"Contextual Response: {response}")


async def voice_example():
    """Voice processing example"""
    print("\n🎤 Voice Processing Example")
    print("=" * 35)

    pebblemind = quick_start()

    # Text to speech
    text = "Hello, this is PebbleMind speaking!"
    print(f"Converting text to speech: {text}")

    try:
        audio_data = await pebblemind.voice_processor.text_to_speech(text)
        print(f"Generated {len(audio_data)} bytes of audio data")

        # Save audio to file
        with open("example_output.wav", "wb") as f:
            f.write(audio_data)
        print("Audio saved to example_output.wav")

    except Exception as e:
        print(f"Voice processing not available: {e}")


async def rag_example():
    """RAG (Retrieval-Augmented Generation) example"""
    print("\n📚 RAG Example")
    print("=" * 15)

    pebblemind = quick_start()

    # Add documents to the knowledge base
    documents = [
        {
            "content": "PebbleMind is a CPU-first local AI assistant designed for privacy and performance.",
            "metadata": {"topic": "introduction", "source": "readme"}
        },
        {
            "content": "The system uses llama.cpp for efficient LLM inference with BLAS acceleration.",
            "metadata": {"topic": "technical", "source": "docs"}
        },
        {
            "content": "PebbleMind supports voice input through whisper.cpp and output through Piper TTS.",
            "metadata": {"topic": "features", "source": "readme"}
        }
    ]

    print("Adding documents to knowledge base...")
    await pebblemind.add_documents(documents)

    # Query with RAG
    query = "What makes PebbleMind special?"
    print(f"Query: {query}")

    response = await pebblemind.query(query, use_rag=True)
    print(f"RAG Response: {response}")


async def api_server_example():
    """API server example"""
    print("\n🌐 API Server Example")
    print("=" * 22)

    pebblemind = quick_start()

    print("Starting API server...")
    await pebblemind.start()

    print("API server running at http://localhost:8000")
    print("Try: curl http://localhost:8000/v1/chat/completions -d '...'")

    # Keep server running for demonstration
    try:
        await asyncio.sleep(1)  # Brief pause for demo
    except KeyboardInterrupt:
        pass
    finally:
        await pebblemind.stop()


def synchronous_example():
    """Synchronous usage example"""
    print("\n⚡ Synchronous Usage Example")
    print("=" * 32)

    # Quick synchronous setup
    pebblemind = quick_start()

    # Run async function synchronously
    response = asyncio.run(pebblemind.query("What is AI?"))
    print(f"Synchronous Response: {response}")


async def comprehensive_example():
    """Comprehensive example showing all features"""
    print("\n🚀 Comprehensive Example")
    print("=" * 27)

    pebblemind = quick_start()

    # 1. Basic chat
    print("1. Basic Chat:")
    response = await pebblemind.query("Explain machine learning briefly")
    print(f"   {response[:100]}...")

    # 2. Add knowledge
    print("\n2. Adding Knowledge:")
    docs = [
        {"content": "Machine learning is a subset of AI that enables computers to learn without explicit programming.", "metadata": {"topic": "ML"}},
        {"content": "Deep learning uses neural networks with multiple layers to process complex data patterns.", "metadata": {"topic": "DL"}}
    ]
    await pebblemind.add_documents(docs)
    print("   Added 2 documents to knowledge base")

    # 3. Query with context
    print("\n3. Contextual Query:")
    response = await pebblemind.query("How does deep learning relate to machine learning?", use_rag=True)
    print(f"   {response[:150]}...")

    # 4. Check system status
    print("\n4. System Status:")
    status = await pebblemind.get_status()
    print(f"   Components initialized: {sum(1 for v in status['components'].values() if v)}/5")

    print("\n✅ Comprehensive example completed!")


async def main():
    """Run all examples"""
    print("🤖 PebbleMind Examples")
    print("======================")

    try:
        await basic_chat_example()
        await voice_example()
        await rag_example()

        print("\n" + "="*50)
        print("Note: API server and comprehensive examples require proper model setup")
        print("Run 'pebblemind status' to check your configuration")
        print("="*50)

    except Exception as e:
        print(f"❌ Example failed: {e}")
        print("Make sure models are downloaded and configuration is correct")
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
