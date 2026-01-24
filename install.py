#!/usr/bin/env python3
"""
PebbleMind Automated Installer
Simplifies the installation process for local edge AI deployment
"""

import sys
import os
import subprocess
import platform
import urllib.request
import hashlib
from pathlib import Path
from typing import Optional, Tuple

# Color codes for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_header(text: str):
    """Print colored header"""
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}{text.center(60)}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{GREEN}✅ {text}{RESET}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{YELLOW}⚠️  {text}{RESET}")


def print_error(text: str):
    """Print error message"""
    print(f"{RED}❌ {text}{RESET}")


def print_info(text: str):
    """Print info message"""
    print(f"{BLUE}ℹ️  {text}{RESET}")


def check_python_version() -> bool:
    """Check if Python version is compatible"""
    print_info("Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print_success(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python 3.9+ required, you have {version.major}.{version.minor}.{version.micro}")
        return False


def get_system_info() -> dict:
    """Get system information for optimization"""
    import multiprocessing

    info = {
        'system': platform.system(),
        'machine': platform.machine(),
        'cpu_count': multiprocessing.cpu_count(),
        'python_version': platform.python_version(),
    }

    # Get memory info (platform-specific)
    try:
        if info['system'] == 'Darwin':  # macOS
            result = subprocess.run(['sysctl', 'hw.memsize'],
                                  capture_output=True, text=True)
            mem_bytes = int(result.stdout.split(':')[1].strip())
            info['memory_gb'] = mem_bytes / (1024**3)
        elif info['system'] == 'Linux':
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
                mem_kb = int(meminfo.split('MemTotal:')[1].split('kB')[0].strip())
                info['memory_gb'] = mem_kb / (1024**2)
        else:  # Windows or unknown
            info['memory_gb'] = 8  # Default assumption
    except:
        info['memory_gb'] = 8  # Default if detection fails

    return info


def recommend_model(sys_info: dict) -> Tuple[str, str]:
    """Recommend optimal model based on system specs"""
    memory_gb = sys_info['memory_gb']
    cpu_count = sys_info['cpu_count']

    if memory_gb < 6:
        return "1.5b", "Ultra-light (best for low-memory systems)"
    elif memory_gb < 12 or cpu_count < 6:
        return "1.5b", "Ultra-light (recommended for your system)"
    elif memory_gb < 16:
        return "3b", "Balanced (good quality/speed trade-off)"
    else:
        return "3b", "Balanced (recommended for your system, can also try 7b)"


def install_dependencies(skip_heavy: bool = False) -> bool:
    """Install Python dependencies"""
    print_info("Installing Python dependencies...")

    try:
        # Core dependencies (always install)
        core_deps = [
            "pydantic>=2.0.0",
            "pyyaml>=6.0",
            "click>=8.0.0",
            "rich>=13.0.0",
            "httpx>=0.25.0",
            "fastapi>=0.104.0",
            "numpy>=1.24.0",
            "scipy>=1.10.0",
        ]

        print_info("Installing core dependencies...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", "pip"
        ])
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--quiet"
        ] + core_deps)
        print_success("Core dependencies installed")

        # Heavy dependencies (optional)
        if not skip_heavy:
            print_info("Installing AI/ML dependencies (this may take a while)...")
            print_warning("This will download ~500MB of packages")

            response = input(f"{YELLOW}Continue? [Y/n]: {RESET}").strip().lower()
            if response and response != 'y':
                print_warning("Skipping heavy dependencies (you can install later)")
                return True

            # Try to install llama-cpp-python
            print_info("Installing llama-cpp-python (may require compilation)...")
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", "--quiet",
                    "llama-cpp-python>=0.2.90"
                ])
                print_success("llama-cpp-python installed")
            except:
                print_warning("llama-cpp-python installation failed")
                print_info("You may need to install build tools:")
                if platform.system() == 'Darwin':
                    print_info("  macOS: brew install cmake")
                elif platform.system() == 'Linux':
                    print_info("  Linux: sudo apt-get install build-essential cmake")
                else:
                    print_info("  Windows: Install Visual Studio Build Tools")
                return False

            # Install sentence-transformers
            print_info("Installing sentence-transformers...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "--quiet",
                "sentence-transformers>=2.2.0"
            ])
            print_success("sentence-transformers installed")

        return True

    except Exception as e:
        print_error(f"Dependency installation failed: {e}")
        return False


def download_model(model_size: str, force: bool = False) -> bool:
    """Download model file with progress"""
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)

    # Model URLs and info
    models = {
        "1.5b": {
            "url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
            "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
            "size_mb": 934,
            "sha256": None  # Add if available for verification
        },
        "3b": {
            "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
            "filename": "qwen2.5-3b-instruct-q4_k_m.gguf",
            "size_mb": 1900,
            "sha256": None
        },
        "7b": {
            "url": "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf",
            "filename": "qwen2.5-7b-instruct-q4_k_m.gguf",
            "size_mb": 4370,
            "sha256": None
        }
    }

    if model_size not in models:
        print_error(f"Unknown model size: {model_size}")
        return False

    model_info = models[model_size]
    model_path = models_dir / model_info["filename"]

    # Check if already downloaded
    if model_path.exists() and not force:
        print_success(f"Model already downloaded: {model_path}")
        return True

    print_info(f"Downloading {model_size.upper()} model (~{model_info['size_mb']}MB)")
    print_warning("This may take several minutes depending on your connection...")

    try:
        # Download with progress
        def report_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(100, (downloaded * 100) // total_size)
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)

            # Update progress line
            print(f"\r{BLUE}  Progress: {percent:3d}% ({mb_downloaded:6.1f}/{mb_total:.1f} MB){RESET}",
                  end='', flush=True)

        urllib.request.urlretrieve(
            model_info["url"],
            model_path,
            reporthook=report_progress
        )
        print()  # New line after progress

        # Verify file size
        actual_size_mb = model_path.stat().st_size / (1024 * 1024)
        if actual_size_mb < model_info["size_mb"] * 0.9:
            print_error(f"Download incomplete. Expected ~{model_info['size_mb']}MB, got {actual_size_mb:.1f}MB")
            model_path.unlink()
            return False

        print_success(f"Model downloaded: {model_path}")
        return True

    except Exception as e:
        print_error(f"Download failed: {e}")
        if model_path.exists():
            model_path.unlink()
        return False


def create_config(model_size: str, sys_info: dict) -> bool:
    """Create optimized configuration file"""
    config_path = Path("pebblemind.yaml")

    if config_path.exists():
        response = input(f"{YELLOW}Config file exists. Overwrite? [y/N]: {RESET}").strip().lower()
        if response != 'y':
            print_info("Keeping existing configuration")
            return True

    # Optimize settings based on system
    threads = min(6, max(2, sys_info['cpu_count'] - 2))
    context_length = 2048 if sys_info['memory_gb'] < 12 else 4096

    models = {
        "1.5b": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "3b": "qwen2.5-3b-instruct-q4_k_m.gguf",
        "7b": "qwen2.5-7b-instruct-q4_k_m.gguf",
    }

    config_content = f"""# PebbleMind Configuration
# Auto-generated for {sys_info['system']} with {sys_info['memory_gb']:.1f}GB RAM

# LLM Configuration - Optimized for your system
llm:
  model_size: "{model_size}"
  model_path: "models/{models[model_size]}"
  model_name: "Qwen2.5-{model_size.upper()}-Instruct"
  context_length: {context_length}
  max_tokens: 256
  temperature: 0.7
  top_p: 0.9
  top_k: 40
  threads: {threads}  # Optimized for {sys_info['cpu_count']} CPU cores
  batch_size: 512
  enable_blas: true
  blas_vendor: "OpenBLAS"
  enable_gpu_offload: false  # Set to true if you have a GPU
  gpu_layers: 0
  auto_detect_gpu: true
  enable_native: true

# Voice Configuration (optional)
voice:
  stt_model: "base.en"
  stt_threads: 4
  tts_model: "amy-low"
  tts_threads: 4
  sample_rate: 22050
  channels: 1

# RAG System Configuration
rag:
  embedding_model: "BAAI/bge-small-en-v1.5"
  embedding_dim: 384
  vector_db_path: "./data/vectors.db"
  chunk_size: 512
  chunk_overlap: 50
  max_results: 5

# Cache Configuration
cache:
  enabled: true
  max_size: 1000
  default_ttl: 300  # 5 minutes
  max_memory_mb: 100

# API Configuration
api:
  host: "127.0.0.1"
  port: 8000
  cors_origins: ["http://localhost:3000"]

# Logging
log_level: "INFO"
data_path: "./data"
cache_path: "./cache"
"""

    try:
        with open(config_path, 'w') as f:
            f.write(config_content)
        print_success(f"Configuration created: {config_path}")
        print_info(f"Optimized for: {threads} threads, {context_length} context length")
        return True
    except Exception as e:
        print_error(f"Failed to create config: {e}")
        return False


def create_example_script():
    """Create a simple example script"""
    example_path = Path("examples/simple_chat.py")
    example_path.parent.mkdir(exist_ok=True)

    script_content = '''"""
Simple chat example for PebbleMind
Run: python examples/simple_chat.py
"""

import asyncio
from pathlib import Path
from pebblemind.config import Config, get_config
from pebblemind.core.llm import LLMEngine

async def main():
    """Simple interactive chat"""
    print("\\n🤖 PebbleMind Simple Chat")
    print("=" * 50)
    print("Type 'quit' to exit\\n")

    # Load configuration
    config = get_config()

    # Initialize LLM engine
    print("Loading model (this may take a few seconds)...")
    engine = LLMEngine(config.llm)
    await engine.initialize()

    print(f"✅ Ready! Using {config.llm.model_size.upper()} model\\n")

    # Chat loop
    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                break

            if not user_input:
                continue

            print("AI: ", end='', flush=True)
            response = await engine.generate(user_input)
            print(response)
            print()

        except KeyboardInterrupt:
            print("\\n\\nExiting...")
            break
        except Exception as e:
            print(f"\\nError: {e}")
            print("Continuing...\\n")

    # Cleanup
    await engine.cleanup()
    print("\\nGoodbye! 👋")

if __name__ == "__main__":
    asyncio.run(main())
'''

    try:
        with open(example_path, 'w') as f:
            f.write(script_content)
        print_success(f"Example created: {example_path}")
        return True
    except Exception as e:
        print_error(f"Failed to create example: {e}")
        return False


def main():
    """Main installer flow"""
    print_header("PebbleMind Installer")
    print(f"{BOLD}Privacy-First Local AI Assistant{RESET}\n")

    # Step 1: Check Python version
    if not check_python_version():
        sys.exit(1)

    # Step 2: Get system info and recommend model
    print_info("Analyzing system...")
    sys_info = get_system_info()

    print_success(f"System: {sys_info['system']} {sys_info['machine']}")
    print_success(f"CPU Cores: {sys_info['cpu_count']}")
    print_success(f"Memory: {sys_info['memory_gb']:.1f} GB")

    recommended_model, reason = recommend_model(sys_info)
    print_info(f"Recommended model: {recommended_model.upper()} - {reason}")

    # Step 3: Choose installation type
    print_header("Installation Options")
    print("1. Full Install (everything including AI models)")
    print("2. Quick Test (dependencies only, no models)")
    print("3. Custom (choose what to install)")

    choice = input(f"\n{BLUE}Choose [1/2/3]: {RESET}").strip()

    install_deps = True
    download_models = True
    create_examples = True

    if choice == '2':
        download_models = False
        print_info("Quick test mode: skipping model download")
    elif choice == '3':
        install_deps = input(f"{BLUE}Install dependencies? [Y/n]: {RESET}").strip().lower() != 'n'
        download_models = input(f"{BLUE}Download model? [Y/n]: {RESET}").strip().lower() != 'n'
        create_examples = input(f"{BLUE}Create examples? [Y/n]: {RESET}").strip().lower() != 'n'

    # Step 4: Install dependencies
    if install_deps:
        print_header("Installing Dependencies")
        if not install_dependencies(skip_heavy=not download_models):
            print_warning("Dependency installation incomplete")
            if not download_models:
                print_info("This is OK for testing, but you'll need them to run models")

    # Step 5: Download model
    if download_models:
        print_header("Downloading AI Model")

        # Confirm model choice
        print(f"Default: {recommended_model.upper()}")
        print("Available: 1.5b (934MB), 3b (1.9GB), 7b (4.4GB)")

        model_choice = input(f"{BLUE}Model size [{recommended_model}]: {RESET}").strip().lower()
        if not model_choice:
            model_choice = recommended_model

        if not download_model(model_choice):
            print_error("Model download failed")
            print_info("You can download manually later")
            model_choice = recommended_model  # Use default for config
    else:
        model_choice = recommended_model

    # Step 6: Create configuration
    print_header("Creating Configuration")
    create_config(model_choice, sys_info)

    # Step 7: Create examples
    if create_examples:
        print_header("Creating Examples")
        create_example_script()

    # Step 8: Final instructions
    print_header("Installation Complete!")

    print(f"{GREEN}✅ PebbleMind is ready!{RESET}\\n")

    print(f"{BOLD}Next Steps:{RESET}")

    if download_models:
        print(f"\\n  1. Test the installation:")
        print(f"     {BLUE}python examples/simple_chat.py{RESET}")
        print(f"\\n  2. Run tests:")
        print(f"     {BLUE}python -m pytest tests/ -v{RESET}")
    else:
        print(f"\\n  1. Run tests (without models):")
        print(f"     {BLUE}python -m pytest tests/ -v{RESET}")
        print(f"\\n  2. Download a model later:")
        print(f"     {BLUE}python install.py{RESET}")

    print(f"\\n  3. Read the docs:")
    print(f"     - {BLUE}QUICKSTART.md{RESET} - 5-minute tutorial")
    print(f"     - {BLUE}INSTALLATION.md{RESET} - Detailed guide")

    print(f"\\n{BOLD}Configuration:{RESET}")
    print(f"  Model: {model_choice.upper()}")
    print(f"  Config: pebblemind.yaml")
    print(f"  Optimized for {sys_info['cpu_count']} cores, {sys_info['memory_gb']:.1f}GB RAM")

    print(f"\\n{BOLD}Happy coding! 🚀{RESET}\\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\\n\\n{YELLOW}Installation cancelled{RESET}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Installation failed: {e}")
        sys.exit(1)
