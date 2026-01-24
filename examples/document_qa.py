"""
Document Q&A with RAG (Retrieval-Augmented Generation)
Demonstrates how to query your documents using semantic search
"""

import asyncio
from pathlib import Path
from pebblemind.config import Config, get_config
from pebblemind.core.llm import LLMEngine
from pebblemind.rag.system import RAGSystem


async def main():
    """Document Q&A system using RAG"""
    print("\n📚 PebbleMind Document Q&A")
    print("=" * 60)
    print("This example shows how to ask questions about your documents")
    print("using Retrieval-Augmented Generation (RAG)\n")

    # Load configuration
    try:
        config = get_config()
    except FileNotFoundError:
        print("❌ Config file not found. Run: python install.py")
        return

    # Initialize components
    print("⏳ Initializing RAG system and LLM...")

    try:
        # Initialize RAG
        rag = RAGSystem(config.rag)
        await rag.initialize()
        print("✅ RAG system ready")

        # Initialize LLM
        engine = LLMEngine(config.llm)
        await engine.initialize()
        print(f"✅ LLM ready ({config.llm.model_size.upper()} model)\n")

    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("\n💡 Install with: pip install sentence-transformers")
        return
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return

    # Sample documents (in real use, load from files)
    sample_docs = [
        {
            "content": """
            Python is a high-level, interpreted programming language known for its
            simplicity and readability. Created by Guido van Rossum and first released
            in 1991, Python has become one of the most popular programming languages.
            It's widely used for web development, data science, machine learning,
            automation, and scientific computing.
            """,
            "metadata": {"source": "python_intro.txt", "topic": "programming"}
        },
        {
            "content": """
            Machine Learning is a subset of artificial intelligence that enables systems
            to learn and improve from experience without being explicitly programmed.
            It focuses on developing computer programs that can access data and use it
            to learn for themselves. Common applications include image recognition,
            natural language processing, and recommendation systems.
            """,
            "metadata": {"source": "ml_intro.txt", "topic": "ai"}
        },
        {
            "content": """
            Quantum computing leverages quantum mechanical phenomena like superposition
            and entanglement to perform computations. Unlike classical bits which are
            either 0 or 1, quantum bits (qubits) can exist in multiple states simultaneously.
            This allows quantum computers to solve certain problems exponentially faster
            than classical computers, particularly in cryptography and optimization.
            """,
            "metadata": {"source": "quantum_intro.txt", "topic": "computing"}
        },
        {
            "content": """
            The Retrieval-Augmented Generation (RAG) approach combines the power of
            large language models with information retrieval. Instead of relying solely
            on the model's training data, RAG retrieves relevant documents from a
            knowledge base and uses them to generate more accurate and up-to-date responses.
            This is particularly useful for domain-specific applications and reducing
            hallucinations.
            """,
            "metadata": {"source": "rag_intro.txt", "topic": "ai"}
        }
    ]

    # Add documents to RAG system
    print("📥 Adding sample documents to knowledge base...")
    await rag.add_documents(sample_docs)

    # Get stats
    stats = await rag.get_stats()
    print(f"✅ Added {stats['total_documents']} document chunks")
    print(f"   Database size: {stats['database_size_mb']:.2f} MB")
    print(f"   Embedding model: {stats['embedding_model']}\n")

    print("💡 Try asking questions like:")
    print("   - What is Python used for?")
    print("   - How does machine learning work?")
    print("   - What is RAG?")
    print("   - Compare quantum and classical computing")
    print("\nType 'quit' to exit, 'stats' for database info\n")

    # Q&A loop
    while True:
        try:
            question = input("Question: ").strip()

            if question.lower() in ['quit', 'exit', 'q']:
                break

            if question.lower() == 'stats':
                stats = await rag.get_stats()
                print(f"\n📊 Database Stats:")
                print(f"   Documents: {stats['total_documents']}")
                print(f"   Size: {stats['database_size_mb']:.2f} MB")
                print(f"   Vector search: {'Enabled' if stats['vector_search_enabled'] else 'Disabled'}")
                print()
                continue

            if not question:
                continue

            # Search for relevant documents
            print("\n🔍 Searching knowledge base...", end='', flush=True)
            results = await rag.search(question, k=3)

            if not results:
                print(" No relevant documents found.")
                print("\nℹ️  Answering from general knowledge:\n")
                answer = await engine.generate(question)
                print(f"AI: {answer}\n")
                continue

            print(f" Found {len(results)} relevant passages")

            # Show sources
            print("\n📄 Sources:")
            for i, result in enumerate(results, 1):
                metadata = result.get('metadata', {})
                source = metadata.get('source', 'unknown')
                score = result.get('score', 0)
                print(f"   {i}. {source} (relevance: {score:.2%})")

            # Generate answer with context
            print("\n💭 Generating answer...\n")

            context = [r['content'] for r in results]
            answer = await engine.generate(
                question,
                context=context,
                system_prompt=(
                    "You are a helpful AI assistant. Answer the question based on "
                    "the provided context. If the context doesn't contain the answer, "
                    "say so clearly."
                )
            )

            print(f"AI: {answer}\n")

        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            continue

    # Cleanup
    await rag.cleanup()
    await engine.cleanup()
    print("\n👋 Goodbye!\n")


if __name__ == "__main__":
    asyncio.run(main())
