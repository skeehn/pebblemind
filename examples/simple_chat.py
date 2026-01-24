"""
Simple Interactive Chat Example
Demonstrates basic LLM usage with streaming support
"""

import asyncio
from pathlib import Path
from pebblemind.config import Config, get_config
from pebblemind.core.llm import LLMEngine


async def main():
    """Simple interactive chat with the AI"""
    print("\n🤖 PebbleMind Simple Chat")
    print("=" * 60)
    print("This example demonstrates basic chat functionality")
    print("Type 'quit' to exit, 'info' for model information\n")

    # Load configuration
    try:
        config = get_config()
    except FileNotFoundError:
        print("❌ Config file not found. Run: python install.py")
        return

    # Initialize LLM engine
    print("⏳ Loading model (this may take a few seconds)...")
    engine = LLMEngine(config.llm)

    try:
        await engine.initialize()
        print(f"✅ Ready! Using {config.llm.model_size.upper()} model")
        print(f"   Context: {config.llm.context_length} tokens")
        print(f"   Threads: {config.llm.threads}\n")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        print("\n💡 Possible solutions:")
        print("   1. Make sure you downloaded a model file")
        print("   2. Check pebblemind.yaml has correct model_path")
        print("   3. Run: python install.py")
        return

    # Chat loop
    conversation_context = []

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                break

            if user_input.lower() == 'info':
                info = await engine.get_model_info()
                print(f"\n📊 Model Info:")
                print(f"   Name: {info.get('model_name')}")
                print(f"   Size: {info.get('file_size_gb', 0):.2f} GB")
                print(f"   BLAS: {'Enabled' if info.get('blas_enabled') else 'Disabled'}")
                print()
                continue

            if not user_input:
                continue

            # Generate response
            print("AI: ", end='', flush=True)

            # Keep last 3 exchanges for context
            context = conversation_context[-6:] if conversation_context else None

            response = await engine.generate(
                user_input,
                context=context,
                max_tokens=256
            )

            print(response)
            print()

            # Update conversation context
            conversation_context.append(f"User: {user_input}")
            conversation_context.append(f"AI: {response}")

        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Continuing...\n")

    # Cleanup
    await engine.cleanup()
    print("\n👋 Goodbye!\n")


if __name__ == "__main__":
    asyncio.run(main())
