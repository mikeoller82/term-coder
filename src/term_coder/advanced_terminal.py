"""
Advanced Terminal Interface for tc - Claude Code style capabilities
Provides proactive editing, intelligent file search, and enhanced REPL experience.
"""

from __future__ import annotations

import asyncio
import sys
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.live import Live
from rich.spinner import Spinner
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.columns import Columns
from rich.tree import Tree
from rich.filesize import decimal

from .config import Config
from .search import LexicalSearch, HybridSearch
from .editor import generate_edit_proposal
from .context import ContextEngine
from .utils import iter_source_files
from .errors import handle_error, ErrorContext
from .project_intelligence import ProjectIntelligence
from .enhanced_repl import start_enhanced_repl


@dataclass
class FileChange:
    """Represents a potential file change."""
    file_path: str
    change_type: str  # 'create', 'modify', 'delete'
    description: str
    confidence: float
    preview: Optional[str] = None
    line_range: Optional[Tuple[int, int]] = None


class ProactiveEditor:
    """Proactive file editing with Claude Code-style capabilities."""
    
    def __init__(self, root: Path, config: Config, console: Console):
        self.root = root
        self.config = config
        self.console = console
        self.search = HybridSearch(root, config=config)
        self.context = ContextEngine(root)
        
        # Track changes and suggestions
        self.pending_changes: List[FileChange] = []
        self.suggestion_history: List[dict] = []
        
    async def analyze_and_suggest_edits(self, query: str, files: Optional[List[str]] = None) -> List[FileChange]:
        """Analyze code and suggest proactive edits."""
        suggestions = []
        
        # Search for relevant files if not specified
        if not files:
            search_results = self.search.search(query, top=10)
            files = [result[0] for result in search_results if result[1] > 0.3]
        
        # Analyze each file for potential improvements
        for file_path in files:
            try:
                path = Path(file_path)
                if not path.exists() or not path.is_file():
                    continue
                    
                content = path.read_text(encoding='utf-8', errors='ignore')
                file_suggestions = await self._analyze_file_content(file_path, content, query)
                suggestions.extend(file_suggestions)
                
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not analyze {file_path}: {e}[/yellow]")
        
        return suggestions
    
    async def _analyze_file_content(self, file_path: str, content: str, query: str) -> List[FileChange]:
        """Analyze file content and suggest improvements."""
        suggestions = []
        lines = content.splitlines()
        
        # Common patterns to look for
        patterns = {
            'error_handling': {
                'pattern': r'(?:try|except|raise|error)',
                'suggestions': ['Add error handling', 'Improve exception catching', 'Add logging for errors']
            },
            'logging': {
                'pattern': r'(?:print|debug|log)',
                'suggestions': ['Add structured logging', 'Improve log formatting', 'Add log levels']
            },
            'documentation': {
                'pattern': r'(?:def |class |import)',
                'suggestions': ['Add docstrings', 'Improve type hints', 'Add usage examples']
            },
            'security': {
                'pattern': r'(?:password|token|key|secret)',
                'suggestions': ['Secure credential handling', 'Add input validation', 'Implement rate limiting']
            }
        }
        
        # Check for specific patterns based on query
        query_lower = query.lower()
        for pattern_name, pattern_info in patterns.items():
            if pattern_name in query_lower or any(word in query_lower for word in pattern_info['suggestions']):
                matches = []
                for i, line in enumerate(lines):
                    if re.search(pattern_info['pattern'], line, re.IGNORECASE):
                        matches.append(i + 1)
                
                if matches:
                    for suggestion in pattern_info['suggestions']:
                        change = FileChange(
                            file_path=file_path,
                            change_type='modify',
                            description=f"{suggestion} in {Path(file_path).name}",
                            confidence=0.7,
                            line_range=(min(matches), max(matches))
                        )
                        suggestions.append(change)
        
        return suggestions
    
    def preview_changes(self, changes: List[FileChange]) -> None:
        """Preview pending changes."""
        if not changes:
            self.console.print("[yellow]No changes to preview[/yellow]")
            return
        
        table = Table(title="Pending Changes", show_header=True, header_style="bold magenta")
        table.add_column("File", style="cyan", width=30)
        table.add_column("Type", style="green", width=10)
        table.add_column("Description", style="white", width=40)
        table.add_column("Confidence", style="yellow", width=10)
        
        for change in changes:
            confidence_str = f"{change.confidence:.1%}"
            table.add_row(
                change.file_path,
                change.change_type.title(),
                change.description,
                confidence_str
            )
        
        self.console.print(table)
    
    async def apply_changes(self, changes: List[FileChange], auto_approve: bool = False) -> bool:
        """Apply changes with user confirmation."""
        if not changes:
            return True
        
        self.preview_changes(changes)
        
        if not auto_approve:
            if not Confirm.ask(f"\nApply {len(changes)} changes?", console=self.console):
                return False
        
        success_count = 0
        for change in changes:
            try:
                if await self._apply_single_change(change):
                    success_count += 1
                    self.console.print(f"[green]✓[/green] Applied: {change.description}")
                else:
                    self.console.print(f"[red]✗[/red] Failed: {change.description}")
            except Exception as e:
                self.console.print(f"[red]Error applying {change.description}: {e}[/red]")
        
        self.console.print(f"\n[green]Successfully applied {success_count}/{len(changes)} changes[/green]")
        return success_count == len(changes)
    
    async def _apply_single_change(self, change: FileChange) -> bool:
        """Apply a single file change."""
        try:
            if change.change_type == 'modify':
                # Use existing editor functionality
                proposal = generate_edit_proposal(
                    change.description, 
                    [change.file_path], 
                    self.root, 
                    self.config
                )
                return proposal is not None
            elif change.change_type == 'create':
                # Create new file
                Path(change.file_path).touch()
                return True
            elif change.change_type == 'delete':
                # Delete file (with backup)
                file_path = Path(change.file_path)
                if file_path.exists():
                    backup_path = file_path.with_suffix(file_path.suffix + '.backup')
                    file_path.rename(backup_path)
                return True
        except Exception:
            return False
        
        return False


class AdvancedSearchInterface:
    """Advanced search interface with Claude Code-style capabilities."""
    
    def __init__(self, root: Path, config: Config, console: Console):
        self.root = root
        self.config = config
        self.console = console
        self.lexical_search = LexicalSearch(root)
        self.hybrid_search = HybridSearch(root, config=config)
        
    async def interactive_search(self) -> None:
        """Start interactive search session."""
        self.console.print("[bold cyan]🔍 Advanced Search Mode[/bold cyan]")
        self.console.print("[dim]Type your search queries. Use 'help' for commands, 'exit' to quit.[/dim]\n")
        
        search_history = []
        
        while True:
            try:
                query = Prompt.ask(
                    "[bold]Search", 
                    console=self.console,
                    default=""
                ).strip()
                
                if not query:
                    continue
                    
                if query.lower() in ['exit', 'quit']:
                    break
                elif query.lower() == 'help':
                    self._show_search_help()
                    continue
                elif query.lower() == 'history':
                    self._show_search_history(search_history)
                    continue
                elif query.startswith('!'):
                    # Execute previous search by number
                    try:
                        idx = int(query[1:]) - 1
                        if 0 <= idx < len(search_history):
                            query = search_history[idx]
                        else:
                            self.console.print("[red]Invalid history index[/red]")
                            continue
                    except ValueError:
                        self.console.print("[red]Invalid history format[/red]")
                        continue
                
                # Add to history
                if query not in search_history:
                    search_history.append(query)
                
                # Perform search
                await self._perform_advanced_search(query)
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Search interrupted[/yellow]")
            except Exception as e:
                self.console.print(f"[red]Search error: {e}[/red]")
    
    async def _perform_advanced_search(self, query: str) -> None:
        """Perform advanced search with multiple strategies."""
        with Live(Spinner("dots", text="Searching..."), console=self.console, refresh_per_second=10):
            # Parse search query for special commands
            search_type = "hybrid"  # default
            context_lines = 2
            file_filter = None
            
            # Parse query modifiers
            if query.startswith("regex:"):
                search_type = "regex"
                query = query[6:].strip()
            elif query.startswith("semantic:"):
                search_type = "semantic"
                query = query[9:].strip()
            elif query.startswith("lexical:"):
                search_type = "lexical"
                query = query[8:].strip()
            
            # Check for file type filters
            if " in:" in query:
                parts = query.split(" in:")
                query = parts[0].strip()
                file_filter = parts[1].strip()
            
            # Perform search based on type
            if search_type == "hybrid":
                results = self.hybrid_search.search(query, top=20)
                await self._display_hybrid_results(query, results)
            elif search_type == "lexical":
                include_filter = [f"*.{file_filter}"] if file_filter else None
                context_results = self.lexical_search.search_with_context(
                    query, 
                    context_before=context_lines, 
                    context_after=context_lines,
                    include=include_filter
                )
                await self._display_context_results(query, context_results)
            else:
                # Fallback to basic search
                basic_results = self.lexical_search.search(query)
                await self._display_basic_results(query, basic_results)
    
    async def _display_hybrid_results(self, query: str, results: List[Tuple[str, float]]) -> None:
        """Display hybrid search results."""
        if not results:
            self.console.print(f"[yellow]No results found for '{query}'[/yellow]")
            return
        
        self.console.print(f"[green]Found {len(results)} files matching '{query}':[/green]\n")
        
        for i, (file_path, score) in enumerate(results[:10], 1):
            # Show file info
            path_obj = Path(file_path)
            if path_obj.exists():
                size = decimal(path_obj.stat().st_size)
                modified = datetime.fromtimestamp(path_obj.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            else:
                size = "unknown"
                modified = "unknown"
            
            # Create file panel
            header = f"{i}. {file_path}"
            metadata = f"Score: {score:.3f} | Size: {size} | Modified: {modified}"
            
            # Try to show a preview
            preview = self._get_file_preview(file_path, query)
            
            panel_content = f"[dim]{metadata}[/dim]"
            if preview:
                panel_content += f"\n\n{preview}"
            
            panel = Panel(
                panel_content,
                title=header,
                border_style="blue" if score > 0.7 else "dim",
                padding=(0, 1)
            )
            self.console.print(panel)
    
    async def _display_context_results(self, query: str, results: List[dict]) -> None:
        """Display search results with context."""
        if not results:
            self.console.print(f"[yellow]No results found for '{query}'[/yellow]")
            return
        
        self.console.print(f"[green]Found {len(results)} matches for '{query}':[/green]\n")
        
        for i, result in enumerate(results[:10], 1):
            file_path = result["file"]
            match_line = result["match_line"]
            context = result.get("context", [])
            context_start = result.get("context_start", 1)
            
            # Highlight the matching line
            highlighted_context = []
            for j, line in enumerate(context):
                line_num = context_start + j
                if line_num == match_line:
                    highlighted_context.append(f"[bold yellow]>{line_num:4d}:[/bold yellow] [bold]{line}[/bold]")
                else:
                    highlighted_context.append(f"[dim]{line_num:4d}:[/dim] {line}")
            
            panel = Panel(
                "\n".join(highlighted_context),
                title=f"{i}. {file_path}:{match_line}",
                border_style="green",
                padding=(0, 1)
            )
            self.console.print(panel)
    
    def _get_file_preview(self, file_path: str, query: str, max_lines: int = 5) -> str:
        """Get a preview of file content around matches."""
        try:
            path_obj = Path(file_path)
            if not path_obj.exists() or path_obj.stat().st_size > 1024 * 1024:  # Skip large files
                return ""
            
            content = path_obj.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()
            
            # Find lines containing the query
            matching_lines = []
            for i, line in enumerate(lines):
                if query.lower() in line.lower():
                    matching_lines.append((i, line))
            
            if not matching_lines:
                # Show first few lines
                preview_lines = lines[:max_lines]
                return "\n".join(f"{i+1:4d}: {line}" for i, line in enumerate(preview_lines))
            
            # Show context around first match
            first_match_line = matching_lines[0][0]
            start = max(0, first_match_line - 2)
            end = min(len(lines), first_match_line + 3)
            
            preview_lines = []
            for i in range(start, end):
                line = lines[i]
                line_num = i + 1
                if i == first_match_line:
                    preview_lines.append(f"[bold yellow]{line_num:4d}: {line}[/bold yellow]")
                else:
                    preview_lines.append(f"{line_num:4d}: {line}")
            
            return "\n".join(preview_lines)
            
        except Exception:
            return ""
    
    def _show_search_help(self) -> None:
        """Show search help."""
        help_text = """
## Advanced Search Commands

### Search Types
- `hybrid: query` - Semantic + lexical search (default)
- `lexical: query` - Text-based search only  
- `semantic: query` - AI-powered semantic search
- `regex: pattern` - Regular expression search

### Filters
- `query in:py` - Search only in Python files
- `query in:js` - Search only in JavaScript files
- `query in:md` - Search only in Markdown files

### Special Commands
- `help` - Show this help
- `history` - Show search history
- `!N` - Repeat search #N from history
- `exit` or `quit` - Exit search mode

### Examples
- `function definition` - Find function definitions
- `lexical: TODO` - Find TODO comments
- `error handling in:py` - Find error handling in Python files
- `regex: class \\w+\\(.*\\):` - Find Python class definitions
        """
        
        panel = Panel(
            Markdown(help_text),
            title="🔍 Search Help",
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def _show_search_history(self, history: List[str]) -> None:
        """Show search history."""
        if not history:
            self.console.print("[yellow]No search history[/yellow]")
            return
        
        table = Table(title="Search History", show_header=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Query", style="cyan")
        
        for i, query in enumerate(history, 1):
            table.add_row(str(i), query)
        
        self.console.print(table)


class ProjectExplorer:
    """Project structure explorer with Claude Code-style navigation."""
    
    def __init__(self, root: Path, console: Console):
        self.root = root
        self.console = console
    
    def show_project_overview(self) -> None:
        """Show comprehensive project overview."""
        self.console.print("[bold cyan]📁 Project Overview[/bold cyan]\n")
        
        # Project structure
        self._show_file_tree()
        
        # Project statistics
        self.console.print()
        self._show_project_stats()
        
        # Recent changes
        self.console.print()
        self._show_recent_activity()
    
    def _show_file_tree(self, max_depth: int = 3) -> None:
        """Show file tree structure."""
        tree = Tree(f"📁 {self.root.name}")
        self._build_tree_recursive(tree, self.root, 0, max_depth)
        self.console.print(tree)
    
    def _build_tree_recursive(self, tree: Tree, path: Path, depth: int, max_depth: int) -> None:
        """Recursively build file tree."""
        if depth >= max_depth:
            return
        
        try:
            items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
            for item in items[:20]:  # Limit items per directory
                if item.name.startswith('.') and item.name not in ['.env', '.gitignore']:
                    continue
                
                if item.is_dir():
                    dir_node = tree.add(f"📁 {item.name}")
                    self._build_tree_recursive(dir_node, item, depth + 1, max_depth)
                else:
                    # Add file with icon based on extension
                    icon = self._get_file_icon(item.suffix)
                    size = decimal(item.stat().st_size) if item.exists() else "0B"
                    tree.add(f"{icon} {item.name} [dim]({size})[/dim]")
                    
        except PermissionError:
            tree.add("[red]Permission denied[/red]")
    
    def _get_file_icon(self, suffix: str) -> str:
        """Get emoji icon for file type."""
        icons = {
            '.py': '🐍',
            '.js': '💛',
            '.ts': '🔷',
            '.html': '🌐',
            '.css': '🎨',
            '.md': '📝',
            '.json': '📋',
            '.yaml': '📄',
            '.yml': '📄',
            '.txt': '📄',
            '.log': '📋',
            '.env': '🔧',
            '.sh': '⚡',
            '.sql': '🗄️',
        }
        return icons.get(suffix.lower(), '📄')
    
    def _show_project_stats(self) -> None:
        """Show project statistics."""
        stats = self._collect_project_stats()
        
        table = Table(title="Project Statistics", show_header=False)
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", style="white", width=15)
        
        for key, value in stats.items():
            table.add_row(key, str(value))
        
        self.console.print(table)
    
    def _collect_project_stats(self) -> Dict[str, Any]:
        """Collect project statistics."""
        stats = {
            "Total Files": 0,
            "Source Files": 0,
            "Total Size": 0,
            "Languages": set(),
            "Test Files": 0,
        }
        
        language_extensions = {
            '.py': 'Python',
            '.js': 'JavaScript', 
            '.ts': 'TypeScript',
            '.html': 'HTML',
            '.css': 'CSS',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.go': 'Go',
            '.rs': 'Rust',
        }
        
        try:
            for file_path in self.root.rglob('*'):
                if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                    stats["Total Files"] += 1
                    
                    try:
                        stats["Total Size"] += file_path.stat().st_size
                    except OSError:
                        pass
                    
                    suffix = file_path.suffix.lower()
                    if suffix in language_extensions:
                        stats["Source Files"] += 1
                        stats["Languages"].add(language_extensions[suffix])
                    
                    if 'test' in file_path.name.lower():
                        stats["Test Files"] += 1
        
        except Exception:
            pass
        
        # Format size
        stats["Total Size"] = decimal(stats["Total Size"])
        stats["Languages"] = ", ".join(sorted(stats["Languages"]))
        
        return stats
    
    def _show_recent_activity(self) -> None:
        """Show recent file activity."""
        try:
            recent_files = []
            cutoff_time = datetime.now().timestamp() - (7 * 24 * 3600)  # Last week
            
            for file_path in self.root.rglob('*'):
                if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                    try:
                        mtime = file_path.stat().st_mtime
                        if mtime > cutoff_time:
                            recent_files.append((file_path, mtime))
                    except OSError:
                        pass
            
            recent_files.sort(key=lambda x: x[1], reverse=True)
            
            if recent_files:
                table = Table(title="Recent Activity (Last 7 days)", show_header=True)
                table.add_column("File", style="cyan", width=40)
                table.add_column("Modified", style="dim", width=20)
                
                for file_path, mtime in recent_files[:10]:
                    rel_path = file_path.relative_to(self.root)
                    mod_time = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
                    table.add_row(str(rel_path), mod_time)
                
                self.console.print(table)
            else:
                self.console.print("[dim]No recent activity[/dim]")
                
        except Exception as e:
            self.console.print(f"[red]Could not analyze recent activity: {e}[/red]")


class AdvancedTerminal:
    """Main advanced terminal interface combining all capabilities."""
    
    def __init__(self, config: Config, root: Optional[Path] = None):
        self.config = config
        self.root = root or Path.cwd()
        self.console = Console()
        
        # Initialize components
        self.proactive_editor = ProactiveEditor(self.root, config, self.console)
        self.search_interface = AdvancedSearchInterface(self.root, config, self.console)
        self.project_explorer = ProjectExplorer(self.root, self.console)
        self.project_intelligence = ProjectIntelligence(self.root, config)
        
        # Session state
        self.session_active = True
        self.command_history = []
    
    async def start(self) -> None:
        """Start the advanced terminal interface."""
        self._show_welcome()
        
        try:
            while self.session_active:
                await self._process_command_cycle()
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Session terminated by user[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Unexpected error: {e}[/red]")
            context = ErrorContext(command="advanced_terminal")
            handle_error(e, context)
        finally:
            self._show_goodbye()
    
    def _show_welcome(self) -> None:
        """Show welcome message."""
        welcome_text = Text.assemble(
            Text("Welcome to ", style="white"),
            Text("tc", style="bold cyan"),
            Text(" Advanced Terminal\n", style="white"),
            Text("Claude Code-style capabilities for proactive development\n", style="dim"),
        )
        
        panel = Panel(
            welcome_text,
            title="🚀 Advanced Development Interface",
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(panel)
        
        # Show quick help
        self.console.print("[dim]Type 'help' for commands, 'search' for advanced search, 'overview' for project info[/dim]\n")
    
    async def _process_command_cycle(self) -> None:
        """Process one command cycle."""
        try:
            command = Prompt.ask(
                "[bold cyan]tc>[/bold cyan]",
                console=self.console,
                default=""
            ).strip()
            
            if not command:
                return
            
            # Add to history
            if command not in self.command_history:
                self.command_history.append(command)
            
            # Process command
            await self._execute_command(command)
            
        except (KeyboardInterrupt, EOFError):
            self.session_active = False
    
    async def _execute_command(self, command: str) -> None:
        """Execute a command."""
        cmd_parts = command.split()
        if not cmd_parts:
            return
        
        cmd = cmd_parts[0].lower()
        args = cmd_parts[1:] if len(cmd_parts) > 1 else []
        
        # Built-in commands
        if cmd in ['exit', 'quit']:
            self.session_active = False
        elif cmd == 'help':
            self._show_help()
        elif cmd == 'search':
            await self.search_interface.interactive_search()
        elif cmd == 'overview':
            self.project_explorer.show_project_overview()
        elif cmd == 'insights':
            self.project_intelligence.show_project_insights()
        elif cmd == 'repl':
            await start_enhanced_repl(self.config, self.root)
        elif cmd == 'edit':
            await self._handle_edit_command(args)
        elif cmd == 'suggest':
            await self._handle_suggest_command(args)
        elif cmd == 'history':
            self._show_command_history()
        elif cmd == 'clear':
            self.console.clear()
            self._show_welcome()
        elif cmd == 'model':
            await self._handle_model_command(args)
        else:
            # Try natural language processing
            await self._handle_natural_command(command)
    
    async def _handle_edit_command(self, args: List[str]) -> None:
        """Handle edit command."""
        if not args:
            self.console.print("[yellow]Usage: edit <files...> or edit <description>[/yellow]")
            return
        
        # Check if args are file paths or description
        if all(Path(arg).exists() for arg in args):
            # Edit specific files
            self.console.print(f"[cyan]Opening editor for: {', '.join(args)}[/cyan]")
            # Integrate with existing editor
        else:
            # Treat as natural language edit request
            description = " ".join(args)
            changes = await self.proactive_editor.analyze_and_suggest_edits(description)
            
            if changes:
                await self.proactive_editor.apply_changes(changes)
            else:
                self.console.print("[yellow]No changes suggested for that request[/yellow]")
    
    async def _handle_suggest_command(self, args: List[str]) -> None:
        """Handle suggest command."""
        if not args:
            self.console.print("[yellow]Usage: suggest <description>[/yellow]")
            return
        
        description = " ".join(args)
        self.console.print(f"[cyan]Analyzing project for: {description}[/cyan]")
        
        with Live(Spinner("dots", text="Analyzing..."), console=self.console, refresh_per_second=10):
            changes = await self.proactive_editor.analyze_and_suggest_edits(description)
        
        if changes:
            self.proactive_editor.preview_changes(changes)
            if Confirm.ask("\nApply suggestions?", console=self.console):
                await self.proactive_editor.apply_changes(changes, auto_approve=True)
        else:
            self.console.print("[yellow]No suggestions found[/yellow]")
    
    async def _handle_model_command(self, args: List[str]) -> None:
        """Handle model management commands."""
        from .llm import LLMOrchestrator
        
        if len(args) == 0:
            # Show current model
            current_model = self.config.get("model.default", "mock-llm")
            self.console.print(f"[cyan]Current model: {current_model}[/cyan]")
            
            # Show available models
            orchestrator = LLMOrchestrator()
            available_models = list(orchestrator.adapters.keys())
            self.console.print("\n[bold]Available models:[/bold]")
            for model in available_models:
                indicator = " ← current" if model == current_model else ""
                self.console.print(f"  • {model}{indicator}")
            
        elif len(args) == 1:
            # Set model
            new_model = args[0]
            orchestrator = LLMOrchestrator()
            
            if new_model not in orchestrator.adapters:
                self.console.print(f"[red]❌ Unknown model: {new_model}[/red]")
                available_models = list(orchestrator.adapters.keys())
                self.console.print("[yellow]Available models:[/yellow] " + ", ".join(available_models))
                return
            
            # Update configuration
            old_model = self.config.get("model.default", "mock-llm")
            self.config.set("model.default", new_model)
            self.config.save()
            
            self.console.print(f"[green]✅ Model changed from {old_model} to {new_model}[/green]")
            
            # Show a helpful tip about the new model
            model_tips = {
                "mock-llm": "Mock model for testing - no API calls made",
                "openai:gpt": "OpenAI GPT-4o-mini - requires OPENAI_API_KEY",
                "anthropic:claude": "Anthropic Claude Haiku - requires ANTHROPIC_API_KEY", 
                "local:ollama": "Local Ollama model - requires Ollama running on localhost:11434",
                "openrouter": "OpenRouter API - requires OPENROUTER_API_KEY"
            }
            tip = model_tips.get(new_model, "")
            if tip:
                self.console.print(f"[dim]💡 {tip}[/dim]")
        else:
            self.console.print("[yellow]Usage: 'model' to show current, 'model <name>' to switch[/yellow]")

    async def _handle_natural_command(self, command: str) -> None:
        """Handle natural language commands."""
        # This would integrate with the existing natural language interface
        self.console.print(f"[dim]Processing natural language: {command}[/dim]")
        
        # Keywords for different actions
        if any(word in command.lower() for word in ['find', 'search', 'look for']):
            # Extract search query
            query = command
            for prefix in ['find', 'search for', 'look for']:
                if prefix in command.lower():
                    query = command.lower().split(prefix, 1)[1].strip()
                    break
            
            await self.search_interface._perform_advanced_search(query)
        
        elif any(word in command.lower() for word in ['edit', 'change', 'modify', 'fix']):
            changes = await self.proactive_editor.analyze_and_suggest_edits(command)
            if changes:
                self.proactive_editor.preview_changes(changes)
                if Confirm.ask("\nApply changes?", console=self.console):
                    await self.proactive_editor.apply_changes(changes)
        
        else:
            self.console.print("[yellow]Command not recognized. Try 'help' for available commands.[/yellow]")
    
    def _show_help(self) -> None:
        """Show help information."""
        help_text = """
# Advanced Terminal Commands

## Core Commands
- `search` - Enter interactive search mode
- `overview` - Show project overview and statistics
- `insights` - Show intelligent project analysis and suggestions
- `repl` - Start enhanced REPL with tab completion
- `edit <files|description>` - Edit files or make changes by description
- `suggest <description>` - Get proactive suggestions for improvements
- `model [model-name]` - Show/change AI model (e.g., `model openai:gpt`)
- `history` - Show command history
- `clear` - Clear screen
- `exit` or `quit` - Exit terminal

## Search Commands (in search mode)
- `hybrid: query` - Semantic + lexical search
- `lexical: query` - Text-based search only
- `semantic: query` - AI-powered search  
- `regex: pattern` - Regular expression search
- `query in:ext` - Filter by file extension

## Natural Language
You can also use natural language commands:
- "find all TODO comments"
- "edit error handling in auth.py"
- "suggest improvements for database code"
- "search for function definitions"

## Tips
- Use Tab completion for file paths
- Commands are case-insensitive
- Use arrow keys to navigate history
- Ctrl+C to interrupt long operations
        """
        
        panel = Panel(
            Markdown(help_text),
            title="📚 Help",
            border_style="green",
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def _show_command_history(self) -> None:
        """Show command history."""
        if not self.command_history:
            self.console.print("[yellow]No command history[/yellow]")
            return
        
        table = Table(title="Command History", show_header=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Command", style="cyan")
        
        for i, cmd in enumerate(self.command_history, 1):
            table.add_row(str(i), cmd)
        
        self.console.print(table)
    
    def _show_goodbye(self) -> None:
        """Show goodbye message."""
        goodbye_text = Text.assemble(
            Text("Thanks for using ", style="dim"),
            Text("tc", style="bold cyan"),
            Text(" Advanced Terminal! 👋", style="dim"),
        )
        
        self.console.print(Panel(goodbye_text, border_style="magenta"))


# Entry point for advanced terminal
async def start_advanced_terminal(config: Config, root: Optional[Path] = None) -> None:
    """Start the advanced terminal interface."""
    terminal = AdvancedTerminal(config, root)
    await terminal.start()