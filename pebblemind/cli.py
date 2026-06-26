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
