from __future__ import annotations

import json
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
from .context import ContextEngine
from .llm import LLMOrchestrator
from .prompts import render_chat_prompt
from .agent import RepoAgent
from .editor import generate_edit_proposal, save_pending, load_pending, clear_pending
from .fixer import generate_fix
from .tester import run_tests
from .explain import parse_target, explain as explain_code
from .refactor import RefactorEngine
from .generator import generate as generate_file
from .gittools import GitIntegration
from .security import create_privacy_manager
from .audit import create_audit_logger
from .language_aware import LanguageAwareContextEngine
from .framework_commands import FrameworkCommandExtensions
from .advanced_terminal import start_advanced_terminal
from .errors import (
    get_error_handler, handle_error, with_error_handling,
    ErrorCategory, ErrorContext, TermCoderError, ErrorSuggestion,
    ConfigurationError, NetworkError, UserInputError, LLMAPIError,
    LSPError, GitError, FrameworkError, FileSystemError, EditError,
    SearchError, ExecutionError
)
import json
import sys
import os
import asyncio
from datetime import datetime
from .recovery import get_recovery_manager
from dotenv import load_dotenv

load_dotenv()


console = Console()
app = typer.Typer(
    add_completion=False, 
    help="""Term Coder - AI coding assistant that understands your repository

🚀 QUICK START:
  tc                          # Start interactive mode (recommended!)
  tc "debug for errors"       # Natural language commands
  tc "fix the login bug"      # AI understands what you want
  tc "explain main.py"        # Get code explanations
  
💬 INTERACTIVE MODE:
  Just run 'tc' with no arguments to start chatting naturally with your codebase.
  
📚 TRADITIONAL COMMANDS:
  Use 'tc --help' to see all available commands for power users.
"""
)

# Set up global error handler
error_handler = get_error_handler()
recovery_manager = get_recovery_manager()


def _load_config() -> Config:
    """Load configuration with error handling and recovery."""
    try:
        return Config.load()
    except FileNotFoundError as e:
        context = ErrorContext(command="config_load", user_input="load config")
        error = ConfigurationError(
            "Configuration file not found",
            context=context,
            suggestions=[
                ErrorSuggestion(
                    title="Initialize Configuration",
                    description="Run 'tc init' to create a default configuration file",
                    command="tc init",
                    priority=1
                )
            ]
        )
        
        # Try to recover by initializing config
        if recovery_manager.recover_configuration(error):
            try:
                return Config.load()
            except Exception:
                pass
        
        console.print("[yellow]Config not found. Run 'tc init' to set up.[/yellow]")
        raise typer.Exit(code=1)
    except Exception as e:
        context = ErrorContext(command="config_load")
        handle_error(e, context, auto_recover=True)
        raise typer.Exit(code=1)


def _get_privacy_and_audit():
    """Get privacy manager and audit logger instances."""
    config_dir = Path(".term-coder")
    privacy_manager = create_privacy_manager(config_dir)
    audit_logger = create_audit_logger(config_dir, privacy_manager)
    return privacy_manager, audit_logger


@app.command()
def init() -> None:
    """Initialize configuration at .term-coder/config.yaml"""
    try:
        from .branding import show_init_screen, show_progress_with_wit, show_completion_message, show_feature_highlight
        
        # Show awesome initialization screen
        show_init_screen(console)
        
        # Show progress with wit
        show_progress_with_wit(console, "loading", 1.5)
        
        # Actually initialize
        path = ensure_initialized()
        
        # Show completion
        show_completion_message(console, "loading", True)
        
        # Show a feature highlight
        show_feature_highlight(console)
        
        console.print(f"\n[bold green]🎉 Term-Coder is ready to assist you![/bold green]")
        console.print(f"[dim]Configuration saved to:[/dim] [cyan]{path}[/cyan]")
        console.print("[dim]Try: [/dim][cyan]tc \"debug for errors\"[/cyan] [dim]or just[/dim] [cyan]tc[/cyan] [dim]to start chatting![/dim]")
        
    except Exception as e:
        console.print(f"[red]Failed to initialize configuration: {e}[/red]")
        raise typer.Exit(code=1)


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
@with_error_handling(category=ErrorCategory.LLM_API, auto_recover=True)
def chat(
    prompt: List[str] = typer.Argument(None, help="Your prompt text (optional - leave empty for interactive mode)"),
    files: List[str] = typer.Option(None, "--files", help="Explicit files to include in context"),
    dir: str = typer.Option(None, "--dir", help="Directory to bias context selection"),
    model: str = typer.Option(None, "--model", help="Model key to use (e.g., openai:gpt)"),
    session: str = typer.Option("default", "--session", help="Chat session name for persistence"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Start interactive mode"),
) -> None:
    """Chat with repo-aware context and streaming. Use natural language!
    
    Examples:
      tc chat "Debug for errors"
      tc chat "Fix the authentication bug"  
      tc chat "Explain how the login system works"
      tc chat --interactive  # Start interactive mode
    """
    context = ErrorContext(command="chat", user_input=" ".join(prompt) if prompt else "")
    
    try:
        cfg = _load_config()
        
        # If no prompt provided or interactive flag, start interactive mode
        if not prompt or interactive:
            import asyncio
            from .interactive_terminal import start_interactive_mode
            
            console.print("[cyan]Starting interactive mode...[/cyan]")
            asyncio.run(start_interactive_mode(cfg))
            return
        
        text = " ".join(prompt)
        
        # Use natural language interface for processing
        from .natural_interface import NaturalLanguageInterface
        
        natural_interface = NaturalLanguageInterface(cfg, console)
        
        # Process with natural language understanding
        result = natural_interface.process_natural_input(text)
        
        if result.get("success"):
            action_result = result.get("result", {})
            action = action_result.get("action", "chat")
            
            # Display result based on action type
            if action == "chat":
                response = action_result.get("response", "")
                console.print(f"[bold magenta]AI:[/bold magenta] {response}")
            else:
                # For non-chat actions, show what was done
                message = action_result.get("message", "Action completed")
                console.print(f"[green]✅ {message}[/green]")
                
                # Show suggestions if available
                suggestions = action_result.get("suggestions", [])
                if suggestions:
                    console.print("\n[bold]💡 Suggestions:[/bold]")
                    for suggestion in suggestions:
                        console.print(f"  • {suggestion}")
        else:
            error_msg = result.get("error", "Unknown error")
            console.print(f"[red]❌ {error_msg}[/red]")
            raise typer.Exit(code=1)
            
    except Exception as e:
        if not handle_error(e, context):
            console.print(f"[red]Chat failed: {e}[/red]")
            raise typer.Exit(code=1)

    # If the prompt matches a known repo intent, handle first
    ra = RepoAgent()
    report = ra.handle_query(text)
    if report:
        console.rule(report.title)
        console.print(report.summary)
        if report.findings:
            console.print("\n".join(report.findings))
        return

    # Select context
    ctx_engine = ContextEngine(cfg)
    # If a directory is specified, include it as a glob and nudge context selection
    include = None
    if dir:
        include = [f"{dir.rstrip('/')}/**/*"]
    ctx = ctx_engine.select_context(files=files, query=text, budget_tokens=int(cfg.get("retrieval.max_tokens", 8000)))

    # Render prompt
    # Load session history and render prompt with it
    from .session import ChatSession

    chat_sess = ChatSession(session)
    chat_sess.load()
    rp = render_chat_prompt(text, ctx, history=chat_sess.history_pairs(limit_chars=4000))

    # Get privacy and audit components
    privacy_manager, audit_logger = _get_privacy_and_audit()
    
    # Choose model
    orchestrator = LLMOrchestrator(
        offline=bool(cfg.get("privacy.offline", False)),
        privacy_manager=privacy_manager,
        audit_logger=audit_logger
    )

    # Log chat interaction
    audit_logger.log_event(
        event_type="chat",
        action="start",
        details={"session": session, "prompt_length": len(text), "files_count": len(files) if files else 0}
    )

    from .progress import progress_context
    
    with progress_context(console=console) as progress:
        with progress.task("chat", "Generating response", total=None) as task:
            console.print(f"[bold cyan]You:[/bold cyan] {text}")
            console.print("[bold magenta]AI:[/bold magenta]")
            
            # Save user message
            chat_sess.append("user", text)
            
            # Stream assistant reply and capture
            full = []
            chunk_count = 0
            
            for chunk in orchestrator.stream(rp.user, model=model):
                s = str(chunk)
                full.append(s)
                console.print(s, end="", soft_wrap=True)
                
                chunk_count += 1
                if chunk_count % 10 == 0:  # Update progress every 10 chunks
                    task.update(1, f"Generating response ({chunk_count} chunks)")
            
            console.print()
            chat_sess.append("assistant", "".join(full))
            chat_sess.save()
            
            task.set_description(f"Response complete ({chunk_count} chunks)")


@app.command()
@with_error_handling(category=ErrorCategory.FILE_SYSTEM)
def index(
    include: List[str] = typer.Option(None, "--include", help="Glob patterns to include"),
    exclude: List[str] = typer.Option(None, "--exclude", help="Glob patterns to exclude"),
) -> None:
    """Build a lightweight TSV index of text files."""
    context = ErrorContext(command="index")
    
    try:
        from .progress import progress_context
        
        cfg = _load_config()
        idx = IndexSystem(cfg)
        
        with progress_context(console=console) as progress:
            with progress.task("index", "Building file index", total=None) as task:
                stats = idx.build_index(Path.cwd(), include=include, exclude=exclude)
                task.set_description(f"Indexed {stats.indexed_files} files")
        
        console.print(f"Indexed {stats.indexed_files}/{stats.total_files} files -> .term-coder/index.tsv")
    
    except Exception as e:
        index_error = TermCoderError(
            f"Failed to build search index: {e}",
            category=ErrorCategory.FILE_SYSTEM,
            context=context,
            suggestions=[
                ErrorSuggestion(
                    title="Check File Permissions",
                    description="Ensure you have read/write permissions in the repository",
                    priority=1
                ),
                ErrorSuggestion(
                    title="Check Disk Space",
                    description="Verify sufficient disk space is available",
                    priority=2
                ),
                ErrorSuggestion(
                    title="Verify Repository Structure",
                    description="Ensure you're in a valid repository directory",
                    priority=3
                )
            ]
        )
        
        if not handle_error(index_error, context):
            console.print(f"[red]Index build failed: {e}[/red]")
            raise typer.Exit(code=1)


@app.command()
@with_error_handling(category=ErrorCategory.EXECUTION)
def run(
    command: List[str] = typer.Argument(..., help="Shell command to execute"),
    timeout: int = typer.Option(30, help="Timeout in seconds"),
    cpu: int = typer.Option(None, "--cpu", help="CPU seconds limit"),
    mem: int = typer.Option(None, "--mem", help="Memory limit in MB"),
    no_network: bool = typer.Option(False, "--no-network", help="Disable network using unshare if available"),
) -> None:
    """Execute a shell command in a sandbox and show results."""
    context = ErrorContext(command="run", user_input=" ".join(command))
    
    try:
        _ = _load_config()
        privacy_manager, audit_logger = _get_privacy_and_audit()
        runner = CommandRunner(cpu_seconds=cpu, memory_mb=mem, no_network=no_network, audit_logger=audit_logger)
        
        result = runner.run_command(" ".join(command), timeout=timeout)
        
        console.rule("stdout")
        if result.stdout:
            console.print(result.stdout)
        console.rule("stderr")
        if result.stderr:
            console.print(result.stderr)
        console.print(f"[bold]Exit:[/bold] {result.exit_code}  [bold]Time:[/bold] {result.execution_time:.2f}s  [bold]CWD:[/bold] {result.snapshot.cwd}")
        
        # Log command execution failure if non-zero exit
        if result.exit_code != 0:
            audit_logger.log_event(
                event_type="command_execution",
                action="failed",
                details={
                    "command": " ".join(command),
                    "exit_code": result.exit_code,
                    "execution_time": result.execution_time
                }
            )
    
    except Exception as e:
        execution_error = TermCoderError(
            f"Command execution failed: {e}",
            category=ErrorCategory.EXECUTION,
            context=context,
            suggestions=[
                ErrorSuggestion(
                    title="Check Command Syntax",
                    description="Verify the command syntax is correct",
                    priority=1
                ),
                ErrorSuggestion(
                    title="Increase Timeout",
                    description="Try increasing the timeout if the command takes longer to execute",
                    priority=2
                ),
                ErrorSuggestion(
                    title="Check Resource Limits",
                    description="Verify CPU and memory limits are sufficient",
                    priority=3
                )
            ]
        )
        
        if not handle_error(execution_error, context):
            console.print(f"[red]Command execution failed: {e}[/red]")
            raise typer.Exit(code=1)


@app.command()
@with_error_handling(category=ErrorCategory.SEARCH)
def search(
    query: List[str] = typer.Argument(..., help="Query string"),
    include: List[str] = typer.Option(None, "--include"),
    exclude: List[str] = typer.Option(None, "--exclude"),
    types: List[str] = typer.Option(None, "--type", help="File extensions to include, e.g. --type py --type md"),
    top: int = typer.Option(20, help="Max results"),
    semantic: bool = typer.Option(False, "--semantic", help="Use semantic search"),
    hybrid: bool = typer.Option(False, "--hybrid", help="Combine lexical and semantic"),
    both: bool = typer.Option(False, "--both", help="Show both lexical and semantic lists"),
) -> None:
    """Search across repository.

    Default is lexical. With --semantic uses embedding search. With --hybrid combines both.
    """
    context = ErrorContext(command="search", user_input=" ".join(query))
    
    try:
        cfg = _load_config()
        q = " ".join(query)
        
        # Validate input
        if not q.strip():
            raise UserInputError(
                "Empty search query provided",
                context=context,
                suggestions=[
                    ErrorSuggestion(
                        title="Provide a search query",
                        description="Enter text to search for in your repository",
                        priority=1
                    )
                ]
            )
    
    except Exception as e:
        search_error = TermCoderError(
            f"Search initialization failed: {e}",
            category=ErrorCategory.SEARCH,
            context=context,
            suggestions=[
                ErrorSuggestion(
                    title="Check Query Syntax",
                    description="Verify your search query is valid",
                    priority=1
                ),
                ErrorSuggestion(
                    title="Try Lexical Search",
                    description="Use default lexical search if semantic search fails",
                    priority=2
                )
            ]
        )
        
        if not handle_error(search_error, context):
            console.print(f"[red]Search failed: {e}[/red]")
            raise typer.Exit(code=1)
        return
    cwd = Path.cwd()

    # Merge type filters into include globs
    if types:
        include = list(include or []) + [f"**/*.{t.lstrip('.')}" for t in types]

    # Respect offline mode: fall back to lexical-only
    offline = bool(cfg.get("privacy.offline", False))
    if offline and (semantic or hybrid or both):
        console.print("[yellow]Offline mode enabled; falling back to lexical search only.[/yellow]")
        semantic = False
        hybrid = False
        both = False

    if hybrid:
        engine = HybridSearch(cwd, alpha=float(cfg.get("retrieval.hybrid_weight", 0.7)), config=cfg)
        results = engine.search(q, include=include, exclude=exclude, top=top)
        for path, score in results:
            console.print(f"[bold]{path}[/bold]  score={score:.3f}")
        return

    if semantic:
        from .semantic import create_embedding_model_from_config

        model_impl = create_embedding_model_from_config(cfg)
        engine = SemanticSearch(cwd, model=model_impl)
        results = engine.search(q, top_k=top, include=include, exclude=exclude)
        for path, score in results:
            console.print(f"[bold]{path}[/bold]  score={score:.3f}")
        return

    engine = LexicalSearch(cwd)

    if both:
        console.rule("Lexical (by file)")
        ranked = engine.rank_files(q, include=include, exclude=exclude, top=top)
        for path, score in ranked:
            console.print(f"[bold]{path}[/bold]  score={score:.3f}")

        console.rule("Semantic")
        from .semantic import create_embedding_model_from_config

        model_impl = create_embedding_model_from_config(cfg)
        sengine = SemanticSearch(cwd, model=model_impl)
        sresults = sengine.search(q, top_k=top, include=include, exclude=exclude)
        for path, score in sresults:
            console.print(f"[bold]{path}[/bold]  score={score:.3f}")
        return

    # Default: lexical line hits
    hits = engine.search(q, include=include, exclude=exclude, limit=top)
    for h in hits:
        console.print(f"[bold]{h.file_path}:{h.line_number}[/bold]: {h.line_text}")


@app.command()
@with_error_handling(category=ErrorCategory.EDIT)
def edit(
    instruction: List[str] = typer.Argument(..., help="High-level edit instruction"),
    files: List[str] = typer.Option(..., "--files", help="Target files to edit", prompt=True),
    no_llm: bool = typer.Option(False, "--no-llm", help="Disable LLM and use deterministic transforms only"),
) -> None:
    """Generate an edit proposal (diff) without applying it."""
    context = ErrorContext(command="edit", user_input=" ".join(instruction))
    
    try:
        cfg = _load_config()
        instr = " ".join(instruction)
        
        # Validate input
        if not instr.strip():
            raise UserInputError(
                "Empty edit instruction provided",
                context=context,
                suggestions=[
                    ErrorSuggestion(
                        title="Provide an instruction",
                        description="Enter a clear description of what changes to make",
                        priority=1
                    )
                ]
            )
        
        if not files:
            raise UserInputError(
                "No files specified for editing",
                context=context,
                suggestions=[
                    ErrorSuggestion(
                        title="Specify target files",
                        description="Use --files to specify which files to edit",
                        priority=1
                    )
                ]
            )
        
        pe = generate_edit_proposal(instr, files, cfg, use_llm=(not no_llm))
        if not pe:
            console.print("[red]No changes could be generated from the instruction.[/red]")
            raise typer.Exit(code=1)
        
        save_pending(pe)
        console.rule("Proposed Diff")
        console.print(pe.proposal.diff or "<no diff>")
        console.rule("Summary")
        console.print(f"Files: {len(pe.proposal.affected_files)}  +{pe.proposal.estimated_impact.lines_added} -{pe.proposal.estimated_impact.lines_removed}  Safety: {pe.proposal.safety_score:.2f}")
    
    except Exception as e:
        edit_error = TermCoderError(
            f"Edit proposal generation failed: {e}",
            category=ErrorCategory.EDIT,
            context=context,
            suggestions=[
                ErrorSuggestion(
                    title="Check File Permissions",
                    description="Ensure target files are readable and writable",
                    priority=1
                ),
                ErrorSuggestion(
                    title="Simplify Instruction",
                    description="Try breaking down complex edits into smaller steps",
                    priority=2
                ),
                ErrorSuggestion(
                    title="Use --no-llm",
                    description="Try using deterministic transforms only",
                    priority=3
                )
            ]
        )
        
        if not handle_error(edit_error, context):
            console.print(f"[red]Edit failed: {e}[/red]")
            raise typer.Exit(code=1)


@app.command()
def diff() -> None:
    """Show the currently pending edit diff."""
    pe = load_pending()
    if not pe:
        console.print("[yellow]No pending edit found.[/yellow]")
        return
    console.rule("Pending Diff")
    console.print(pe.proposal.diff or "<no diff>")


@app.command()
def apply(
    pick: List[str] = typer.Option(None, "--pick", help="Specific files to apply; default all affected"),
    unsafe: bool = typer.Option(False, "--unsafe", help="Allow creating new files"),
) -> None:
    """Apply the pending edit to the working tree with backup and formatters."""
    from .patcher import PatchSystem

    pe = load_pending()
    if not pe:
        console.print("[yellow]No pending edit found.[/yellow]")
        return
    ps = PatchSystem(Path.cwd())
    # If pick is provided, filter proposal's affected files
    if pick:
        pe.proposal.affected_files = [p for p in pe.proposal.affected_files if p in set(pick)]
        if pe.proposal.new_contents:
            pe.proposal.new_contents = {k: v for k, v in pe.proposal.new_contents.items() if k in set(pick)}
    ok, backup_id = ps.apply_patch(pe.proposal, unsafe=unsafe)
    if ok:
        console.print(f"[green]Applied.[/green] Backup: {backup_id}")
        clear_pending()
    else:
        console.print("[red]Apply failed. Use 'tc diff' to inspect or 'tc apply --unsafe' if needed.[/red]")


@app.command()
def fix(with_last_run: bool = typer.Option(True, "--with-last-run", help="Use last run logs for analysis")) -> None:
    """Analyze last run logs and propose a fix (command or edit)."""
    cfg = _load_config()
    suggestion = generate_fix(cfg, use_last_run=with_last_run)
    if suggestion.kind == "none":
        console.print("[yellow]No specific fix suggestion available.")
        return
    console.rule("Fix Suggestion")
    console.print(suggestion.rationale)
    if suggestion.kind == "command" and suggestion.command:
        console.print(f"[bold]Suggested command:[/bold] {suggestion.command}")
    if suggestion.kind == "edit" and suggestion.pending_edit:
        save_pending(suggestion.pending_edit)
        console.rule("Proposed Diff")
        console.print(suggestion.pending_edit.proposal.diff or "<no diff>")
        console.print("Run 'tc apply' to apply this fix.")


@app.command()
def test(
    cmd: Optional[str] = typer.Option(None, "--cmd", help="Override test command"),
    framework: Optional[str] = typer.Option(None, "--framework", help="pytest|jest|gotest"),
) -> None:
    """Run tests with basic parsing and failure extraction."""
    cfg = _load_config()
    report = run_tests(command=cmd, framework=framework, cfg=cfg)
    console.rule("Test Report")
    console.print(f"Framework: {report.framework}")
    console.print(f"Command: {report.command}")
    console.print(f"Passed: {report.passed}  Failed: {report.failed}  Skipped: {report.skipped}")
    if report.failures:
        console.rule("Failures")
        for f in report.failures[:20]:
            console.print(f"- {f.test_id}: {f.message}")


@app.command()
def explain(
    target: str = typer.Argument(..., help="Path[, :start:end] or path#symbol (e.g., foo.py:10:50 or foo.py#MyClass)"),
    model: Optional[str] = typer.Option(None, "--model"),
) -> None:
    """Explain a file, range, or symbol with syntax-aware slicing."""
    cfg = _load_config()
    spec = parse_target(target)
    text = explain_code(spec, model=model, offline=bool(cfg.get("privacy.offline", False)))
    console.rule(f"Explain: {target}")
    console.print(text)


@app.command()
def refactor_rename(
    old: str = typer.Argument(..., help="Old symbol name"),
    new: str = typer.Argument(..., help="New symbol name"),
    include: List[str] = typer.Option(["**/*.py"], "--include"),
    exclude: List[str] = typer.Option(None, "--exclude"),
    apply: bool = typer.Option(False, "--apply", help="Apply changes after preview"),
) -> None:
    """Rename a Python symbol across files (token-aware) with safety checks and test validation."""
    engine = RefactorEngine(Path.cwd())
    plan = engine.rename_symbol_python(old, new, include=include, exclude=exclude)
    console.rule("Refactor Preview (rename)")
    if not plan.proposal or not plan.proposal.diff:
        console.print("[yellow]No occurrences found.")
        return
    console.print(plan.proposal.diff)
    console.rule("Stats")
    console.print(f"Files changed: {plan.safety.files_changed}  Replacements: {plan.safety.total_replacements}")
    if not apply:
        console.print("Run with --apply to apply and validate with tests.")
        return
    ok, backup_id, test_result = engine.apply_and_validate(plan, run_tests=True)
    if ok:
        console.print(f"[green]Refactor applied successfully. Backup: {backup_id}. Tests passed: {test_result}")
    else:
        console.print(f"[red]Refactor failed or tests failed. Rolled back using backup: {backup_id}. Result: {test_result}")


@app.command()
def generate(
    framework: str = typer.Argument(..., help="Framework: python|react|node"),
    kind: str = typer.Argument(..., help="Type to generate: module|component|script"),
    name: str = typer.Argument(..., help="Name, e.g. UserProfile"),
    out_dir: Optional[Path] = typer.Option(None, "--out-dir", help="Output directory"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing file"),
) -> None:
    """Scaffold code from templates for modules, components, and scripts."""
    try:
        result = generate_file(framework, kind, name, out_dir=out_dir, force=force)
    except Exception as e:
        console.print(f"[red]Generation failed:[/red] {e}")
        raise typer.Exit(code=1)
    console.print(f"[green]Generated:[/green] {result.path}")
    if result.validated:
        console.print(f"[green]{result.message}[/green]")
    else:
        console.print(f"[yellow]{result.message}[/yellow]")


@app.command()
def review(range: Optional[str] = typer.Option(None, "--range", help="Git range to review, e.g., HEAD~3..HEAD")) -> None:
    """Review staged changes or a provided git range using AI (if available)."""
    try:
        gi = GitIntegration(Path.cwd())
    except Exception as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)
    diff = gi.diff_range(range, context_lines=3) if range else gi.diff_staged(context_lines=3)
    text = gi.review_changes(diff)
    console.rule("Code Review")
    console.print(text)


@app.command()
def commit(message: Optional[str] = typer.Option(None, "-m", "--message", help="Commit message; if omitted, AI will generate")) -> None:
    """Create a commit with an AI-generated message if not provided."""
    try:
        gi = GitIntegration(Path.cwd())
    except Exception as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)
    diff = gi.diff_staged(context_lines=3)
    if not message:
        message = gi.generate_commit_message(diff)
    sha = gi.commit(message)
    console.print(f"[green]Committed[/green] {sha[:8]} - {message}")


@app.command()
def pr(
    range: Optional[str] = typer.Option(None, "--range", help="Git range, e.g., main..HEAD"),
    model: Optional[str] = typer.Option(None, "--model"),
) -> None:
    """Draft a PR description from staged changes or a provided git range."""
    try:
        gi = GitIntegration(Path.cwd())
    except Exception as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)
    diff = gi.diff_range(range, context_lines=3) if range else gi.diff_staged(context_lines=3)
    desc = gi.generate_pr_description(diff, model=model)
    console.rule("PR Description")
    console.print(desc)


@app.command()
def privacy(
    setting: Optional[str] = typer.Argument(None, help="Privacy setting to view/modify"),
    value: Optional[str] = typer.Argument(None, help="New value for the setting"),
) -> None:
    """Manage privacy settings and view current configuration."""
    privacy_manager, audit_logger = _get_privacy_and_audit()
    
    if setting is None:
        # Show all privacy settings
        console.rule("Privacy Settings")
        console.print(f"Redact secrets: {privacy_manager.should_redact_secrets()}")
        console.print(f"Log prompts: {privacy_manager.should_log_prompts()}")
        console.print(f"Offline mode: {privacy_manager.is_offline_mode()}")
        console.print(f"Audit level: {privacy_manager.get_audit_level()}")
        
        console.rule("Data Consent")
        console.print(f"Data collection: {privacy_manager.can_collect_data()}")
        console.print(f"Analytics: {privacy_manager.can_send_analytics()}")
        console.print(f"Model training: {privacy_manager.can_use_for_training()}")
        console.print(f"Error reporting: {privacy_manager.can_report_errors()}")
        return
    
    if value is None:
        # Show specific setting
        if hasattr(privacy_manager, f"get_{setting}"):
            current = getattr(privacy_manager, f"get_{setting}")()
            console.print(f"{setting}: {current}")
        else:
            console.print(f"[red]Unknown privacy setting: {setting}[/red]")
        return
    
    # Update setting
    try:
        if setting in ["redact_secrets", "log_prompts", "offline_mode", "audit_level"]:
            old_value = privacy_manager.privacy_config.get(setting)
            privacy_manager.update_privacy_setting(setting, value.lower() == "true" if value.lower() in ["true", "false"] else value)
            audit_logger.log_privacy_change(setting, value)
            console.print(f"[green]Updated {setting} to {value}[/green]")
        elif setting in ["data_collection", "analytics", "model_training", "error_reporting"]:
            privacy_manager.update_consent(setting, value.lower() == "true")
            audit_logger.log_privacy_change(f"consent_{setting}", value)
            console.print(f"[green]Updated consent for {setting} to {value}[/green]")
        else:
            console.print(f"[red]Unknown privacy setting: {setting}[/red]")
    except Exception as e:
        console.print(f"[red]Failed to update setting: {e}[/red]")


@app.command()
def scan_secrets(
    path: Optional[str] = typer.Argument(None, help="Path to scan (default: current directory)"),
    include: List[str] = typer.Option(None, "--include", help="Glob patterns to include"),
    exclude: List[str] = typer.Option(None, "--exclude", help="Glob patterns to exclude"),
    fix: bool = typer.Option(False, "--fix", help="Automatically redact found secrets"),
) -> None:
    """Scan for secrets in files and optionally redact them."""
    from .security import SecretDetector
    from .utils import iter_source_files
    
    privacy_manager, audit_logger = _get_privacy_and_audit()
    detector = SecretDetector()
    
    scan_path = Path(path) if path else Path.cwd()
    if not scan_path.exists():
        console.print(f"[red]Path does not exist: {scan_path}[/red]")
        raise typer.Exit(code=1)
    
    console.rule("Secret Scan")
    total_files = 0
    files_with_secrets = 0
    total_secrets = 0
    
    for file_path in iter_source_files(scan_path, include, exclude):
        if not file_path.is_file():
            continue
            
        total_files += 1
        try:
            content = file_path.read_text(encoding='utf-8')
            matches = detector.detect_secrets(content)
            
            if matches:
                files_with_secrets += 1
                total_secrets += len(matches)
                
                console.print(f"\n[bold red]{file_path}[/bold red]")
                for match in matches:
                    console.print(f"  Line {content[:match.start].count(chr(10)) + 1}: {match.pattern_name} ({match.severity})")
                    console.print(f"    {match.text} -> {match.redacted_text}")
                
                # Log security event
                audit_logger.log_security_event(
                    "secrets_found_in_file",
                    "medium",
                    {
                        "file": str(file_path),
                        "secret_count": len(matches),
                        "patterns": [m.pattern_name for m in matches]
                    }
                )
                
                # Optionally fix
                if fix:
                    redacted_content, _ = detector.redact_secrets(content)
                    file_path.write_text(redacted_content, encoding='utf-8')
                    console.print(f"    [green]Redacted secrets in {file_path}[/green]")
                    audit_logger.log_file_access(str(file_path), "redact_secrets")
        
        except Exception as e:
            console.print(f"[yellow]Could not scan {file_path}: {e}[/yellow]")
    
    console.rule("Scan Summary")
    console.print(f"Files scanned: {total_files}")
    console.print(f"Files with secrets: {files_with_secrets}")
    console.print(f"Total secrets found: {total_secrets}")
    
    if total_secrets > 0 and not fix:
        console.print("\n[yellow]Run with --fix to automatically redact secrets[/yellow]")


@app.command()
def audit(
    days: int = typer.Option(7, "--days", help="Number of days to include in summary"),
    export: Optional[str] = typer.Option(None, "--export", help="Export audit log to file"),
) -> None:
    """View audit log summary and export logs."""
    privacy_manager, audit_logger = _get_privacy_and_audit()
    
    if export:
        # Export audit logs
        export_path = Path(export)
        try:
            summary = audit_logger.get_audit_summary(days=days)
            export_path.write_text(json.dumps(summary, indent=2))
            console.print(f"[green]Exported audit summary to {export_path}[/green]")
            audit_logger.log_event("audit", "export", resource=str(export_path))
        except Exception as e:
            console.print(f"[red]Failed to export audit log: {e}[/red]")
        return
    
    # Show audit summary
    summary = audit_logger.get_audit_summary(days=days)
    
    console.rule("Audit Summary")
    console.print(f"Period: {summary['date_range']}")
    console.print(f"Total events: {summary['total_events']}")
    console.print(f"Success rate: {summary['success_rate']:.1%}")
    console.print(f"Errors: {summary['error_count']}")
    console.print(f"Security events: {summary['security_events']}")
    
    if summary['event_types']:
        console.rule("Event Types")
        for event_type, count in summary['event_types'].items():
            console.print(f"{event_type}: {count}")


@app.command()
def cleanup(
    retention_days: int = typer.Option(90, "--retention-days", help="Keep logs newer than this many days"),
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt"),
) -> None:
    """Clean up old audit logs and session data."""
    privacy_manager, audit_logger = _get_privacy_and_audit()
    
    if not confirm:
        response = typer.confirm(f"Delete audit logs older than {retention_days} days?")
        if not response:
            console.print("Cleanup cancelled.")
            return
    
    try:
        audit_logger.cleanup_old_logs(retention_days)
        console.print(f"[green]Cleaned up audit logs older than {retention_days} days[/green]")
    except Exception as e:
        console.print(f"[red]Cleanup failed: {e}[/red]")


@app.command()
def tui() -> None:
    """Launch the Text User Interface (TUI) mode."""
    try:
        from .tui import run_tui
        cfg = _load_config()
        console.print("[cyan]Starting TUI mode...[/cyan]")
        console.print("[dim]Press F1 for help, Esc to exit[/dim]")
        run_tui(cfg)
    except ImportError:
        console.print("[red]TUI mode requires additional dependencies. Install with: pip install term-coder[tui][/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]TUI failed to start: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def lsp(
    action: str = typer.Argument(..., help="Action: start|stop|status|diagnostics"),
    file: Optional[str] = typer.Argument(None, help="File path for diagnostics"),
) -> None:
    """Manage Language Server Protocol integration."""
    import asyncio
    
    cfg = _load_config()
    root_path = Path.cwd()
    
    async def run_lsp_action():
        from .lsp import LSPManager
        
        manager = LSPManager(cfg, root_path)
        
        if action == "status":
            console.rule("LSP Status")
            for lang, config in manager.server_configs.items():
                status = "Available" if lang in manager.clients else "Not started"
                console.print(f"{lang}: {status} (command: {' '.join(config['command'])})")
        
        elif action == "diagnostics" and file:
            file_path = Path(file)
            if not file_path.exists():
                console.print(f"[red]File not found: {file}[/red]")
                return
            
            diagnostics = await manager.get_diagnostics(file_path)
            
            console.rule(f"Diagnostics for {file}")
            if not diagnostics:
                console.print("[green]No diagnostics found[/green]")
            else:
                for diag in diagnostics:
                    severity_map = {1: "ERROR", 2: "WARNING", 3: "INFO", 4: "HINT"}
                    severity = severity_map.get(diag.severity, "UNKNOWN")
                    
                    line = diag.range.start.line + 1
                    col = diag.range.start.character + 1
                    
                    color = {"ERROR": "red", "WARNING": "yellow", "INFO": "blue", "HINT": "dim"}.get(severity, "white")
                    console.print(f"[{color}]{severity}[/{color}] Line {line}:{col} - {diag.message}")
                    if diag.source:
                        console.print(f"  Source: {diag.source}")
        
        elif action == "start":
            console.print("[cyan]Starting LSP servers...[/cyan]")
            # LSP servers start automatically when needed
            console.print("[green]LSP integration ready[/green]")
        
        elif action == "stop":
            console.print("[cyan]Stopping LSP servers...[/cyan]")
            await manager.shutdown_all()
            console.print("[green]LSP servers stopped[/green]")
        
        else:
            console.print(f"[red]Unknown action: {action}[/red]")
            console.print("Available actions: start, stop, status, diagnostics")
    
    asyncio.run(run_lsp_action())


@app.command()
def symbols(
    file: str = typer.Argument(..., help="File to analyze for symbols"),
    type: Optional[str] = typer.Option(None, "--type", help="Filter by symbol type (function, class, variable)"),
) -> None:
    """Extract and display symbols from a file using tree-sitter."""
    cfg = _load_config()
    file_path = Path(file)
    
    if not file_path.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(code=1)
    
    from .tree_sitter import TreeSitterParser
    
    parser = TreeSitterParser(cfg)
    syntax_tree = parser.parse_file(file_path)
    
    if not syntax_tree:
        console.print(f"[yellow]Could not parse file: {file}[/yellow]")
        return
    
    symbols = parser.extract_symbols(syntax_tree)
    
    if type:
        symbols = [s for s in symbols if s.type == type]
    
    console.rule(f"Symbols in {file}")
    
    if not symbols:
        console.print("[yellow]No symbols found[/yellow]")
        return
    
    # Group symbols by type
    by_type = {}
    for symbol in symbols:
        if symbol.type not in by_type:
            by_type[symbol.type] = []
        by_type[symbol.type].append(symbol)
    
    for symbol_type, symbol_list in by_type.items():
        console.print(f"\n[bold cyan]{symbol_type.title()}s:[/bold cyan]")
        for symbol in symbol_list:
            line = symbol.definition_node.start_line + 1
            console.print(f"  {symbol.name} (line {line})")
            if symbol.scope:
                scope_name = parser._extract_symbol_name(symbol.scope)
                if scope_name:
                    console.print(f"    in {symbol.scope.type}: {scope_name}")


@app.command()
def frameworks() -> None:
    """Detect and display information about frameworks used in the project."""
    cfg = _load_config()
    root_path = Path.cwd()
    
    extensions = FrameworkCommandExtensions(cfg, root_path)
    detected = extensions.get_detected_frameworks()
    
    console.rule("Detected Frameworks")
    
    if not detected:
        console.print("[yellow]No frameworks detected in this project[/yellow]")
        return
    
    for name, info in detected.items():
        console.print(f"\n[bold green]{info.name}[/bold green]")
        if info.version:
            console.print(f"  Version: {info.version}")
        
        if info.config_files:
            console.print("  Config files:")
            for config_file in info.config_files:
                console.print(f"    - {config_file}")
        
        if info.entry_points:
            console.print("  Entry points:")
            for entry_point in info.entry_points:
                console.print(f"    - {entry_point}")
        
        # Show available commands
        commands = extensions.get_framework_commands(name)
        if commands:
            console.print("  Available commands:")
            for cmd_name, cmd in commands.items():
                console.print(f"    - {cmd_name}: {cmd.description}")


@app.command()
def framework_run(
    framework: str = typer.Argument(..., help="Framework name (e.g., django, react, rust_web)"),
    command: str = typer.Argument(..., help="Command to run (e.g., runserver, start, build)"),
    args: List[str] = typer.Argument(None, help="Additional arguments for the command"),
) -> None:
    """Run a framework-specific command."""
    cfg = _load_config()
    root_path = Path.cwd()
    
    extensions = FrameworkCommandExtensions(cfg, root_path)
    
    try:
        console.print(f"[cyan]Running {framework} {command}...[/cyan]")
        result = extensions.execute_framework_command(framework, command, args or [])
        
        console.rule("stdout")
        if result.stdout:
            console.print(result.stdout)
        
        console.rule("stderr")
        if result.stderr:
            console.print(result.stderr)
        
        if result.returncode == 0:
            console.print(f"[green]Command completed successfully[/green]")
        else:
            console.print(f"[red]Command failed with exit code {result.returncode}[/red]")
            raise typer.Exit(code=result.returncode)
    
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def scaffold(
    framework: str = typer.Argument(..., help="Framework (django, react, fastapi, etc.)"),
    template: str = typer.Argument(..., help="Template type (model, component, router, etc.)"),
    name: str = typer.Argument(..., help="Name for the generated code"),
    output: Optional[str] = typer.Option(None, "--output", help="Output file path"),
) -> None:
    """Generate framework-specific code templates."""
    cfg = _load_config()
    root_path = Path.cwd()
    
    extensions = FrameworkCommandExtensions(cfg, root_path)
    
    code = extensions.generate_framework_specific_code(framework, template, name)
    
    if not code:
        console.print(f"[red]No template found for {framework} {template}[/red]")
        console.print("Available templates depend on the detected frameworks.")
        raise typer.Exit(code=1)
    
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(code)
        console.print(f"[green]Generated {framework} {template} at {output_path}[/green]")
    else:
        console.rule(f"{framework.title()} {template.title()}: {name}")
        console.print(code)


def main() -> None:
    app()


if __name__ == "__main__":
    main()


@app.command()
@with_error_handling(category=ErrorCategory.SYSTEM)
def diagnostics() -> None:
    """Run comprehensive system diagnostics and error reporting."""
    context = ErrorContext(command="diagnostics")
    
    try:
        from .recovery import ComponentRecovery
        
        console.print("[bold cyan]Running System Diagnostics...[/bold cyan]")
        
        # Initialize recovery system
        recovery = ComponentRecovery()
        
        # Run diagnostics
        diagnostics_result = recovery.run_diagnostics()
        
        # Display results
        console.print("\n[bold green]System Information:[/bold green]")
        system_info = diagnostics_result.get("system_info", {})
        for key, value in system_info.items():
            console.print(f"  {key}: {value}")
        
        console.print("\n[bold green]Health Status:[/bold green]")
        health_status = diagnostics_result.get("health_status", {})
        for component, status in health_status.items():
            status_color = "green" if status else "red"
            status_text = "✓" if status else "✗"
            console.print(f"  {component}: [{status_color}]{status_text}[/{status_color}]")
        
        console.print("\n[bold green]Dependencies:[/bold green]")
        dependencies = diagnostics_result.get("dependencies", {})
        for dep, info in dependencies.items():
            if isinstance(info, dict):
                available = info.get("available", False)
                version = info.get("version", "unknown")
                status_color = "green" if available else "red"
                status_text = "✓" if available else "✗"
                console.print(f"  {dep}: [{status_color}]{status_text}[/{status_color}] (v{version})")
            else:
                status_color = "green" if info else "red"
                status_text = "✓" if info else "✗"
                console.print(f"  {dep}: [{status_color}]{status_text}[/{status_color}]")
        
        # Get error handler statistics
        error_handler = get_error_handler()
        error_stats = error_handler.get_error_statistics()
        
        if error_stats.get("total_errors", 0) > 0:
            console.print("\n[bold yellow]Error Statistics:[/bold yellow]")
            console.print(f"  Total errors: {error_stats['total_errors']}")
            console.print(f"  Recent errors (last hour): {error_stats.get('recent_errors', 0)}")
            
            if error_stats.get("by_category"):
                console.print("  By category:")
                for category, count in error_stats["by_category"].items():
                    console.print(f"    {category}: {count}")
            
            if error_stats.get("by_severity"):
                console.print("  By severity:")
                for severity, count in error_stats["by_severity"].items():
                    console.print(f"    {severity}: {count}")
        else:
            console.print("\n[bold green]No errors recorded[/bold green]")
        
        # Overall health assessment
        overall_health = diagnostics_result.get("overall_health", True)
        if overall_health:
            console.print("\n[bold green]✓ System appears healthy[/bold green]")
        else:
            console.print("\n[bold red]⚠ System issues detected[/bold red]")
            console.print("Run individual commands to see specific error details.")
    
    except Exception as e:
        diagnostic_error = TermCoderError(
            f"Diagnostics failed: {e}",
            category=ErrorCategory.SYSTEM,
            context=context,
            suggestions=[
                ErrorSuggestion(
                    title="Check System Resources",
                    description="Ensure sufficient memory and disk space",
                    priority=1
                ),
                ErrorSuggestion(
                    title="Restart Application",
                    description="Try restarting term-coder if issues persist",
                    priority=2
                )
            ]
        )
        
        if not handle_error(diagnostic_error, context):
            console.print(f"[red]Diagnostics failed: {e}[/red]")
            raise typer.Exit(code=1)


@app.command()
@with_error_handling(category=ErrorCategory.SYSTEM)
def interactive() -> None:
    """Start interactive natural language mode.
    
    Talk to term-coder naturally:
    - "Debug for errors"
    - "Fix the authentication bug"
    - "Explain how the login system works"
    - "Add error handling to main.py"
    """
    try:
        cfg = _load_config()
        import asyncio
        from .interactive_terminal import start_interactive_mode
        
        console.print("[cyan]🚀 Starting Term-Coder Interactive Mode...[/cyan]")
        console.print("[dim]Talk naturally - I'll understand what you want to do![/dim]")
        console.print()
        
        asyncio.run(start_interactive_mode(cfg))
        
    except Exception as e:
        context = ErrorContext(command="interactive")
        if not handle_error(e, context):
            console.print(f"[red]Interactive mode failed: {e}[/red]")
            raise typer.Exit(code=1)


@app.command()
@with_error_handling(category=ErrorCategory.SYSTEM)
def export_errors(
    output_file: str = typer.Option("error_report.json", "--output", "-o", help="Output file path")
) -> None:
    """Export error report for debugging and support."""
    context = ErrorContext(command="export_errors")
    
    try:
        error_handler = get_error_handler()
        output_path = Path(output_file)
        
        # Generate comprehensive error report
        report = {
            "timestamp": datetime.now().isoformat(),
            "system_info": {
                "platform": sys.platform,
                "python_version": sys.version,
                "working_directory": str(Path.cwd()),
                "environment": dict(os.environ)
            },
            "statistics": error_handler.get_error_statistics(),
            "errors": [error.to_dict() for error in error_handler.error_history[-100:]]  # Last 100 errors
        }
        
        # Add diagnostics if available
        try:
            from .recovery import ComponentRecovery
            recovery = ComponentRecovery()
            report["diagnostics"] = recovery.run_diagnostics()
        except Exception:
            pass
        
        # Write report
        output_path.write_text(json.dumps(report, indent=2))
        
        console.print(f"[green]Error report exported to: {output_path}[/green]")
        console.print(f"Report contains {len(report['errors'])} error entries")
    
    except Exception as e:
        export_error = TermCoderError(
            f"Failed to export error report: {e}",
            category=ErrorCategory.SYSTEM,
            context=context,
            suggestions=[
                ErrorSuggestion(
                    title="Check Output Path",
                    description="Ensure the output directory exists and is writable",
                    priority=1
                ),
                ErrorSuggestion(
                    title="Use Different Output File",
                    description="Try a different output file path",
                    priority=2
                )
            ]
        )
        
        if not handle_error(export_error, context):
            console.print(f"[red]Export failed: {e}[/red]")
            raise typer.Exit(code=1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show version information"),
    help: bool = typer.Option(False, "--help", help="Show help information"),
) -> None:
    """Term-Coder: AI coding assistant that understands your repository.
    
    🚀 QUICK START:
      tc                          # Start interactive mode (recommended!)
      tc "debug for errors"       # Natural language commands
      tc "fix the login bug"      # AI understands what you want
      tc "explain main.py"        # Get code explanations
    
    💬 NATURAL LANGUAGE:
      Just tell term-coder what you want to do in plain English!
      
    Examples:
      • "Debug for errors"
      • "Fix the authentication bug"
      • "Explain how the login system works"
      • "Add error handling to main.py"
      • "Search for database connections"
      • "Review my recent changes"
      • "Generate tests for the user service"
    """
    
    if version:
        console.print("term-coder version 1.0.0")
        return
    
    if help or ctx.invoked_subcommand is not None:
        return
    
    # No subcommand provided - check if there are arguments that look like natural language
    if ctx.params.get('args'):
        # User provided arguments - treat as natural language command
        user_input = " ".join(ctx.params['args'])
        
        try:
            cfg = _load_config()
            from .natural_interface import NaturalLanguageInterface
            natural_interface = NaturalLanguageInterface(cfg, console)
            result = natural_interface.process_natural_input(user_input)
            
            if result.get("success"):
                action_result = result.get("result", {})
                action = action_result.get("action", "chat")
                
                if action == "chat":
                    response = action_result.get("response", "")
                    console.print(f"[bold magenta]🤖 AI:[/bold magenta] {response}")
                else:
                    message = action_result.get("message", "Action completed")
                    console.print(f"[green]✅ {message}[/green]")
                    
                    suggestions = action_result.get("suggestions", [])
                    if suggestions:
                        console.print("\n[bold]💡 Suggestions:[/bold]")
                        for suggestion in suggestions:
                            console.print(f"  • {suggestion}")
            else:
                error_msg = result.get("error", "Unknown error")
                console.print(f"[red]❌ {error_msg}[/red]")
                raise typer.Exit(code=1)
                
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            console.print("[dim]Try 'tc --help' for available commands[/dim]")
            raise typer.Exit(code=1)
    else:
        # No arguments - start interactive mode
        try:
            cfg = _load_config()
            import asyncio
            from .interactive_terminal import start_interactive_mode
            
            console.print("[cyan]🚀 Welcome to Term-Coder![/cyan]")
            console.print("[dim]Starting interactive mode... Talk naturally about your code![/dim]")
            console.print()
            
            asyncio.run(start_interactive_mode(cfg))
            
        except Exception as e:
            console.print(f"[red]Failed to start interactive mode: {e}[/red]")
            console.print("[dim]Try 'tc init' first to set up configuration[/dim]")
            raise typer.Exit(code=1)


# Add a way to capture arguments for natural language processing
@app.command(hidden=True)
def _natural_language_fallback(*args):
    """Hidden command to handle natural language input."""
    pass


@app.command()
@with_error_handling(category=ErrorCategory.SYSTEM)
def advanced(
    root: Optional[str] = typer.Option(None, "--root", "-r", help="Project root directory")
) -> None:
    """Start advanced terminal with Claude Code-style capabilities.
    
    Features:
    - Proactive file editing and suggestions
    - Advanced ripgrep-based search with context
    - Interactive project exploration
    - Natural language command processing
    - Session management and history
    """
    try:
        cfg = _load_config()
        project_root = Path(root) if root else Path.cwd()
        
        if not project_root.exists():
            console.print(f"[red]Root directory does not exist: {project_root}[/red]")
            raise typer.Exit(code=1)
        
        console.print("[cyan]🚀 Starting Advanced Terminal Mode...[/cyan]")
        console.print("[dim]Claude Code-style proactive development interface[/dim]")
        console.print()
        
        asyncio.run(start_advanced_terminal(cfg, project_root))
        
    except Exception as e:
        context = ErrorContext(command="advanced")
        if not handle_error(e, context):
            console.print(f"[red]Advanced terminal failed: {e}[/red]")
            raise typer.Exit(code=1)


if __name__ == "__main__":
    app()