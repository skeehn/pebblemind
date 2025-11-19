"""Rich CLI with progress bars, spinners, and beautiful formatting"""

import asyncio
from typing import Optional, List, Dict, Any, Callable
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.tree import Tree
from rich.live import Live
from rich.layout import Layout
from rich.prompt import Prompt, Confirm
from rich.text import Text
import logging

logger = logging.getLogger(__name__)


class RichCLI:
    """
    Rich CLI interface with beautiful formatting and interactive elements.

    Features:
    - Progress bars for long operations
    - Spinners for async tasks
    - Markdown rendering
    - Syntax highlighting
    - Tables and trees
    - Interactive prompts
    """

    def __init__(self):
        """Initialize Rich CLI"""
        self.console = Console()
        self._active_progress: Optional[Progress] = None

    def print(self, message: str, style: Optional[str] = None):
        """
        Print message with optional styling

        Args:
            message: Message to print
            style: Rich style string (e.g., "bold red", "green")
        """
        self.console.print(message, style=style)

    def print_panel(
        self,
        content: str,
        title: Optional[str] = None,
        style: str = "cyan",
        border_style: str = "blue"
    ):
        """
        Print content in a panel

        Args:
            content: Panel content
            title: Optional panel title
            style: Content style
            border_style: Border style
        """
        panel = Panel(
            content,
            title=title,
            style=style,
            border_style=border_style
        )
        self.console.print(panel)

    def print_markdown(self, markdown: str):
        """
        Render and print markdown

        Args:
            markdown: Markdown content
        """
        md = Markdown(markdown)
        self.console.print(md)

    def print_code(
        self,
        code: str,
        language: str = "python",
        theme: str = "monokai"
    ):
        """
        Print syntax-highlighted code

        Args:
            code: Code to highlight
            language: Programming language
            theme: Color theme
        """
        syntax = Syntax(code, language, theme=theme, line_numbers=True)
        self.console.print(syntax)

    def print_table(
        self,
        data: List[Dict[str, Any]],
        title: Optional[str] = None,
        show_header: bool = True
    ):
        """
        Print data as table

        Args:
            data: List of dictionaries
            title: Optional table title
            show_header: Show table header
        """
        if not data:
            self.print("[yellow]No data to display[/yellow]")
            return

        table = Table(title=title, show_header=show_header)

        # Add columns from first row
        for key in data[0].keys():
            table.add_column(str(key).title(), style="cyan")

        # Add rows
        for row in data:
            table.add_row(*[str(v) for v in row.values()])

        self.console.print(table)

    def print_tree(self, tree_data: Dict[str, Any], title: str = "Tree"):
        """
        Print hierarchical data as tree

        Args:
            tree_data: Nested dictionary
            title: Tree title
        """
        tree = Tree(title)
        self._build_tree(tree, tree_data)
        self.console.print(tree)

    def _build_tree(self, tree: Tree, data: Any, max_depth: int = 10, depth: int = 0):
        """Recursively build tree structure"""
        if depth >= max_depth:
            return

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    branch = tree.add(f"[bold]{key}[/bold]")
                    self._build_tree(branch, value, max_depth, depth + 1)
                else:
                    tree.add(f"{key}: [cyan]{value}[/cyan]")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    branch = tree.add(f"[bold]Item {i}[/bold]")
                    self._build_tree(branch, item, max_depth, depth + 1)
                else:
                    tree.add(f"[cyan]{item}[/cyan]")

    def prompt(
        self,
        message: str,
        default: Optional[str] = None,
        password: bool = False
    ) -> str:
        """
        Interactive prompt for user input

        Args:
            message: Prompt message
            default: Default value
            password: Hide input for passwords

        Returns:
            User input
        """
        return Prompt.ask(
            message,
            default=default,
            password=password,
            console=self.console
        )

    def confirm(self, message: str, default: bool = False) -> bool:
        """
        Yes/no confirmation prompt

        Args:
            message: Confirmation message
            default: Default choice

        Returns:
            True if confirmed
        """
        return Confirm.ask(message, default=default, console=self.console)

    def start_progress(
        self,
        description: str = "Processing...",
        total: Optional[int] = None
    ) -> int:
        """
        Start progress bar

        Args:
            description: Progress description
            total: Total steps (None for indeterminate)

        Returns:
            Task ID for updating progress
        """
        if self._active_progress is None:
            self._active_progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=self.console
            )
            self._active_progress.start()

        task_id = self._active_progress.add_task(description, total=total)
        return task_id

    def update_progress(self, task_id: int, advance: int = 1, description: Optional[str] = None):
        """
        Update progress bar

        Args:
            task_id: Task ID from start_progress
            advance: Steps to advance
            description: Updated description
        """
        if self._active_progress:
            self._active_progress.update(
                task_id,
                advance=advance,
                description=description or self._active_progress.tasks[task_id].description
            )

    def stop_progress(self):
        """Stop progress bar"""
        if self._active_progress:
            self._active_progress.stop()
            self._active_progress = None

    async def spinner(
        self,
        task: Callable,
        description: str = "Processing...",
        success_message: str = "Done!",
        error_message: str = "Failed!"
    ) -> Any:
        """
        Run async task with spinner

        Args:
            task: Async function to execute
            description: Spinner description
            success_message: Message on success
            error_message: Message on error

        Returns:
            Task result
        """
        with self.console.status(description, spinner="dots"):
            try:
                result = await task() if asyncio.iscoroutinefunction(task) else task()
                self.console.print(f"✅ {success_message}", style="green")
                return result
            except Exception as e:
                self.console.print(f"❌ {error_message}: {e}", style="red")
                raise

    def print_error(self, message: str, exception: Optional[Exception] = None):
        """
        Print error message

        Args:
            message: Error message
            exception: Optional exception details
        """
        error_text = f"❌ [bold red]Error:[/bold red] {message}"
        if exception:
            error_text += f"\n[dim]{str(exception)}[/dim]"
        self.console.print(error_text)

    def print_success(self, message: str):
        """Print success message"""
        self.console.print(f"✅ [bold green]{message}[/bold green]")

    def print_warning(self, message: str):
        """Print warning message"""
        self.console.print(f"⚠️  [bold yellow]Warning:[/bold yellow] {message}")

    def print_info(self, message: str):
        """Print info message"""
        self.console.print(f"ℹ️  [bold blue]Info:[/bold blue] {message}")

    def clear(self):
        """Clear console"""
        self.console.clear()

    def rule(self, title: Optional[str] = None, style: str = "blue"):
        """
        Print horizontal rule

        Args:
            title: Optional rule title
            style: Rule style
        """
        self.console.rule(title, style=style)


# Global CLI instance
_cli: Optional[RichCLI] = None


def get_cli() -> RichCLI:
    """Get global CLI instance"""
    global _cli
    if _cli is None:
        _cli = RichCLI()
    return _cli
