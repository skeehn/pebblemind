#!/usr/bin/env python3
"""Qwen2.5 Model Strategy Demo

Demonstrates the new Qwen2.5 model strategy with GPU offloading support.
Shows how to switch between different model sizes and configure GPU offloading.
"""

import asyncio
import time
from pebblemind.core import PebbleMind
from pebblemind.config import Config, LLMConfig


async def demo_model_switching():
    """Demonstrate switching between different model sizes"""
    print("🔄 Model Switching Demo")
    print("=" * 30)

    # Create configuration with 3B model as default
    config = Config()
    config.llm.model_size = "3b"
    config.llm.enable_gpu_offload = False  # Start with CPU-only

    pebblemind = PebbleMind(config)
    await pebblemind.initialize()

    # Test with 3B model
    print("\n📊 Testing 3B Model (Default)")
    start_time = time.time()
    response = await pebblemind.query("Explain quantum computing in simple terms.")
    end_time = time.time()
    
    print(f"Response: {response[:100]}...")
    print(f"Time: {end_time - start_time:.2f}s")

    # Switch to 1.5B model
    print("\n📊 Switching to 1.5B Model (Ultra-light)")
    success = await pebblemind.llm_engine.switch_model("1.5b")
    if success:
        start_time = time.time()
        response = await pebblemind.query("What is machine learning?")
        end_time = time.time()
        
        print(f"Response: {response[:100]}...")
        print(f"Time: {end_time - start_time:.2f}s")

    # Switch to 7B model
    print("\n📊 Switching to 7B Model (High-quality)")
    success = await pebblemind.llm_engine.switch_model("7b")
    if success:
        start_time = time.time()
        response = await pebblemind.query("Write a short poem about artificial intelligence.")
        end_time = time.time()
        
        print(f"Response: {response[:100]}...")
        print(f"Time: {end_time - start_time:.2f}s")

    await pebblemind.stop()


async def demo_gpu_offloading():
    """Demonstrate GPU offloading configuration"""
    print("\n🎮 GPU Offloading Demo")
    print("=" * 25)

    # Create configuration with GPU offloading enabled
    config = Config()
    config.llm.model_size = "3b"
    config.llm.enable_gpu_offload = True
    config.llm.gpu_layers = -1  # Auto-detect

    pebblemind = PebbleMind(config)
    await pebblemind.initialize()

    # Get model information
    model_info = await pebblemind.llm_engine.get_model_info()
    
    print(f"Model: {model_info.get('model_name')}")
    print(f"GPU Available: {model_info.get('gpu_available')}")
    print(f"GPU Offload Enabled: {model_info.get('gpu_offload_enabled')}")
    print(f"GPU Layers: {model_info.get('gpu_layers')}")

    if model_info.get('gpu_offload_enabled'):
        print("\n🚀 Testing with GPU acceleration...")
        start_time = time.time()
        response = await pebblemind.query("Explain the benefits of renewable energy.")
        end_time = time.time()
        
        print(f"Response: {response[:100]}...")
        print(f"Time with GPU: {end_time - start_time:.2f}s")
    else:
        print("⚠️  GPU not available, using CPU-only mode")

    await pebblemind.stop()


async def demo_performance_comparison():
    """Compare performance across different configurations"""
    print("\n⚡ Performance Comparison Demo")
    print("=" * 35)

    test_prompt = "Write a brief explanation of how neural networks work."
    
    configurations = [
        {"size": "1.5b", "gpu": False, "name": "1.5B CPU-only"},
        {"size": "3b", "gpu": False, "name": "3B CPU-only"},
        {"size": "3b", "gpu": True, "name": "3B GPU-offload"},
        {"size": "7b", "gpu": False, "name": "7B CPU-only"},
    ]

    results = []

    for config_data in configurations:
        print(f"\n🧪 Testing {config_data['name']}...")
        
        config = Config()
        config.llm.model_size = config_data["size"]
        config.llm.enable_gpu_offload = config_data["gpu"]
        config.llm.gpu_layers = -1 if config_data["gpu"] else 0

        pebblemind = PebbleMind(config)
        await pebblemind.initialize()

        # Warm up
        await pebblemind.query("Hello")

        # Benchmark
        start_time = time.time()
        response = await pebblemind.query(test_prompt)
        end_time = time.time()

        results.append({
            "config": config_data["name"],
            "time": end_time - start_time,
            "response_length": len(response)
        })

        print(f"  Time: {end_time - start_time:.2f}s")
        print(f"  Response: {response[:50]}...")

        await pebblemind.stop()

    # Summary
    print("\n📈 Performance Summary:")
    print("-" * 40)
    for result in results:
        print(f"{result['config']:20} | {result['time']:6.2f}s | {result['response_length']:3d} chars")


async def demo_model_info():
    """Show detailed model information"""
    print("\n📋 Model Information Demo")
    print("=" * 30)

    config = Config()
    config.llm.model_size = "3b"

    pebblemind = PebbleMind(config)
    await pebblemind.initialize()

    model_info = await pebblemind.llm_engine.get_model_info()
    
    print("Current Model Details:")
    for key, value in model_info.items():
        if key != "available_models":
            print(f"  {key}: {value}")
    
    print(f"\nAvailable Models: {', '.join(model_info.get('available_models', []))}")

    await pebblemind.stop()


async def main():
    """Run all demos"""
    print("🤖 PebbleMind Qwen2.5 Model Strategy Demo")
    print("=" * 50)
    print("This demo showcases the new Qwen2.5 model strategy with:")
    print("- 3B model as default (balanced intelligence)")
    print("- 1.5B model for ultra-light CPU usage")
    print("- 7B model for high-quality responses")
    print("- GPU layer offloading for mixed CPU/GPU inference")
    print("- Dynamic model switching without restart")
    print()

    try:
        await demo_model_info()
        await demo_model_switching()
        await demo_gpu_offloading()
        await demo_performance_comparison()

        print("\n✅ Demo completed successfully!")
        print("\n💡 Tips:")
        print("- Use 1.5B for fastest responses on low-end hardware")
        print("- Use 3B for balanced quality and speed (recommended)")
        print("- Use 7B for highest quality with GPU offloading")
        print("- Enable GPU offloading for significant speed improvements")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("Make sure models are downloaded and configuration is correct")


if __name__ == "__main__":
    asyncio.run(main())
