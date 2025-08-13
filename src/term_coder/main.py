#!/usr/bin/env python3
"""
Term-Coder: Natural Language Coding Assistant

Just run 'tc' and start talking naturally about your code!

Examples:
  tc                          # Start interactive mode
  tc "debug for errors"       # Find and analyze errors
  tc "fix the login bug"      # Fix specific issues
  tc "explain main.py"        # Understand code
  tc "add logging to auth.py" # Make changes
"""

import sys
import asyncio
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console

from .config import Config, ensure_initialized
from .natural_interface import NaturalLanguageInterface
from .interactive_terminal import start_interactive_mode
from .errors import handle_error, ErrorContext


console = Console()


def main():
    """Main entry point for term-coder."""
    
    # If no arguments, start interactive mode
    if len(sys.argv) == 1:
        start_interactive_session()
        return
    
    # If arguments look like natural language, process them
    args = sys.argv[1:]
    
    # Check for help flags
    if any(arg in ['-h', '--help', 'help'] for arg in args):
        show_help()
        return
    
    # Check for version flag
    if any(arg in ['-v', '--version', 'version'] for arg in args):
        console.print("term-coder version 1.0.0")
        return
    
    # Check for traditional commands
    traditional_commands = [
        'init', 'config', 'index', 'search', 'edit', 'diff', 'apply',
        'run', 'test', 'fix', 'explain', 'review', 'commit', 'pr',
        'generate', 'refactor-rename', 'privacy', 'scan-secrets',
        'audit', 'cleanup', 'diagnostics', 'export-errors', 'tui',
        'lsp', 'symbols', 'frameworks', 'interactive'
    ]
    
    if args[0] in traditional_commands:
        # Use traditional CLI
        from .cli import app
        app()
        return
    
    # Otherwise, treat as natural language
    user_input = " ".join(args)
    process_natural_language(user_input)


def start_interactive_session():
    """Start the interactive terminal session."""
    try:
        cfg = load_config_with_init()
        
        # Show the awesome welcome screen
        from .branding import show_welcome_screen, show_motivational_message
        show_welcome_screen(console)
        show_motivational_message(console)
        
        asyncio.run(start_interactive_mode(cfg))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye! 👋[/yellow]")
    except Exception as e:
        console.print(f"[red]Failed to start: {e}[/red]")
        console.print("[dim]Try 'tc init' first to set up configuration[/dim]")
        sys.exit(1)


def process_natural_language(user_input: str):
    """Process natural language input."""
    try:
        cfg = load_config_with_init()
        
        # Check for easter eggs first
        from .branding import show_easter_eggs, get_random_comment
        if show_easter_eggs(console, user_input):
            return
        
        # Show what we're processing with a witty comment
        thinking_comment = get_random_comment("thinking")
        console.print(f"[dim]{thinking_comment}[/dim]")
        
        # Use natural language interface
        natural_interface = NaturalLanguageInterface(cfg, console)
        result = asyncio.run(natural_interface.process_natural_input(user_input))
        
        if result.get("success"):
            action_result = result.get("result", {})
            action = action_result.get("action", "chat")
            
            # Display result based on action type
            if action == "chat":
                response = action_result.get("response", "")
                console.print(f"\n[bold magenta]🤖 AI:[/bold magenta] {response}")
            else:
                # For non-chat actions, show what was done
                message = action_result.get("message", "Action completed")
                console.print(f"\n[green]✅ {message}[/green]")
                
                # Show suggestions if available
                suggestions = action_result.get("suggestions", [])
                if suggestions:
                    console.print("\n[bold]💡 Next steps:[/bold]")
                    for suggestion in suggestions:
                        console.print(f"  • {suggestion}")
        else:
            error_msg = result.get("error", "Unknown error")
            console.print(f"\n[red]❌ {error_msg}[/red]")
            console.print("[dim]Try being more specific or use 'tc --help' for available commands[/dim]")
            sys.exit(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
    except Exception as e:
        context = ErrorContext(command="natural_language", user_input=user_input)
        if not handle_error(e, context):
            console.print(f"\n[red]Error: {e}[/red]")
            console.print("[dim]Try 'tc --help' for available commands or 'tc interactive' for interactive mode[/dim]")
            sys.exit(1)


def load_config_with_init() -> Config:
    """Load configuration, initializing if needed."""
    try:
        return Config.load()
    except FileNotFoundError:
        console.print("[yellow]Configuration not found. Initializing...[/yellow]")
        try:
            ensure_initialized()
            return Config.load()
        except Exception as e:
            console.print(f"[red]Failed to initialize configuration: {e}[/red]")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Failed to load configuration: {e}[/red]")
        sys.exit(1)


def show_help():
    """Show help information."""
    help_text = """
[bold cyan]Term-Coder: AI Coding Assistant[/bold cyan]

🚀 [bold]NATURAL LANGUAGE INTERFACE[/bold]
Just tell term-coder what you want to do in plain English!

[bold green]Examples:[/bold green]
  tc                          # Start interactive mode
  tc "debug for errors"       # Find and analyze errors  
  tc "fix the login bug"      # Fix specific issues
  tc "explain main.py"        # Understand code
  tc "add logging to auth.py" # Make changes
  tc "search for TODO items"  # Find specific code
  tc "review my changes"      # Code review
  tc "run the tests"          # Execute tests

💬 [bold]INTERACTIVE MODE[/bold]
  tc                          # Start conversational mode
  tc interactive              # Explicit interactive mode

🔧 [bold]TRADITIONAL COMMANDS[/bold]
  tc init                     # Initialize configuration
  tc index                    # Build search index
  tc search "query"           # Search code
  tc edit "instruction" --files file.py  # Edit files
  tc diff                     # Show pending changes
  tc apply                    # Apply changes
  tc review                   # Code review
  tc test                     # Run tests

📚 [bold]MORE HELP[/bold]
  tc --help                   # This help
  tc <command> --help         # Command-specific help
  tc diagnostics              # System health check

[dim]Just start typing what you want to do - term-coder will understand![/dim]
    """
    
    console.print(help_text)


if __name__ == "__main__":
    main()