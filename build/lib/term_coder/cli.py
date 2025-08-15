from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.progress import Progress

from .config import Config, ensure_initialized
from .index import IndexSystem
from .runner import CommandRunner
from .search import LexicalSearch, HybridSearch
from .semantic import SemanticSearch


console = Console()
app = typer.Typer(add_completion=False, help="Term Coder - repo-aware coding assistant")


def _load_config() -> Config:
    try:
        return Config.load()
    except FileNotFoundError:
        console.print("[yellow]Config not found. Run 'tc init' to set up.[/yellow]")
        raise typer.Exit(code=1)


@app.command()
def init() -> None:
    """Initialize configuration at .term-coder/config.yaml"""
    path = ensure_initialized()
    console.print(f"[green]Initialized config at {path}[/green]")


@app.command()
def config(key: Optional[str] = typer.Argument(None), value: Optional[str] = typer.Argument(None)) -> None:
    """Get or set configuration values. Usage: tc config key [value]"""
    cfg = _load_config()
    if key is None:
        console.print(Markdown("```yaml\n" + cfg.to_yaml() + "\n```"))
        return
    if value is None:
        current = cfg.get(key)
        console.print(f"{key}: {current}")
    else:
        cfg.set(key, value)
        cfg.save()
        console.print(f"[green]Updated {key}[/green]")


@app.command()
def chat(prompt: List[str] = typer.Argument(..., help="Your prompt text")) -> None:
    """Interactive chat with styled output."""
    _ = _load_config()
    text = " ".join(prompt)
    with Live(console=console, refresh_per_second=8):
        console.print(Panel(f"[bold cyan]You:[/bold cyan] {text}", title="Input", border_style="cyan"))
        console.print(Panel("[bold magenta]AI:[/bold magenta] (streaming stub)", title="Response", border_style="magenta"))


@app.command()
def index(
    include: List[str] = typer.Option(None, "--include", help="Glob patterns to include"),
    exclude: List[str] = typer.Option(None, "--exclude", help="Glob patterns to exclude"),
) -> None:
    """Build a lightweight TSV index of text files with a styled summary."""
    cfg = _load_config()
    idx = IndexSystem(cfg)
    stats = idx.build_index(Path.cwd(), include=include, exclude=exclude)
    table = Table(title="Index Summary")
    table.add_column("Total Files", justify="right", style="cyan")
    table.add_column("Indexed Files", justify="right", style="green")
    table.add_row(str(stats.total_files), str(stats.indexed_files))
    console.print(table)


@app.command()
def run(command: List[str] = typer.Argument(..., help="Shell command to execute"), timeout: int = typer.Option(30, help="Timeout in seconds")) -> None:
    """Execute a shell command with styled output."""
    _ = _load_config()
    runner = CommandRunner()
    result = runner.run_command(" ".join(command), timeout=timeout)
    console.print(Panel("stdout", title="Output", border_style="green"))
    if result.stdout:
        console.print(result.stdout)
    console.print(Panel("stderr", title="Errors", border_style="red"))
    if result.stderr:
        console.print(result.stderr)
    console.print(Panel(f"[bold]Exit:[/bold] {result.exit_code}  [bold]Time:[/bold] {result.execution_time:.2f}s", title="Summary", border_style="blue"))


@app.command()
def search(
    query: List[str] = typer.Argument(..., help="Query string"),
    include: List[str] = typer.Option(None, "--include"),
    exclude: List[str] = typer.Option(None, "--exclude"),
    top: int = typer.Option(20, help="Max results"),
    semantic: bool = typer.Option(False, "--semantic", help="Use semantic search"),
    hybrid: bool = typer.Option(False, "--hybrid", help="Combine lexical and semantic"),
) -> None:
    """Search across repository with styled results."""
    _ = _load_config()
    q = " ".join(query)
    cwd = Path.cwd()

    if hybrid:
        engine = HybridSearch(cwd)
        results = engine.search(q, include=include, exclude=exclude, top=top)
        for path, score in results:
            console.print(Panel(f"[bold]{path}[/bold]  score={score:.3f}", border_style="cyan"))
        return

    if semantic:
        engine = SemanticSearch(cwd)
        results = engine.search(q, top_k=top, include=include, exclude=exclude)
        for path, score in results:
            console.print(Panel(f"[bold]{path}[/bold]  score={score:.3f}", border_style="magenta"))
        return

    engine = LexicalSearch(cwd)
    hits = engine.search(q, include=include, exclude=exclude, limit=top)
    for h in hits:
        console.print(Panel(f"[bold]{h.file_path}:{h.line_number}[/bold]: {h.line_text}", border_style="green"))


@app.command()
def file_search(
    query: str = typer.Argument(..., help="Search term for files"),
    directory: str = typer.Option(".", help="Directory to search in"),
    extension: Optional[str] = typer.Option(None, help="File extension to filter by"),
) -> None:
    """Search for files matching a query."""
    console.print(Panel(f"Searching for files with query: [bold]{query}[/bold]", border_style="cyan"))
    path = Path(directory)
    with Progress() as progress:
        task = progress.add_task("Searching", total=None)
        results = []
        for file in path.rglob(f"*{query}*{extension or ''}"):
            results.append(file)
            progress.console.print(f"Found: {file}")
        progress.update(task, completed=len(results))
    if results:
        table = Table(title="Search Results")
        table.add_column("File Path", style="green")
        for result in results:
            table.add_row(str(result))
        console.print(table)
    else:
        console.print(Panel("No files found.", border_style="red"))


@app.command()
def file_create(
    file_path: str = typer.Argument(..., help="Path of the file to create"),
    content: Optional[str] = typer.Option("", help="Initial content for the file"),
) -> None:
    """Create a new file with optional content."""
    path = Path(file_path)
    if path.exists():
        console.print(Panel(f"[red]File already exists: {file_path}[/red]", border_style="red"))
        return
    path.write_text(content)
    console.print(Panel(f"[green]File created: {file_path}[/green]", border_style="green"))


@app.command()
def file_edit(
    file_path: str = typer.Argument(..., help="Path of the file to edit"),
    new_content: str = typer.Option(..., help="New content to write to the file"),
) -> None:
    """Edit an existing file by replacing its content."""
    path = Path(file_path)
    if not path.exists():
        console.print(Panel(f"[red]File not found: {file_path}[/red]", border_style="red"))
        return
    path.write_text(new_content)
    console.print(Panel(f"[green]File updated: {file_path}[/green]", border_style="green"))


@app.command()
def file_retrieve(
    file_path: str = typer.Argument(..., help="Path of the file to retrieve"),
) -> None:
    """Retrieve and display the content of a file."""
    path = Path(file_path)
    if not path.exists():
        console.print(Panel(f"[red]File not found: {file_path}[/red]", border_style="red"))
        return
    content = path.read_text()
    console.print(Panel(f"[bold]Content of {file_path}:[/bold]\n{content}", border_style="blue"))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
