from __future__ import annotations

import asyncio
import sys
from typing import Dict, List, Optional, Any
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.live import Live
from rich.spinner import Spinner
from rich.markdown import Markdown
from rich.syntax import Syntax

from .natural_interface import NaturalLanguageInterface
from .config import Config
from .session import ChatSession
from .errors import handle_error, ErrorContext


class InteractiveTerminal:
    """Interactive terminal interface with natural language processing."""
    
    def __init__(self, config: Config):
        self.config = config
        self.console = Console()
        self.natural_interface = NaturalLanguageInterface(config, self.console)
        self.session = ChatSession("interactive")
        self.running = True
        
        # Session state
        self.context_files = []
        self.last_action = None
        self.conversation_history = []
    
    async def start(self):
        """Start the interactive terminal session."""
        self._show_welcome()
        
        try:
            while self.running:
                await self._process_input_cycle()
        except KeyboardInterrupt:
            self._show_goodbye()
        except Exception as e:
            context = ErrorContext(command="interactive_terminal")
            handle_error(e, context)
    
    def _show_welcome(self):
        """Show welcome message and instructions."""
        from .branding import show_welcome_screen, show_tips_and_tricks
        
        # Show the awesome welcome screen
        show_welcome_screen(self.console)
        
        # Show a helpful tip
        show_tips_and_tricks(self.console)
    
    async def _process_input_cycle(self):
        """Process one input cycle."""
        try:
            # Get user input
            user_input = self._get_user_input()
            
            if not user_input.strip():
                return
            
            # Handle special commands
            if await self._handle_special_commands(user_input):
                return
            
            # Add to conversation history
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # Check for easter eggs first
            from .branding import show_easter_eggs, get_random_comment
            if show_easter_eggs(self.console, user_input):
                return
            
            # Show witty thinking indicator
            thinking_comment = get_random_comment("thinking")
            with Live(Spinner("dots", text=thinking_comment), console=self.console, refresh_per_second=10):
                # Process with natural language interface
                result = self.natural_interface.process_natural_input(
                    user_input, 
                    session_context=self._get_session_context()
                )
            
            # Display result
            await self._display_result(result, user_input)
            
            # Update session state
            self._update_session_state(result)
            
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Use 'exit' to quit gracefully[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def _get_user_input(self) -> str:
        """Get user input with a nice prompt."""
        # Show context indicator if we have context files
        context_indicator = ""
        if self.context_files:
            file_count = len(self.context_files)
            context_indicator = f"[dim]({file_count} files in context)[/dim] "
        
        prompt_text = f"{context_indicator}[bold cyan]You:[/bold cyan] "
        
        try:
            return Prompt.ask(prompt_text, console=self.console, default="")
        except (EOFError, KeyboardInterrupt):
            return "exit"
    
    async def _handle_special_commands(self, user_input: str) -> bool:
        """Handle special commands. Returns True if handled."""
        command = user_input.strip().lower()
        
        if command in ["exit", "quit", "bye"]:
            self.running = False
            self._show_goodbye()
            return True
        
        elif command == "help":
            self._show_help()
            return True
        
        elif command == "clear":
            self.console.clear()
            self._show_welcome()
            return True
        
        elif command == "status":
            self._show_status()
            return True
        
        elif command.startswith("context"):
            await self._handle_context_command(command)
            return True
        
        return False
    
    async def _display_result(self, result: Dict[str, Any], user_input: str):
        """Display the result of processing user input."""
        if not result.get("success"):
            self.console.print(f"[red]❌ {result.get('error', 'Unknown error')}[/red]")
            return
        
        intent = result.get("intent")
        action_result = result.get("result", {})
        action = action_result.get("action", "unknown")
        
        # Show what we understood
        if intent:
            self.console.print(f"[dim]🎯 Action: {action}[/dim]")
        
        # Display based on action type
        if action == "search":
            await self._display_search_result(action_result)
        
        elif action == "debug":
            await self._display_debug_result(action_result)
        
        elif action == "fix":
            await self._display_fix_result(action_result)
        
        elif action == "explain":
            await self._display_explain_result(action_result)
        
        elif action == "edit":
            await self._display_edit_result(action_result)
        
        elif action == "chat":
            await self._display_chat_result(action_result)
        
        else:
            # Generic display
            message = action_result.get("message", "Action completed")
            self.console.print(f"[green]✅ {message}[/green]")
            
            if "suggestions" in action_result:
                self._display_suggestions(action_result["suggestions"])
    
    async def _display_search_result(self, result: Dict[str, Any]):
        """Display search results."""
        results = result.get("results", [])
        query = result.get("query", "")
        
        if not results:
            self.console.print(f"[yellow]🔍 No results found for '{query}'[/yellow]")
            return
        
        self.console.print(f"[green]🔍 Found {len(results)} results for '{query}':[/green]")
        self.console.print()
        
        for i, item in enumerate(results[:5], 1):  # Show top 5
            file_path = item["file"]
            score = item.get("score", 0)
            preview = item.get("preview", "")
            
            # File header
            self.console.print(f"[bold]{i}. {file_path}[/bold] [dim](score: {score:.3f})[/dim]")
            
            # Preview
            if preview:
                syntax = Syntax(preview, "python", theme="monokai", line_numbers=False)
                self.console.print(Panel(syntax, padding=(0, 1), border_style="dim"))
            
            self.console.print()
    
    async def _display_debug_result(self, result: Dict[str, Any]):
        """Display debug results."""
        error_locations = result.get("error_locations", [])
        analysis = result.get("analysis", "")
        
        if not error_locations:
            self.console.print("[yellow]🐛 No obvious error patterns found[/yellow]")
            self._display_suggestions(result.get("suggestions", []))
            return
        
        self.console.print(f"[red]🐛 Found {len(error_locations)} potential error locations:[/red]")
        self.console.print()
        
        for i, location in enumerate(error_locations[:5], 1):
            file_path = location["file"]
            score = location.get("score", 0)
            self.console.print(f"[bold]{i}. {file_path}[/bold] [dim](relevance: {score:.3f})[/dim]")
        
        if analysis:
            self.console.print()
            self.console.print(Panel(analysis, title="🔍 Analysis", border_style="yellow"))
    
    async def _display_fix_result(self, result: Dict[str, Any]):
        """Display fix results."""
        proposals = result.get("proposals", [])
        
        if not proposals:
            self.console.print("[yellow]🔧 No fix proposals generated[/yellow]")
            self._display_suggestions(result.get("suggestions", []))
            return
        
        self.console.print(f"[green]🔧 Generated {len(proposals)} fix proposals:[/green]")
        self.console.print()
        
        for i, proposal in enumerate(proposals, 1):
            file_path = proposal.get("file", "unknown")
            description = proposal.get("description", "No description")
            
            self.console.print(f"[bold]{i}. {file_path}[/bold]")
            self.console.print(f"   {description}")
            self.console.print()
        
        self.console.print("[dim]💡 Use 'tc diff' to see proposed changes and 'tc apply' to apply them[/dim]")
    
    async def _display_explain_result(self, result: Dict[str, Any]):
        """Display explanation results."""
        explanation = result.get("explanation", "")
        context_files = result.get("context_files", [])
        
        if not explanation:
            self.console.print("[yellow]📖 No explanation generated[/yellow]")
            return
        
        # Show context files if any
        if context_files:
            files_text = ", ".join(context_files[:3])
            if len(context_files) > 3:
                files_text += f" and {len(context_files) - 3} more"
            self.console.print(f"[dim]📁 Based on: {files_text}[/dim]")
            self.console.print()
        
        # Show explanation
        explanation_panel = Panel(
            Markdown(explanation),
            title="📖 Explanation",
            border_style="blue",
            padding=(1, 2)
        )
        self.console.print(explanation_panel)
    
    async def _display_edit_result(self, result: Dict[str, Any]):
        """Display edit results."""
        proposal = result.get("proposal")
        
        if not proposal:
            self.console.print("[yellow]✏️ No edit proposal generated[/yellow]")
            return
        
        files = proposal.get("files", [])
        summary = proposal.get("summary", "")
        
        self.console.print(f"[green]✏️ {summary}[/green]")
        
        if files:
            self.console.print(f"[dim]📁 Files to be modified: {', '.join(files)}[/dim]")
        
        self.console.print()
        self.console.print("[dim]💡 Use 'tc diff' to review changes and 'tc apply' to apply them[/dim]")
    
    async def _display_chat_result(self, result: Dict[str, Any]):
        """Display chat results."""
        response = result.get("response", "")
        context_files = result.get("context_files", [])
        
        # Show context files if any
        if context_files:
            files_text = ", ".join(context_files[:3])
            if len(context_files) > 3:
                files_text += f" and {len(context_files) - 3} more"
            self.console.print(f"[dim]📁 Context: {files_text}[/dim]")
            self.console.print()
        
        # Show AI response
        self.console.print("[bold magenta]🤖 AI:[/bold magenta]")
        
        # Try to render as markdown if it looks like markdown
        if any(marker in response for marker in ["```", "##", "**", "*", "`"]):
            self.console.print(Markdown(response))
        else:
            self.console.print(response)
        
        # Add to conversation history
        self.conversation_history.append({"role": "assistant", "content": response})
    
    def _display_suggestions(self, suggestions: List[str]):
        """Display suggestions to the user."""
        if not suggestions:
            return
        
        self.console.print()
        self.console.print("[bold]💡 Suggestions:[/bold]")
        for suggestion in suggestions:
            self.console.print(f"  • {suggestion}")
    
    def _show_help(self):
        """Show help information."""
        help_text = """
# Term-Coder Interactive Help

## Natural Language Commands

You can speak naturally! Here are some examples:

**Debugging & Fixing:**
- "Debug for errors"
- "Find bugs in the authentication system"
- "Fix the login issue"
- "What's wrong with the database connection?"

**Code Understanding:**
- "Explain how the user registration works"
- "What does the main.py file do?"
- "Show me the authentication flow"
- "How is data validation handled?"

**Code Modification:**
- "Add error handling to the payment processing"
- "Implement logging in the user service"
- "Add input validation to the login form"
- "Refactor the database queries"

**Search & Analysis:**
- "Find all database queries"
- "Search for TODO comments"
- "Show me the API endpoints"
- "Where is the password hashing done?"

**Testing & Review:**
- "Run the tests"
- "Review my recent changes"
- "Check code quality"
- "Generate tests for the user model"

## Special Commands

- `exit` or `quit` - Leave interactive mode
- `help` - Show this help
- `clear` - Clear the screen
- `status` - Show session status
- `context` - Manage context files

## Tips

- Be specific about what you want to do
- Mention file names when relevant
- Ask follow-up questions
- Use "explain" when you need understanding
- Use "fix" when you want changes made
        """
        
        panel = Panel(
            Markdown(help_text),
            title="🆘 Help",
            border_style="green",
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def _show_status(self):
        """Show current session status."""
        status_info = []
        
        # Context files
        if self.context_files:
            status_info.append(f"📁 Context files: {len(self.context_files)}")
            for file in self.context_files[:3]:
                status_info.append(f"   • {file}")
            if len(self.context_files) > 3:
                status_info.append(f"   • ... and {len(self.context_files) - 3} more")
        else:
            status_info.append("📁 No context files")
        
        # Last action
        if self.last_action:
            status_info.append(f"🎯 Last action: {self.last_action}")
        
        # Conversation length
        status_info.append(f"💬 Conversation: {len(self.conversation_history)} messages")
        
        # Configuration
        model = self.config.get("llm.default_model", "unknown")
        status_info.append(f"🤖 Model: {model}")
        
        offline = self.config.get("privacy.offline_mode", False)
        status_info.append(f"🔒 Offline mode: {'Yes' if offline else 'No'}")
        
        status_text = "\n".join(status_info)
        
        panel = Panel(
            status_text,
            title="📊 Session Status",
            border_style="blue",
            padding=(1, 2)
        )
        self.console.print(panel)
    
    async def _handle_context_command(self, command: str):
        """Handle context management commands."""
        if command == "context":
            self._show_status()
        elif command == "context clear":
            self.context_files = []
            self.console.print("[green]✅ Context cleared[/green]")
        else:
            self.console.print("[yellow]Available context commands: 'context', 'context clear'[/yellow]")
    
    def _get_session_context(self) -> Dict[str, Any]:
        """Get current session context."""
        return {
            "context_files": self.context_files,
            "last_action": self.last_action,
            "conversation_history": self.conversation_history[-5:],  # Last 5 messages
        }
    
    def _update_session_state(self, result: Dict[str, Any]):
        """Update session state based on result."""
        if result.get("success"):
            action_result = result.get("result", {})
            self.last_action = action_result.get("action")
            
            # Update context files if relevant
            context_files = action_result.get("context_files", [])
            if context_files:
                # Add new context files, avoiding duplicates
                for file in context_files:
                    if file not in self.context_files:
                        self.context_files.append(file)
                
                # Keep only the most recent 10 context files
                self.context_files = self.context_files[-10:]
    
    def _show_goodbye(self):
        """Show goodbye message."""
        from .branding import get_compact_logo, show_motivational_message
        
        # Show compact logo
        logo = Text(get_compact_logo(), style="bold cyan")
        self.console.print(Align.center(logo))
        
        goodbye_text = Text.assemble(
            Text("Thanks for coding with ", style="dim"),
            Text("Term-Coder", style="bold cyan"),
            Text("! 👋\n\n", style="dim"),
            Text("🎉 Session saved successfully!\n", style="green"),
            Text("💾 History: ", style="dim"), Text(".term-coder/sessions/\n", style="cyan"),
            Text("🚀 Resume anytime: ", style="dim"), Text("tc\n", style="yellow"),
            Text("⚡ Quick commands: ", style="dim"), Text("tc \"your request\"\n\n", style="yellow"),
            Text("Keep building amazing things! 🌟", style="bold magenta")
        )
        
        panel = Panel(
            Align.center(goodbye_text),
            title="👋 See You Soon!",
            border_style="magenta",
            padding=(1, 2)
        )
        self.console.print(panel)
        
        # Show a motivational message
        show_motivational_message(self.console)


async def start_interactive_mode(config: Config):
    """Start the interactive terminal mode."""
    terminal = InteractiveTerminal(config)
    await terminal.start()