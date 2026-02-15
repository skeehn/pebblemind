#!/usr/bin/env python3
"""Interactive chat test for PebbleMind - Test real capabilities"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_basic_chat():
    """Test basic chat functionality"""
    print("="*60)
    print("PEBBLEMIND CHAT FUNCTIONALITY TEST")
    print("="*60)
    print()

    try:
        # Import from parent package, not core subpackage
        import pebblemind
        from pebblemind.core import PebbleMind

        # Actually PebbleMind is in the pebblemind module root
        # Let's try the correct import
        import importlib
        spec = importlib.util.spec_from_file_location(
            "pebblemind_core_module",
            Path(__file__).parent / "pebblemind" / "core.py"
        )
        core_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(core_module)
        PebbleMind = core_module.PebbleMind

        # Initialize
        print("🔧 Initializing PebbleMind...")
        mind = PebbleMind()
        await mind.initialize()
        print("✅ Initialized successfully!\n")

        # Test queries with varying complexity
        test_queries = [
            {
                "query": "Hello! Can you introduce yourself?",
                "category": "Basic Greeting"
            },
            {
                "query": "What is 15 + 27?",
                "category": "Simple Math"
            },
            {
                "query": "Explain what Python is in one sentence.",
                "category": "Knowledge Question"
            },
            {
                "query": "Write a haiku about AI",
                "category": "Creative Writing"
            },
            {
                "query": "List 3 benefits of using Python for web development",
                "category": "Technical Knowledge"
            }
        ]

        results = []

        for i, test in enumerate(test_queries, 1):
            print(f"\n{'─'*60}")
            print(f"TEST {i}/{len(test_queries)}: {test['category']}")
            print(f"{'─'*60}")
            print(f"👤 User: {test['query']}")
            print()

            try:
                import time
                start_time = time.time()

                response = await mind.query(test['query'])

                elapsed = time.time() - start_time

                print(f"🤖 Assistant: {response}")
                print()
                print(f"⏱️  Response time: {elapsed:.2f}s")

                results.append({
                    "category": test['category'],
                    "success": True,
                    "time": elapsed,
                    "response_length": len(response)
                })

            except Exception as e:
                print(f"❌ Error: {e}")
                results.append({
                    "category": test['category'],
                    "success": False,
                    "error": str(e)
                })

        # Summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}\n")

        successful = sum(1 for r in results if r.get('success'))
        print(f"✅ Successful: {successful}/{len(results)}")

        if successful > 0:
            avg_time = sum(r.get('time', 0) for r in results if r.get('success')) / successful
            print(f"⏱️  Average response time: {avg_time:.2f}s")

            avg_length = sum(r.get('response_length', 0) for r in results if r.get('success')) / successful
            print(f"📏 Average response length: {int(avg_length)} chars")

        print("\n📊 Detailed Results:")
        for r in results:
            status = "✅" if r.get('success') else "❌"
            category = r.get('category')
            if r.get('success'):
                print(f"  {status} {category}: {r.get('time', 0):.2f}s, {r.get('response_length', 0)} chars")
            else:
                print(f"  {status} {category}: {r.get('error', 'Unknown error')}")

        # Cleanup
        await mind.stop()
        print(f"\n{'='*60}")
        print("✅ Test complete!")
        print(f"{'='*60}")

    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\nMake sure all dependencies are installed:")
        print("  pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def test_context_window():
    """Test context window and memory"""
    print("\n" + "="*60)
    print("CONTEXT WINDOW & MEMORY TEST")
    print("="*60)
    print()

    try:
        from pebblemind.core import PebbleMind

        print("🔧 Initializing PebbleMind...")
        mind = PebbleMind()
        await mind.initialize()
        print("✅ Initialized!\n")

        # Multi-turn conversation
        conversation = [
            "My name is Alex and I'm a software engineer.",
            "What did I just tell you my name was?",
            "What's my profession?",
            "Based on what you know about me, suggest a programming project.",
        ]

        for i, message in enumerate(conversation, 1):
            print(f"\n{'─'*60}")
            print(f"TURN {i}/{len(conversation)}")
            print(f"{'─'*60}")
            print(f"👤 User: {message}")

            try:
                response = await mind.query(message, use_memory=True)
                print(f"🤖 Assistant: {response}")
            except Exception as e:
                print(f"❌ Error: {e}")

        # Test memory retrieval
        print(f"\n{'─'*60}")
        print("MEMORY RETRIEVAL TEST")
        print(f"{'─'*60}")

        try:
            context = await mind.memory_manager.retrieve_relevant_context(
                "Tell me what you remember about me",
                max_memories=5
            )
            print(f"\n📝 Retrieved {len(context)} memories:")
            for i, memory in enumerate(context, 1):
                print(f"  {i}. {memory[:100]}...")
        except Exception as e:
            print(f"❌ Memory retrieval error: {e}")

        await mind.stop()
        print(f"\n{'='*60}")
        print("✅ Context test complete!")
        print(f"{'='*60}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def test_capabilities():
    """Test and document capabilities"""
    print("\n" + "="*60)
    print("CAPABILITY ASSESSMENT")
    print("="*60)
    print()

    capabilities = {
        "✅ SUPPORTED": [
            "Basic conversation and Q&A",
            "Text generation (explanations, summaries)",
            "Simple reasoning and math",
            "Creative writing (poems, stories)",
            "Code explanation and discussion",
            "Knowledge retrieval (if RAG is set up)",
            "Memory of conversation context",
            "Multi-turn dialogue",
        ],
        "⚠️  LIMITED": [
            "Complex mathematical calculations",
            "Real-time information (no internet access)",
            "Image generation/processing",
            "Very long document analysis",
            "Code execution (requires tool integration)",
        ],
        "❌ NOT SUPPORTED": [
            "Web browsing or internet access",
            "File system operations (without tools)",
            "External API calls (without configuration)",
            "Real-time data (stocks, weather, news)",
            "Video processing",
        ]
    }

    for category, items in capabilities.items():
        print(f"\n{category}:")
        for item in items:
            print(f"  • {item}")

    print(f"\n{'='*60}")
    print("USE CASES")
    print(f"{'='*60}\n")

    use_cases = {
        "💼 Personal Assistant": [
            "Answer questions about programming",
            "Explain concepts in simple terms",
            "Help with writing tasks",
            "Brainstorm ideas",
        ],
        "👨‍💻 Development Aid": [
            "Code review and explanations",
            "Algorithm design discussions",
            "Debugging assistance",
            "Architecture planning",
        ],
        "📚 Learning Tool": [
            "Concept explanations",
            "Practice problems",
            "Study guide generation",
            "Topic summaries",
        ],
        "✍️  Content Creation": [
            "Blog post drafts",
            "Documentation writing",
            "Creative writing",
            "Email composition",
        ],
    }

    for category, items in use_cases.items():
        print(f"{category}:")
        for item in items:
            print(f"  • {item}")
        print()

    return True


async def main():
    """Run all tests"""
    print("\n" + "🧠 " * 20)
    print("PEBBLEMIND COMPREHENSIVE TESTING")
    print("🧠 " * 20 + "\n")

    tests = [
        ("Basic Chat Functionality", test_basic_chat),
        ("Context Window & Memory", test_context_window),
        ("Capabilities Assessment", test_capabilities),
    ]

    results = []

    for name, test_func in tests:
        try:
            print(f"\n{'█'*60}")
            print(f"Running: {name}")
            print(f"{'█'*60}")
            result = await test_func()
            results.append((name, result))
        except KeyboardInterrupt:
            print("\n\n⚠️  Test interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            results.append((name, False))

    # Final summary
    print("\n\n" + "="*60)
    print("FINAL TEST SUMMARY")
    print("="*60 + "\n")

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    passed = sum(1 for _, r in results if r)
    print(f"\n📊 Overall: {passed}/{len(results)} tests passed")

    return all(r for _, r in results)


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
