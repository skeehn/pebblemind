"""Command Line Interface for PebbleMind"""

import asyncio
import sys
import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner

from .core import PebbleMind, quick_start
from .config import Config, load_config
from .models import ModelManager

console = Console()


@click.group()
@click.option("--config", "-c", type=click.Path(exists=True), help="Path to config file")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx: click.Context, config: Optional[str], verbose: bool):
    """PebbleMind: CPU-First Local AI Assistant

    A privacy-first, CPU-optimized AI assistant that runs entirely on your local machine.
    """
    ctx.ensure_object(dict)

    # Load configuration
    if config:
        ctx.obj["config"] = Config.from_file(config)
    else:
        ctx.obj["config"] = Config()

    # Set logging level
    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)


@cli.group()
def models():
    """Manage language models"""
    pass


@models.command("list")
@click.option("--catalog", is_flag=True, help="Show catalog of available models")
@click.pass_context
def models_list(ctx: click.Context, catalog: bool):
    """List installed models or available models"""
    config = ctx.obj["config"]
    models_dir = Path(config.data_path) / "models"
    manager = ModelManager(models_dir)
    
    if catalog:
        # Show catalog of available models
        console.print("\n[bold blue]📦 Available Models[/bold blue]")
        console.print("=" * 70)
        
        from rich.table import Table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("ID", style="dim")
        table.add_column("Name")
        table.add_column("Size", justify="right")
        table.add_column("Speed")
        table.add_column("Quality")
        table.add_column("Status")
        
        for model_id, info in manager.list_catalog().items():
            model_path = models_dir / info["filename"]
            status = "✅ Installed" if model_path.exists() else "⬇️  Available"
            
            table.add_row(
                model_id,
                info["name"],
                f"{info['size_gb']:.1f}GB",
                info["speed"],
                info["quality"],
                status
            )
        
        console.print(table)
        console.print(f"\n[dim]Install with: pebblemind models install <id>[/dim]\n")
        
    else:
        # Show installed models
        installed = manager.list_installed()
        
        if not installed:
            console.print("\n[yellow]No models installed yet.[/yellow]")
            console.print("Browse available models: [cyan]pebblemind models list --catalog[/cyan]\n")
            return
        
        console.print("\n[bold blue]💾 Installed Models[/bold blue]")
        console.print("=" * 70)
        
        from rich.table import Table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Name")
        table.add_column("Size", justify="right")
        table.add_column("Path", style="dim")
        
        for model in installed:
            table.add_row(
                model["name"],
                f"{model['size_gb']:.2f}GB",
                model["path"]
            )
        
        console.print(table)
        console.print()


@models.command("install")
@click.argument("model_id")
@click.pass_context
def models_install(ctx: click.Context, model_id: str):
    """Install a model from the catalog"""
    config = ctx.obj["config"]
    models_dir = Path(config.data_path) / "models"
    manager = ModelManager(models_dir)
    
    # Check if model exists in catalog
    model_info = manager.get_model_info(model_id)
    if not model_info:
        console.print(f"[red]❌ Model '{model_id}' not found in catalog[/red]")
        console.print("Available models: [cyan]pebblemind models list --catalog[/cyan]")
        return
    
    # Check if already installed
    if model_info["installed"]:
        console.print(f"[yellow]Model already installed: {model_info['path']}[/yellow]")
        return
    
    console.print(f"\n[bold blue]📥 Installing {model_info['name']}[/bold blue]")
    console.print(f"Size: {model_info['size_gb']:.1f}GB")
    console.print(f"Use case: {model_info['use_case']}\n")
    
    # Download with progress bar
    from rich.progress import Progress, BarColumn, DownloadColumn, TimeRemainingColumn
    
    with Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        DownloadColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        task_id = progress.add_task("Downloading...", total=model_info["size_gb"] * 1024**3)
        
        def update_progress(downloaded, total, percent):
            progress.update(task_id, completed=downloaded)
        
        try:
            model_path = manager.download(model_id, progress_callback=update_progress)
            
            console.print(f"\n[green]✅ Model installed successfully![/green]")
            console.print(f"Path: {model_path}")
            console.print(f"\n[bold]Set as active model:[/bold]")
            console.print(f"  pebblemind config set llm.model_path {model_path}\n")
            
        except Exception as e:
            console.print(f"\n[red]❌ Download failed: {e}[/red]")


@models.command("info")
@click.argument("model_id")
@click.pass_context
def models_info(ctx: click.Context, model_id: str):
    """Show detailed information about a model"""
    config = ctx.obj["config"]
    models_dir = Path(config.data_path) / "models"
    manager = ModelManager(models_dir)
    
    model_info = manager.get_model_info(model_id)
    
    if not model_info:
        console.print(f"[red]❌ Model '{model_id}' not found in catalog[/red]")
        return
    
    console.print(f"\n[bold blue]{model_info['name']}[/bold blue]")
    console.print("=" * 50)
    console.print(f"\n[bold]ID:[/bold] {model_id}")
    console.print(f"[bold]Size:[/bold] {model_info['size_gb']:.1f}GB")
    console.print(f"[bold]Speed:[/bold] {model_info['speed']}")
    console.print(f"[bold]Quality:[/bold] {model_info['quality']}")
    console.print(f"[bold]Status:[/bold] {'✅ Installed' if model_info['installed'] else '⬇️  Not installed'}")
    
    if model_info["installed"]:
        console.print(f"[bold]Path:[/bold] {model_info['path']}")
        console.print(f"[bold]Actual Size:[/bold] {model_info['actual_size_gb']:.2f}GB")
    
    console.print(f"\n[bold]Description:[/bold]")
    console.print(f"  {model_info['description']}")
    console.print(f"\n[bold]Best for:[/bold]")
    console.print(f"  {model_info['use_case']}")
    
    if not model_info["installed"]:
        console.print(f"\n[dim]Install: pebblemind models install {model_id}[/dim]")
    
    console.print()


@models.command("remove")
@click.argument("model_id")
@click.confirmation_option(prompt="Are you sure you want to remove this model?")
@click.pass_context
def models_remove(ctx: click.Context, model_id: str):
    """Remove an installed model"""
    config = ctx.obj["config"]
    models_dir = Path(config.data_path) / "models"
    manager = ModelManager(models_dir)
    
    model_info = manager.get_model_info(model_id)
    
    if not model_info:
        console.print(f"[red]❌ Model '{model_id}' not found[/red]")
        return
    
    if not model_info["installed"]:
        console.print(f"[yellow]Model not installed[/yellow]")
        return
    
    try:
        manager.remove(model_info["path"])
        console.print(f"[green]✅ Model removed: {model_info['name']}[/green]")
    except Exception as e:
        console.print(f"[red]❌ Error removing model: {e}[/red]")


@cli.group()
def config_cmd():
    """Manage configuration"""
    pass


@config_cmd.command("show")
@click.pass_context
def config_show(ctx: click.Context):
    """Show current configuration"""
    config = ctx.obj["config"]
    
    console.print("\n[bold blue]PebbleMind Configuration[/bold blue]")
    console.print("=" * 50)
    
    console.print("\n[bold]LLM Settings:[/bold]")
    console.print(f"  Model Path: {config.llm.model_path or '[dim]Not set[/dim]'}")
    console.print(f"  Model Size: {config.llm.model_size}")
    console.print(f"  Context Length: {config.llm.context_length}")
    console.print(f"  Temperature: {config.llm.temperature}")
    console.print(f"  Max Tokens: {config.llm.max_tokens}")
    console.print(f"  GPU Layers: {config.llm.gpu_layers}")
    
    console.print("\n[bold]Cache Settings:[/bold]")
    console.print(f"  Enabled: {'✅' if config.cache.enabled else '❌'}")
    console.print(f"  Max Size: {config.cache.max_size}")
    console.print(f"  TTL: {config.cache.ttl}s")
    
    console.print("\n[bold]RAG Settings:[/bold]")
    console.print(f"  Enabled: {'✅' if config.rag.enabled else '❌'}")
    console.print(f"  Embedding Model: {config.rag.embedding_model}")
    console.print(f"  Chunk Size: {config.rag.chunk_size}")
    console.print(f"  Chunk Overlap: {config.rag.chunk_overlap}")
    console.print(f"  Top K Results: {config.rag.top_k}")
    
    console.print("\n[bold]Paths:[/bold]")
    console.print(f"  Data: {config.data_path}")
    console.print(f"  Cache: {config.cache_path}")
    console.print(f"  Config: {config.config_path}\n")


@config_cmd.command("set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str):
    """Set configuration value"""
    config = ctx.obj["config"]
    
    # Parse key path (e.g., "llm.temperature")
    parts = key.split(".")
    if len(parts) != 2:
        console.print(f"[red]Invalid key format. Use: section.key (e.g., llm.temperature)[/red]")
        return
    
    section, setting = parts
    
    try:
        # Get the section object
        if not hasattr(config, section):
            console.print(f"[red]Unknown section: {section}[/red]")
            return
        
        section_obj = getattr(config, section)
        
        if not hasattr(section_obj, setting):
            console.print(f"[red]Unknown setting: {setting} in {section}[/red]")
            return
        
        # Convert value to appropriate type
        current_value = getattr(section_obj, setting)
        if isinstance(current_value, bool):
            value = value.lower() in ["true", "1", "yes", "on"]
        elif isinstance(current_value, int):
            value = int(value)
        elif isinstance(current_value, float):
            value = float(value)
        
        # Set the value
        setattr(section_obj, setting, value)
        
        # Save configuration
        config.save()
        
        console.print(f"[green]✓ Set {key} = {value}[/green]")
        
    except Exception as e:
        console.print(f"[red]Error setting config: {e}[/red]")


@cli.command()
@click.pass_context
def doctor(ctx: click.Context):
    """Check system health and configuration"""
    config = ctx.obj["config"]
    
    console.print("\n[bold blue]🏥 PebbleMind Health Check[/bold blue]")
    console.print("=" * 50)
    
    issues = []
    warnings = []
    
    # Check Python version
    import sys
    py_version = sys.version_info
    console.print(f"\n[bold]Python:[/bold]")
    if 3 <= py_version.major <= 3 and 10 <= py_version.minor <= 12:
        console.print(f"  ✅ Version {py_version.major}.{py_version.minor}.{py_version.micro}")
    elif py_version.minor == 13:
        console.print(f"  ⚠️  Version {py_version.major}.{py_version.minor}.{py_version.micro} (llama-cpp-python may need build tools)")
        warnings.append("Python 3.13 requires C++ build tools for llama-cpp-python")
    else:
        console.print(f"  ❌ Version {py_version.major}.{py_version.minor}.{py_version.micro} (need 3.10-3.12)")
        issues.append("Python version not in recommended range (3.10-3.12)")
    
    # Check dependencies
    console.print(f"\n[bold]Dependencies:[/bold]")
    deps_ok = True
    
    try:
        import llama_cpp
        console.print(f"  ✅ llama-cpp-python installed")
    except ImportError:
        console.print(f"  ❌ llama-cpp-python not found")
        issues.append("llama-cpp-python not installed")
        deps_ok = False
    
    try:
        import numpy
        console.print(f"  ✅ numpy installed")
    except ImportError:
        console.print(f"  ⚠️  numpy not found")
        warnings.append("numpy recommended for better performance")
    
    try:
        import scipy
        console.print(f"  ✅ scipy installed")
    except ImportError:
        console.print(f"  ⚠️  scipy not found")
        warnings.append("scipy recommended for RAG")
    
    # Check model
    console.print(f"\n[bold]Model:[/bold]")
    if config.llm.model_path:
        model_path = Path(config.llm.model_path).expanduser()
        if model_path.exists():
            size_gb = model_path.stat().st_size / (1024**3)
            console.print(f"  ✅ Model found: {model_path}")
            console.print(f"     Size: {size_gb:.2f} GB")
        else:
            console.print(f"  ❌ Model not found: {model_path}")
            issues.append(f"Model file missing: {model_path}")
    else:
        console.print(f"  ⚠️  No model configured")
        warnings.append("No model path set in configuration")
    
    # Check paths
    console.print(f"\n[bold]Paths:[/bold]")
    data_path = Path(config.data_path).expanduser()
    cache_path = Path(config.cache_path).expanduser()
    
    if data_path.exists():
        console.print(f"  ✅ Data directory: {data_path}")
    else:
        console.print(f"  ⚠️  Data directory will be created: {data_path}")
    
    if cache_path.exists():
        console.print(f"  ✅ Cache directory: {cache_path}")
    else:
        console.print(f"  ⚠️  Cache directory will be created: {cache_path}")
    
    # Check disk space
    import shutil
    total, used, free = shutil.disk_usage(Path.home())
    free_gb = free / (1024**3)
    console.print(f"\n[bold]Disk Space:[/bold]")
    if free_gb > 10:
        console.print(f"  ✅ {free_gb:.1f} GB free")
    elif free_gb > 5:
        console.print(f"  ⚠️  {free_gb:.1f} GB free (models need 3-7 GB)")
        warnings.append("Low disk space - may not fit larger models")
    else:
        console.print(f"  ❌ {free_gb:.1f} GB free (insufficient)")
        issues.append("Not enough disk space for models")
    
    # Summary
    console.print(f"\n[bold]Summary:[/bold]")
    if not issues and not warnings:
        console.print("  ✅ [green]All checks passed! System is healthy.[/green]")
    elif issues:
        console.print(f"  ❌ [red]{len(issues)} issue(s) found:[/red]")
        for issue in issues:
            console.print(f"     • {issue}")
    elif warnings:
        console.print(f"  ⚠️  [yellow]{len(warnings)} warning(s):[/yellow]")
        for warning in warnings:
            console.print(f"     • {warning}")
    
    # Next steps
    if issues:
        console.print(f"\n[bold]Next Steps:[/bold]")
        console.print("  1. Fix critical issues above")
        console.print("  2. See INSTALLATION.md for setup guide")
        console.print("  3. Run 'pebblemind doctor' again to verify\n")
    elif not config.llm.model_path:
        console.print(f"\n[bold]Quick Start:[/bold]")
        console.print("  1. Download a model (see INSTALLATION.md)")
        console.print("  2. Set model path: pebblemind config set llm.model_path /path/to/model")
        console.print("  3. Try: pebblemind chat 'Hello!'\n")


@cli.command()
@click.pass_context
def status(ctx: click.Context):
    """Show system status"""
    config = ctx.obj["config"]

    try:
        pebblemind = quick_start()

        async def get_status():
            return await pebblemind.get_status()

        status_info = asyncio.run(get_status())

        # Display status information
        console.print("\n[bold blue]PebbleMind Status[/bold blue]")
        console.print("=" * 40)

        console.print(f"Initialized: {'✅' if status_info['initialized'] else '❌'}")
        console.print(f"Running: {'✅' if status_info['running'] else '❌'}")

        console.print("\n[bold]Components:[/bold]")
        for component, available in status_info['components'].items():
            status_icon = "✅" if available else "❌"
            console.print(f"  {component}: {status_icon}")

        console.print(f"\nData Directory: {config.data_path}")
        console.print(f"Cache Directory: {config.cache_path}")

        # Show model information
        if status_info['components']['llm']:
            async def get_model_info():
                return await pebblemind.llm_engine.get_model_info()

            model_info = asyncio.run(get_model_info())
            if model_info.get('status') == 'loaded':
                console.print(f"\n[bold]Current Model:[/bold]")
                console.print(f"  Name: {model_info.get('model_name', 'Unknown')}")
                console.print(f"  Size: {model_info.get('model_size', 'Unknown')}")
                console.print(f"  File Size: {model_info.get('file_size_gb', 0):.2f} GB")
                console.print(f"  GPU Offload: {'Enabled' if model_info.get('gpu_offload_enabled') else 'Disabled'}")
                if model_info.get('gpu_offload_enabled'):
                    console.print(f"  GPU Layers: {model_info.get('gpu_layers', 0)}")
                console.print(f"  Available Models: {', '.join(model_info.get('available_models', []))}")

    except Exception as e:
        console.print(f"[red]Error getting status: {e}[/red]")


@cli.command()
@click.option("--model", "-m", help="Path to LLM model file")
@click.option("--model-size", help="Model size: 1.5b, 3b, 7b")
@click.option("--interactive", "-i", is_flag=True, help="Start interactive chat")
@click.argument("message", required=False)
@click.pass_context
def chat(ctx: click.Context, model: Optional[str], model_size: Optional[str], interactive: bool, message: Optional[str]):
    """Chat with PebbleMind"""
    config = ctx.obj["config"]

    # Update model configuration if provided
    if model:
        config.llm.model_path = model
    if model_size:
        if model_size not in ["1.5b", "3b", "7b"]:
            console.print(f"[red]Invalid model size: {model_size}. Use: 1.5b, 3b, 7b[/red]")
            return
        config.llm.model_size = model_size

    try:
        pebblemind = quick_start()

        # Warn when no real model is loaded, so fallback responses aren't
        # mistaken for real inference.
        if type(pebblemind.llm_engine).__name__ == "_FallbackLLMEngine":
            console.print(
                "[yellow]⚠ No local model loaded — running in limited fallback "
                "mode. Install a model for real answers (see INSTALLATION.md).[/yellow]"
            )

        if message:
            # Single message mode
            async def single_query():
                with console.status("[bold green]Thinking...", spinner="dots"):
                    response = await pebblemind.query(message)
                return response

            response = asyncio.run(single_query())

            # Display response
            console.print("\n[bold blue]Response:[/bold blue]")
            console.print(Panel.fit(response, border_style="blue"))

        elif interactive:
            # Interactive chat mode
            console.print("[bold green]Welcome to PebbleMind Interactive Chat![/bold green]")
            console.print("Type 'quit' or 'exit' to end the conversation.\n")

            conversation_history = []

            while True:
                # Get user input
                user_input = Prompt.ask("[bold cyan]You[/bold cyan]")

                if user_input.lower() in ['quit', 'exit', 'q']:
                    console.print("[yellow]Goodbye! 👋[/yellow]")
                    break

                if not user_input.strip():
                    continue

                # Add to conversation history
                conversation_history.append(user_input)

                # Get response
                async def get_response():
                    with console.status("[bold green]Thinking...", spinner="dots"):
                        response = await pebblemind.query(
                            user_input,
                            context=conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
                        )
                    return response

                response = asyncio.run(get_response())

                # Display response
                console.print(f"\n[bold green]PebbleMind[/bold green]: {response}\n")

        else:
            console.print("[red]Please provide a message or use --interactive flag[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.argument("audio_file", type=click.Path(exists=True))
@click.pass_context
def transcribe(ctx: click.Context, audio_file: str):
    """Transcribe audio file to text"""
    config = ctx.obj["config"]

    try:
        pebblemind = quick_start()

        # Read audio file
        with open(audio_file, "rb") as f:
            audio_data = f.read()

        async def transcribe_audio():
            with console.status("[bold green]Transcribing...", spinner="dots"):
                text = await pebblemind.voice_processor.speech_to_text(audio_data)
            return text

        transcription = asyncio.run(transcribe_audio())

        console.print("\n[bold blue]Transcription:[/bold blue]")
        console.print(Panel.fit(transcription, border_style="blue"))

    except Exception as e:
        console.print(f"[red]Error transcribing audio: {e}[/red]")


@cli.command()
@click.argument("text")
@click.option("--output", "-o", type=click.Path(), help="Output audio file path")
@click.pass_context
def speak(ctx: click.Context, text: str, output: Optional[str]):
    """Convert text to speech"""
    config = ctx.obj["config"]

    try:
        pebblemind = quick_start()

        async def generate_speech():
            with console.status("[bold green]Generating speech...", spinner="dots"):
                audio_data = await pebblemind.voice_processor.text_to_speech(text)
            return audio_data

        audio_data = asyncio.run(generate_speech())

        if output:
            # Save to file
            with open(output, "wb") as f:
                f.write(audio_data)
            console.print(f"[green]Audio saved to: {output}[/green]")
        else:
            console.print("[yellow]Audio generated successfully (use --output to save to file)[/yellow]")

    except Exception as e:
        console.print(f"[red]Error generating speech: {e}[/red]")


@cli.command()
@click.argument("documents", nargs=-1, type=click.Path(exists=True))
@click.option("--recursive", "-r", is_flag=True, help="Recursively add documents from directories")
@click.pass_context
def add_docs(ctx: click.Context, documents: tuple, recursive: bool):
    """Add documents to the RAG system"""
    config = ctx.obj["config"]

    if not documents:
        console.print("[red]Please provide document paths[/red]")
        return

    try:
        pebblemind = quick_start()

        # Collect all documents
        doc_list = []

        for doc_path in documents:
            path = Path(doc_path)

            if path.is_file():
                # Single file
                if path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx']:
                    doc_list.append({
                        "content": path.read_text(),
                        "metadata": {"source": str(path), "type": path.suffix}
                    })
                else:
                    console.print(f"[yellow]Skipping unsupported file: {path}[/yellow]")

            elif path.is_dir() and recursive:
                # Directory with recursion
                for file_path in path.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx']:
                        try:
                            doc_list.append({
                                "content": file_path.read_text(),
                                "metadata": {"source": str(file_path), "type": file_path.suffix}
                            })
                        except Exception as e:
                            console.print(f"[yellow]Error reading {file_path}: {e}[/yellow]")

        if not doc_list:
            console.print("[red]No valid documents found[/red]")
            return

        # Add documents to RAG system
        async def add_documents():
            with console.status(f"[bold green]Adding {len(doc_list)} documents...", spinner="dots"):
                await pebblemind.add_documents(doc_list)

        asyncio.run(add_documents())
        console.print(f"[green]Successfully added {len(doc_list)} documents to RAG system[/green]")

    except Exception as e:
        console.print(f"[red]Error adding documents: {e}[/red]")


@cli.command()
@click.argument("model_size", type=click.Choice(["1.5b", "3b", "7b"]))
@click.pass_context
def switch_model(ctx: click.Context, model_size: str):
    """Switch to a different model size"""
    config = ctx.obj["config"]

    try:
        pebblemind = quick_start()

        async def switch():
            with console.status(f"[bold green]Switching to {model_size} model...", spinner="dots"):
                success = await pebblemind.llm_engine.switch_model(model_size)
            return success

        success = asyncio.run(switch())

        if success:
            console.print(f"[green]Successfully switched to {model_size} model[/green]")
            
            # Show model info
            async def get_info():
                return await pebblemind.llm_engine.get_model_info()

            info = asyncio.run(get_info())
            console.print(f"\n[bold]Model Details:[/bold]")
            console.print(f"  Name: {info.get('model_name', 'Unknown')}")
            console.print(f"  Size: {info.get('model_size', 'Unknown').upper()}")
            console.print(f"  File Size: {info.get('file_size_gb', 0):.2f} GB")
            console.print(f"  GPU Available: {'Yes' if info.get('gpu_available') else 'No'}")
            console.print(f"  GPU Offload: {'Enabled' if info.get('gpu_offload_enabled') else 'Disabled'}")
            if info.get('gpu_offload_enabled'):
                console.print(f"  GPU Layers: {info.get('gpu_layers', 0)}")
            
            # Performance tip
            if model_size == "7b" and not info.get('gpu_offload_enabled'):
                console.print(f"\n[yellow]💡 Tip: Enable GPU offloading for better 7B model performance[/yellow]")
            elif model_size == "1.5b":
                console.print(f"\n[blue]⚡ Ultra-light model active - fastest CPU responses[/blue]")
                console.print(f"\n[green]✅ Recommended for MacBook Air and lightweight devices[/green]")
            elif model_size == "3b":
                console.print(f"\n[green]⚖️  Balanced model active - optimal quality/speed ratio[/green]")
                console.print(f"\n[yellow]⚠️  Consider 1.5B model for better performance on MacBook Air[/yellow]")
        else:
            console.print(f"[red]Failed to switch to {model_size} model[/red]")

    except Exception as e:
        console.print(f"[red]Error switching model: {e}[/red]")


@cli.command()
@click.pass_context
def stats(ctx: click.Context):
    """Show RAG system statistics"""
    config = ctx.obj["config"]

    try:
        pebblemind = quick_start()

        if pebblemind.rag_system is None:
            console.print(
                "[yellow]RAG system is disabled[/yellow] — install the vector-search "
                "extras to enable it:\n  pip install sentence-transformers sqlite-vec"
            )
            return

        async def get_stats():
            return await pebblemind.rag_system.get_stats()

        stats_info = asyncio.run(get_stats())

        console.print("\n[bold blue]RAG System Statistics[/bold blue]")
        console.print("=" * 40)

        console.print(f"Total Documents: {stats_info.get('total_documents', 'N/A')}")
        console.print(f"Database Size: {stats_info.get('database_size_mb', 0):.2f} MB")
        console.print(f"Vector Search: {'✅' if stats_info.get('vector_search_enabled') else '❌'}")
        console.print(f"Embedding Dimension: {stats_info.get('embedding_dimension', 'N/A')}")
        console.print(f"Embedding Model: {stats_info.get('embedding_model', 'N/A')}")

    except Exception as e:
        console.print(f"[red]Error getting statistics: {e}[/red]")


@cli.command()
@click.option("--host", default="localhost", help="API server host")
@click.option("--port", default=8000, type=int, help="API server port")
@click.pass_context
def serve(ctx: click.Context, host: str, port: int):
    """Start the API server"""
    config = ctx.obj["config"]

    # Update API config
    config.api.host = host
    config.api.port = port

    try:
        pebblemind = quick_start()

        async def start_server():
            await pebblemind.start()

        console.print(f"[green]Starting PebbleMind API server on {host}:{port}[/green]")
        console.print("[dim]Press Ctrl+C to stop[/dim]")

        asyncio.run(start_server())

    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]Error starting server: {e}[/red]")


@cli.command()
@click.option("--output", "-o", type=click.Path(), help="Output configuration file path")
@click.pass_context
def init(ctx: click.Context, output: Optional[str]):
    """Initialize a new PebbleMind configuration file"""
    config = ctx.obj["config"]

    if output:
        config_path = Path(output)
    else:
        config_path = Path("./pebblemind.yaml")

    try:
        config.to_file(str(config_path))
        console.print(f"[green]Configuration file created: {config_path}[/green]")

        # Show configuration template
        console.print("\n[bold blue]Configuration Overview:[/bold blue]")
        console.print("- Edit the configuration file to customize PebbleMind")
        console.print("- Set model paths, adjust parameters, and configure components")
        console.print("- Use 'pebblemind --config <path>' to use custom configuration")

    except Exception as e:
        console.print(f"[red]Error creating configuration: {e}[/red]")


def main():
    """Main entry point"""
    cli()


if __name__ == "__main__":
    main()
