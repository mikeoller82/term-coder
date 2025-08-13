from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

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
    """Basic stub for streaming chat output (to be implemented)."""
    _ = _load_config()
    text = " ".join(prompt)
    with Live(console=console, refresh_per_second=8):
        console.print(f"[bold cyan]You:[/bold cyan] {text}")
        console.print("[bold magenta]AI:[/bold magenta] (streaming stub)")


@app.command()
def index(
    include: List[str] = typer.Option(None, "--include", help="Glob patterns to include"),
    exclude: List[str] = typer.Option(None, "--exclude", help="Glob patterns to exclude"),
) -> None:
    """Build a lightweight TSV index of text files."""
    cfg = _load_config()
    idx = IndexSystem(cfg)
    stats = idx.build_index(Path.cwd(), include=include, exclude=exclude)
    console.print(f"Indexed {stats.indexed_files}/{stats.total_files} files -> .term-coder/index.tsv")


@app.command()
def run(command: List[str] = typer.Argument(..., help="Shell command to execute"), timeout: int = typer.Option(30, help="Timeout in seconds")) -> None:
    """Execute a shell command with timeout and show results."""
    _ = _load_config()
    runner = CommandRunner()
    result = runner.run_command(" ".join(command), timeout=timeout)
    console.rule("stdout")
    if result.stdout:
        console.print(result.stdout)
    console.rule("stderr")
    if result.stderr:
        console.print(result.stderr)
    console.print(f"[bold]Exit:[/bold] {result.exit_code}  [bold]Time:[/bold] {result.execution_time:.2f}s")


@app.command()
def search(
    query: List[str] = typer.Argument(..., help="Query string"),
    include: List[str] = typer.Option(None, "--include"),
    exclude: List[str] = typer.Option(None, "--exclude"),
    top: int = typer.Option(20, help="Max results"),
    semantic: bool = typer.Option(False, "--semantic", help="Use semantic search"),
    hybrid: bool = typer.Option(False, "--hybrid", help="Combine lexical and semantic"),
) -> None:
    """Search across repository.

    Default is lexical. With --semantic uses embedding search. With --hybrid combines both.
    """
    _ = _load_config()
    q = " ".join(query)
    cwd = Path.cwd()

    if hybrid:
        engine = HybridSearch(cwd)
        results = engine.search(q, include=include, exclude=exclude, top=top)
        for path, score in results:
            console.print(f"[bold]{path}[/bold]  score={score:.3f}")
        return

    if semantic:
        engine = SemanticSearch(cwd)
        results = engine.search(q, top_k=top, include=include, exclude=exclude)
        for path, score in results:
            console.print(f"[bold]{path}[/bold]  score={score:.3f}")
        return

    engine = LexicalSearch(cwd)
    hits = engine.search(q, include=include, exclude=exclude, limit=top)
    for h in hits:
        console.print(f"[bold]{h.file_path}:{h.line_number}[/bold]: {h.line_text}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
