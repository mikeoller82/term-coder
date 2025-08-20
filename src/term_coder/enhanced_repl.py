"""
Enhanced REPL capabilities with syntax highlighting, completion, and session management.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import readline
import rlcompleter

from rich.console import Console
from rich.syntax import Syntax
from rich.text import Text
from rich.table import Table
from rich.panel import Panel

from .config import Config
from .utils import iter_source_files


class SessionManager:
    """Manages terminal sessions with persistence and history."""
    
    def __init__(self, config: Config, root: Path):
        self.config = config
        self.root = root
        self.console = Console()
        
        # Session storage
        self.session_dir = root / ".term-coder" / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # Current session
        self.session_id = self._generate_session_id()
        self.session_file = self.session_dir / f"{self.session_id}.json"
        self.start_time = datetime.now()
        
        # Session state
        self.command_history: List[Dict[str, Any]] = []
        self.context_files: List[str] = []
        self.bookmarks: Dict[str, str] = {}
        self.variables: Dict[str, Any] = {}
        
        # Load previous session if exists
        self._load_session()
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"session_{timestamp}"
    
    def _load_session(self) -> None:
        """Load previous session data."""
        # Look for the most recent session
        sessions = list(self.session_dir.glob("session_*.json"))
        if not sessions:
            return
        
        # Load the most recent session
        latest_session = max(sessions, key=lambda p: p.stat().st_mtime)
        
        # Only load if it's less than 24 hours old
        if time.time() - latest_session.stat().st_mtime < 86400:  # 24 hours
            try:
                with open(latest_session, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.command_history = data.get('command_history', [])
                self.context_files = data.get('context_files', [])
                self.bookmarks = data.get('bookmarks', {})
                self.variables = data.get('variables', {})
                
                self.console.print(f"[dim]Restored session from {latest_session.name}[/dim]")
                
            except (json.JSONDecodeError, KeyError) as e:
                self.console.print(f"[yellow]Could not restore session: {e}[/yellow]")
    
    def save_session(self) -> None:
        """Save current session data."""
        try:
            session_data = {
                'session_id': self.session_id,
                'start_time': self.start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'command_history': self.command_history,
                'context_files': self.context_files,
                'bookmarks': self.bookmarks,
                'variables': self.variables,
                'project_root': str(self.root)
            }
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.console.print(f"[yellow]Could not save session: {e}[/yellow]")
    
    def add_command(self, command: str, result: Optional[Dict[str, Any]] = None) -> None:
        """Add command to history."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'command': command,
            'result': result,
            'working_directory': str(Path.cwd().relative_to(self.root)),
            'context_files': list(self.context_files)
        }
        self.command_history.append(entry)
        
        # Keep only last 1000 commands
        if len(self.command_history) > 1000:
            self.command_history = self.command_history[-1000:]
    
    def get_command_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent command history."""
        return self.command_history[-limit:]
    
    def add_context_file(self, file_path: str) -> None:
        """Add file to context."""
        if file_path not in self.context_files:
            self.context_files.append(file_path)
            
        # Keep only last 20 context files
        if len(self.context_files) > 20:
            self.context_files = self.context_files[-20:]
    
    def remove_context_file(self, file_path: str) -> None:
        """Remove file from context."""
        if file_path in self.context_files:
            self.context_files.remove(file_path)
    
    def clear_context(self) -> None:
        """Clear all context files."""
        self.context_files.clear()
    
    def add_bookmark(self, name: str, path: str) -> None:
        """Add bookmark for quick navigation."""
        self.bookmarks[name] = path
    
    def get_bookmark(self, name: str) -> Optional[str]:
        """Get bookmark path."""
        return self.bookmarks.get(name)
    
    def list_bookmarks(self) -> Dict[str, str]:
        """List all bookmarks."""
        return self.bookmarks.copy()
    
    def set_variable(self, name: str, value: Any) -> None:
        """Set session variable."""
        self.variables[name] = value
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get session variable."""
        return self.variables.get(name, default)
    
    def show_session_info(self) -> None:
        """Display session information."""
        duration = datetime.now() - self.start_time
        
        info_table = Table(title=f"Session Info: {self.session_id}", show_header=False)
        info_table.add_column("Property", style="cyan", width=20)
        info_table.add_column("Value", style="white")
        
        info_table.add_row("Duration", str(duration).split('.')[0])
        info_table.add_row("Commands", str(len(self.command_history)))
        info_table.add_row("Context Files", str(len(self.context_files)))
        info_table.add_row("Bookmarks", str(len(self.bookmarks)))
        info_table.add_row("Variables", str(len(self.variables)))
        info_table.add_row("Project Root", str(self.root))
        
        self.console.print(info_table)
        
        # Show context files if any
        if self.context_files:
            self.console.print("\n[bold]Context Files:[/bold]")
            for i, file_path in enumerate(self.context_files[-10:], 1):  # Show last 10
                self.console.print(f"  {i}. {file_path}")
        
        # Show bookmarks if any
        if self.bookmarks:
            self.console.print("\n[bold]Bookmarks:[/bold]")
            for name, path in self.bookmarks.items():
                self.console.print(f"  [cyan]{name}[/cyan] → {path}")


class SyntaxHighlighter:
    """Provides syntax highlighting for code snippets."""
    
    def __init__(self, console: Console):
        self.console = console
        
        # File extension to language mapping
        self.language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'jsx',
            '.tsx': 'tsx',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.sql': 'sql',
            '.sh': 'bash',
            '.bash': 'bash',
            '.zsh': 'zsh',
            '.fish': 'fish',
            '.md': 'markdown',
            '.rst': 'rst',
            '.toml': 'toml',
            '.ini': 'ini',
            '.cfg': 'ini',
            '.conf': 'ini',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.java': 'java',
            '.kt': 'kotlin',
            '.swift': 'swift',
            '.rb': 'ruby',
            '.php': 'php',
            '.r': 'r',
            '.R': 'r',
            '.scala': 'scala',
            '.clj': 'clojure',
            '.hs': 'haskell',
            '.elm': 'elm',
            '.dart': 'dart',
            '.vue': 'vue',
        }
    
    def highlight_file(self, file_path: str, max_lines: int = 50) -> None:
        """Display file with syntax highlighting."""
        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                self.console.print(f"[red]File not found: {file_path}[/red]")
                return
            
            if path_obj.stat().st_size > 1024 * 1024:  # 1MB limit
                self.console.print(f"[yellow]File too large: {file_path}[/yellow]")
                return
            
            # Read file content
            try:
                content = path_obj.read_text(encoding='utf-8', errors='ignore')
            except UnicodeDecodeError:
                content = path_obj.read_text(encoding='latin-1', errors='ignore')
            
            # Truncate if too many lines
            lines = content.splitlines()
            if len(lines) > max_lines:
                content = '\n'.join(lines[:max_lines]) + '\n... (truncated)'
            
            # Detect language
            language = self.language_map.get(path_obj.suffix.lower(), 'text')
            
            # Display with syntax highlighting
            syntax = Syntax(
                content, 
                language, 
                theme="monokai", 
                line_numbers=True,
                word_wrap=True,
                background_color="default"
            )
            
            panel = Panel(
                syntax,
                title=f"📄 {file_path}",
                border_style="blue",
                padding=(0, 1)
            )
            
            self.console.print(panel)
            
        except Exception as e:
            self.console.print(f"[red]Error displaying file: {e}[/red]")
    
    def highlight_code(self, code: str, language: str = "python") -> None:
        """Display code snippet with syntax highlighting."""
        try:
            syntax = Syntax(
                code, 
                language, 
                theme="monokai", 
                line_numbers=True,
                word_wrap=True,
                background_color="default"
            )
            
            self.console.print(syntax)
            
        except Exception as e:
            self.console.print(f"[red]Error highlighting code: {e}[/red]")


class CommandCompleter:
    """Provides intelligent command completion."""
    
    def __init__(self, root: Path, session: SessionManager):
        self.root = root
        self.session = session
        
        # Basic commands
        self.commands = [
            'search', 'find', 'edit', 'suggest', 'overview', 'help',
            'history', 'clear', 'bookmark', 'context', 'session',
            'cd', 'ls', 'cat', 'grep', 'exit', 'quit'
        ]
        
        # File cache for completion
        self._file_cache: List[str] = []
        self._cache_time = 0
        self._cache_ttl = 300  # 5 minutes
        
        # Set up readline completion
        self._setup_completion()
    
    def _setup_completion(self) -> None:
        """Set up readline completion."""
        try:
            import readline
            readline.set_completer(self.complete)
            readline.parse_and_bind("tab: complete")
            
            # Set up history
            history_file = self.root / ".term-coder" / "command_history"
            history_file.parent.mkdir(parents=True, exist_ok=True)
            
            if history_file.exists():
                readline.read_history_file(str(history_file))
            
            # Save history on exit
            import atexit
            atexit.register(readline.write_history_file, str(history_file))
            
        except ImportError:
            pass  # readline not available
    
    def complete(self, text: str, state: int) -> Optional[str]:
        """Readline completion function."""
        try:
            if state == 0:
                self._matches = self._get_matches(text)
            
            if state < len(self._matches):
                return self._matches[state]
            
        except Exception:
            pass
        
        return None
    
    def _get_matches(self, text: str) -> List[str]:
        """Get completion matches for text."""
        matches = []
        
        # Complete commands
        for cmd in self.commands:
            if cmd.startswith(text):
                matches.append(cmd)
        
        # Complete file paths
        file_matches = self._complete_files(text)
        matches.extend(file_matches)
        
        # Complete bookmarks
        for bookmark in self.session.bookmarks:
            if bookmark.startswith(text):
                matches.append(bookmark)
        
        # Complete context files
        for context_file in self.session.context_files:
            if context_file.startswith(text):
                matches.append(context_file)
        
        return sorted(set(matches))
    
    def _complete_files(self, text: str) -> List[str]:
        """Complete file paths."""
        matches = []
        
        # Refresh cache if needed
        current_time = time.time()
        if current_time - self._cache_time > self._cache_ttl:
            self._refresh_file_cache()
        
        # Find matching files
        for file_path in self._file_cache:
            if file_path.startswith(text):
                matches.append(file_path)
                
            # Also match basename
            basename = os.path.basename(file_path)
            if basename.startswith(text) and basename not in matches:
                matches.append(file_path)
        
        return matches[:20]  # Limit matches
    
    def _refresh_file_cache(self) -> None:
        """Refresh file cache for completion."""
        try:
            self._file_cache = []
            
            # Get source files
            for file_path in iter_source_files(self.root):
                rel_path = str(file_path.relative_to(self.root))
                self._file_cache.append(rel_path)
            
            # Add common directories
            for item in self.root.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    self._file_cache.append(item.name + '/')
            
            self._cache_time = time.time()
            
        except Exception:
            pass  # Ignore errors during cache refresh


class EnhancedREPL:
    """Enhanced REPL with session management, syntax highlighting, and completion."""
    
    def __init__(self, config: Config, root: Path):
        self.config = config
        self.root = root
        self.console = Console()
        
        # Initialize components
        self.session = SessionManager(config, root)
        self.highlighter = SyntaxHighlighter(self.console)
        self.completer = CommandCompleter(root, self.session)
        
        # REPL state
        self.running = True
    
    async def start(self) -> None:
        """Start the enhanced REPL."""
        self.console.print("[bold cyan]🚀 Enhanced Terminal REPL[/bold cyan]")
        self.console.print("[dim]Type 'help' for commands, Tab for completion[/dim]\n")
        
        try:
            while self.running:
                await self._process_command_cycle()
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Goodbye! 👋[/yellow]")
        except Exception as e:
            self.console.print(f"[red]REPL error: {e}[/red]")
        finally:
            self.session.save_session()
    
    async def _process_command_cycle(self) -> None:
        """Process one command cycle."""
        try:
            # Show context indicator
            context_info = ""
            if self.session.context_files:
                context_info = f"[dim]({len(self.session.context_files)} files)[/dim] "
            
            # Get command with completion support
            try:
                import readline
                command = input(f"{context_info}tc> ").strip()
            except ImportError:
                # Fallback without readline
                from rich.prompt import Prompt
                command = Prompt.ask(f"{context_info}[bold cyan]tc>[/bold cyan]", console=self.console).strip()
            
            if not command:
                return
            
            # Add to session history
            self.session.add_command(command)
            
            # Process command
            await self._execute_enhanced_command(command)
            
        except (EOFError, KeyboardInterrupt):
            self.running = False
    
    async def _execute_enhanced_command(self, command: str) -> None:
        """Execute enhanced command with additional features."""
        parts = command.split()
        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        # Enhanced commands
        if cmd in ['exit', 'quit']:
            self.running = False
        
        elif cmd == 'help':
            self._show_enhanced_help()
        
        elif cmd == 'session':
            if args and args[0] == 'info':
                self.session.show_session_info()
            else:
                self.session.show_session_info()
        
        elif cmd == 'context':
            await self._handle_context_command(args)
        
        elif cmd == 'bookmark':
            await self._handle_bookmark_command(args)
        
        elif cmd == 'history':
            self._show_command_history(int(args[0]) if args and args[0].isdigit() else 20)
        
        elif cmd == 'cat':
            if args:
                for file_path in args:
                    self.highlighter.highlight_file(file_path)
        
        elif cmd == 'ls':
            self._list_directory(args[0] if args else '.')
        
        elif cmd == 'cd':
            self._change_directory(args[0] if args else str(self.root))
        
        elif cmd == 'clear':
            self.console.clear()
        
        else:
            # Forward to main command processor or show error
            self.console.print(f"[yellow]Unknown command: {cmd}[/yellow]")
            self.console.print("[dim]Type 'help' for available commands[/dim]")
    
    async def _handle_context_command(self, args: List[str]) -> None:
        """Handle context management commands."""
        if not args:
            # Show current context
            if self.session.context_files:
                table = Table(title="Context Files", show_header=True)
                table.add_column("#", style="dim", width=4)
                table.add_column("File", style="cyan")
                
                for i, file_path in enumerate(self.session.context_files, 1):
                    table.add_row(str(i), file_path)
                
                self.console.print(table)
            else:
                self.console.print("[yellow]No files in context[/yellow]")
        
        elif args[0] == 'add':
            if len(args) > 1:
                file_path = args[1]
                if Path(file_path).exists():
                    self.session.add_context_file(file_path)
                    self.console.print(f"[green]Added to context: {file_path}[/green]")
                else:
                    self.console.print(f"[red]File not found: {file_path}[/red]")
            else:
                self.console.print("[yellow]Usage: context add <file>[/yellow]")
        
        elif args[0] == 'remove':
            if len(args) > 1:
                file_path = args[1]
                self.session.remove_context_file(file_path)
                self.console.print(f"[green]Removed from context: {file_path}[/green]")
            else:
                self.console.print("[yellow]Usage: context remove <file>[/yellow]")
        
        elif args[0] == 'clear':
            self.session.clear_context()
            self.console.print("[green]Context cleared[/green]")
        
        else:
            self.console.print("[yellow]Usage: context [add|remove|clear] [file][/yellow]")
    
    async def _handle_bookmark_command(self, args: List[str]) -> None:
        """Handle bookmark commands."""
        if not args:
            # List bookmarks
            bookmarks = self.session.list_bookmarks()
            if bookmarks:
                table = Table(title="Bookmarks", show_header=True)
                table.add_column("Name", style="cyan")
                table.add_column("Path", style="white")
                
                for name, path in bookmarks.items():
                    table.add_row(name, path)
                
                self.console.print(table)
            else:
                self.console.print("[yellow]No bookmarks[/yellow]")
        
        elif args[0] == 'add':
            if len(args) >= 3:
                name, path = args[1], args[2]
                self.session.add_bookmark(name, path)
                self.console.print(f"[green]Bookmark added: {name} → {path}[/green]")
            else:
                self.console.print("[yellow]Usage: bookmark add <name> <path>[/yellow]")
        
        elif args[0] == 'cd':
            if len(args) > 1:
                bookmark_path = self.session.get_bookmark(args[1])
                if bookmark_path:
                    self._change_directory(bookmark_path)
                else:
                    self.console.print(f"[red]Bookmark not found: {args[1]}[/red]")
            else:
                self.console.print("[yellow]Usage: bookmark cd <name>[/yellow]")
        
        else:
            self.console.print("[yellow]Usage: bookmark [add|cd] [args...][/yellow]")
    
    def _show_command_history(self, limit: int = 20) -> None:
        """Show command history."""
        history = self.session.get_command_history(limit)
        
        if not history:
            self.console.print("[yellow]No command history[/yellow]")
            return
        
        table = Table(title=f"Command History (Last {len(history)})", show_header=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Time", style="dim", width=12)
        table.add_column("Command", style="cyan")
        
        for i, entry in enumerate(history, 1):
            timestamp = datetime.fromisoformat(entry['timestamp'])
            time_str = timestamp.strftime('%H:%M:%S')
            table.add_row(str(i), time_str, entry['command'])
        
        self.console.print(table)
    
    def _list_directory(self, path: str) -> None:
        """List directory contents."""
        try:
            dir_path = Path(path)
            if not dir_path.exists():
                self.console.print(f"[red]Directory not found: {path}[/red]")
                return
            
            if not dir_path.is_dir():
                self.console.print(f"[red]Not a directory: {path}[/red]")
                return
            
            table = Table(title=f"📁 {path}", show_header=True)
            table.add_column("Name", style="cyan", width=30)
            table.add_column("Type", style="dim", width=10)
            table.add_column("Size", style="yellow", width=10)
            table.add_column("Modified", style="dim", width=12)
            
            items = sorted(dir_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
            
            for item in items[:50]:  # Limit to 50 items
                if item.is_dir():
                    name = f"📁 {item.name}"
                    item_type = "dir"
                    size = "-"
                else:
                    name = f"📄 {item.name}"
                    item_type = "file"
                    try:
                        size = self._format_file_size(item.stat().st_size)
                    except OSError:
                        size = "unknown"
                
                try:
                    modified = datetime.fromtimestamp(item.stat().st_mtime).strftime('%Y-%m-%d')
                except OSError:
                    modified = "unknown"
                
                table.add_row(name, item_type, size, modified)
            
            self.console.print(table)
            
        except Exception as e:
            self.console.print(f"[red]Error listing directory: {e}[/red]")
    
    def _format_file_size(self, size: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"
    
    def _change_directory(self, path: str) -> None:
        """Change current directory."""
        try:
            target_path = Path(path).resolve()
            
            # Ensure we stay within project root
            try:
                target_path.relative_to(self.root)
            except ValueError:
                self.console.print(f"[red]Path outside project root: {path}[/red]")
                return
            
            if not target_path.exists():
                self.console.print(f"[red]Directory not found: {path}[/red]")
                return
            
            if not target_path.is_dir():
                self.console.print(f"[red]Not a directory: {path}[/red]")
                return
            
            os.chdir(target_path)
            rel_path = target_path.relative_to(self.root)
            self.console.print(f"[green]Changed to: {rel_path}[/green]")
            
        except Exception as e:
            self.console.print(f"[red]Error changing directory: {e}[/red]")
    
    def _show_enhanced_help(self) -> None:
        """Show enhanced help."""
        help_text = """
# Enhanced Terminal REPL Commands

## Navigation & Files
- `ls [path]` - List directory contents
- `cd <path>` - Change directory
- `cat <file>` - Display file with syntax highlighting

## Context Management
- `context` - Show context files
- `context add <file>` - Add file to context
- `context remove <file>` - Remove file from context
- `context clear` - Clear all context

## Bookmarks
- `bookmark` - List all bookmarks
- `bookmark add <name> <path>` - Add bookmark
- `bookmark cd <name>` - Navigate to bookmark

## Session Management
- `session` - Show session information
- `history [N]` - Show command history (default: 20)
- `clear` - Clear screen

## General
- `help` - Show this help
- `exit` or `quit` - Exit REPL

## Features
- **Tab Completion**: Auto-complete commands, files, and bookmarks
- **Syntax Highlighting**: Rich code display with color
- **Persistent History**: Commands saved across sessions
- **Context Awareness**: Track and manage working files
- **Smart Navigation**: Bookmarks and directory history

## Tips
- Use Tab for completion
- Commands and file paths are completed automatically
- Session state is automatically saved
- Context files help with project navigation
        """
        
        panel = Panel(
            Text.from_markup(help_text.strip()),
            title="📚 Enhanced REPL Help",
            border_style="green",
            padding=(1, 2)
        )
        
        self.console.print(panel)


# Entry point for enhanced REPL
async def start_enhanced_repl(config: Config, root: Optional[Path] = None) -> None:
    """Start the enhanced REPL."""
    project_root = root or Path.cwd()
    repl = EnhancedREPL(config, project_root)
    await repl.start()