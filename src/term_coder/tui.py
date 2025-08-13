from __future__ import annotations

import curses
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple
from pathlib import Path
import json
from datetime import datetime

from .config import Config
from .llm import LLMOrchestrator
from .context import ContextEngine
from .prompts import render_chat_prompt
from .session import ChatSession
from .security import create_privacy_manager
from .audit import create_audit_logger


@dataclass
class UITheme:
    """Color theme for the TUI."""
    primary: int = curses.COLOR_CYAN
    secondary: int = curses.COLOR_MAGENTA
    success: int = curses.COLOR_GREEN
    warning: int = curses.COLOR_YELLOW
    error: int = curses.COLOR_RED
    info: int = curses.COLOR_BLUE
    text: int = curses.COLOR_WHITE
    background: int = curses.COLOR_BLACK


@dataclass
class Pane:
    """Represents a UI pane with content and scrolling."""
    title: str
    content: List[str]
    scroll_pos: int = 0
    max_lines: int = 100
    auto_scroll: bool = True
    
    def add_line(self, line: str) -> None:
        """Add a line to the pane content."""
        self.content.append(line)
        if len(self.content) > self.max_lines:
            self.content.pop(0)
        if self.auto_scroll:
            self.scroll_pos = max(0, len(self.content) - 1)
    
    def scroll_up(self, lines: int = 1) -> None:
        """Scroll up by specified lines."""
        self.scroll_pos = max(0, self.scroll_pos - lines)
        self.auto_scroll = False
    
    def scroll_down(self, lines: int = 1) -> None:
        """Scroll down by specified lines."""
        self.scroll_pos = min(len(self.content) - 1, self.scroll_pos + lines)
        if self.scroll_pos >= len(self.content) - 1:
            self.auto_scroll = True
    
    def scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the pane."""
        self.scroll_pos = max(0, len(self.content) - 1)
        self.auto_scroll = True


class ProgressIndicator:
    """Progress indicator for long-running operations."""
    
    def __init__(self, total: Optional[int] = None, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = time.time()
        self.is_indeterminate = total is None
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.spinner_pos = 0
    
    def update(self, increment: int = 1) -> None:
        """Update progress by increment."""
        if not self.is_indeterminate:
            self.current = min(self.total, self.current + increment)
        self.spinner_pos = (self.spinner_pos + 1) % len(self.spinner_chars)
    
    def get_display(self, width: int = 50) -> str:
        """Get progress display string."""
        elapsed = time.time() - self.start_time
        
        if self.is_indeterminate:
            spinner = self.spinner_chars[self.spinner_pos]
            return f"{spinner} {self.description} ({elapsed:.1f}s)"
        
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        filled = int((width * self.current) / self.total) if self.total > 0 else 0
        bar = "█" * filled + "░" * (width - filled)
        
        return f"{self.description} [{bar}] {percentage:.1f}% ({elapsed:.1f}s)"
    
    def is_complete(self) -> bool:
        """Check if progress is complete."""
        return not self.is_indeterminate and self.current >= self.total


class TUIApplication:
    """Main TUI application class."""
    
    def __init__(self, config: Config):
        self.config = config
        self.stdscr = None
        self.theme = UITheme()
        self.running = False
        self.current_mode = "chat"  # chat, search, files, help
        
        # UI state
        self.input_buffer = ""
        self.input_history = []
        self.history_pos = -1
        self.cursor_pos = 0
        
        # Panes
        self.chat_pane = Pane("Chat", [])
        self.output_pane = Pane("Output", [])
        self.files_pane = Pane("Files", [])
        self.status_pane = Pane("Status", [])
        
        # Progress tracking
        self.current_progress: Optional[ProgressIndicator] = None
        self.progress_thread: Optional[threading.Thread] = None
        
        # Components
        self.privacy_manager = create_privacy_manager(Path(".term-coder"))
        self.audit_logger = create_audit_logger(Path(".term-coder"), self.privacy_manager)
        self.orchestrator = LLMOrchestrator(
            offline=bool(config.get("privacy.offline", False)),
            privacy_manager=self.privacy_manager,
            audit_logger=self.audit_logger
        )
        self.context_engine = ContextEngine(config)
        self.chat_session = ChatSession("tui_session")
        self.chat_session.load()
        
        # Key bindings
        self.key_bindings = {
            # Mode switching
            ord('\t'): self.switch_mode,
            curses.KEY_F1: lambda: self.set_mode("help"),
            curses.KEY_F2: lambda: self.set_mode("chat"),
            curses.KEY_F3: lambda: self.set_mode("search"),
            curses.KEY_F4: lambda: self.set_mode("files"),
            
            # Navigation
            curses.KEY_UP: self.history_up,
            curses.KEY_DOWN: self.history_down,
            curses.KEY_LEFT: self.cursor_left,
            curses.KEY_RIGHT: self.cursor_right,
            curses.KEY_HOME: self.cursor_home,
            curses.KEY_END: self.cursor_end,
            curses.KEY_PPAGE: self.scroll_up,  # Page Up
            curses.KEY_NPAGE: self.scroll_down,  # Page Down
            
            # Editing
            curses.KEY_BACKSPACE: self.backspace,
            127: self.backspace,  # DEL key
            8: self.backspace,    # Ctrl+H
            curses.KEY_DC: self.delete_char,  # Delete key
            
            # Input
            ord('\n'): self.submit_input,
            ord('\r'): self.submit_input,
            
            # Control keys
            27: self.handle_escape,  # ESC key
            ord('\x03'): self.handle_interrupt,  # Ctrl+C
            ord('\x04'): self.handle_eof,  # Ctrl+D
            ord('\x0c'): self.refresh_screen,  # Ctrl+L
            ord('\x17'): self.delete_word,  # Ctrl+W
            ord('\x15'): self.clear_line,  # Ctrl+U
            ord('\x01'): self.cursor_home,  # Ctrl+A
            ord('\x05'): self.cursor_end,  # Ctrl+E
            
            # Search and navigation in panes
            ord('/'): self.start_search,  # Start search in current pane
            ord('n'): self.next_search_result,  # Next search result
            ord('N'): self.prev_search_result,  # Previous search result
            ord('g'): self.goto_top,  # Go to top of current pane
            ord('G'): self.goto_bottom,  # Go to bottom of current pane
        }
        
        # Search state
        self.search_query = ""
        self.search_results = []
        self.search_index = -1
        self.in_search_mode = False
    
    def init_colors(self) -> None:
        """Initialize color pairs for the TUI."""
        if not curses.has_colors():
            return
        
        curses.start_color()
        curses.use_default_colors()
        
        # Define color pairs
        curses.init_pair(1, self.theme.primary, -1)      # Primary text
        curses.init_pair(2, self.theme.secondary, -1)    # Secondary text
        curses.init_pair(3, self.theme.success, -1)      # Success messages
        curses.init_pair(4, self.theme.warning, -1)      # Warning messages
        curses.init_pair(5, self.theme.error, -1)        # Error messages
        curses.init_pair(6, self.theme.info, -1)         # Info messages
        curses.init_pair(7, self.theme.text, -1)         # Normal text
        curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Inverted
    
    def run(self, stdscr) -> None:
        """Main TUI loop."""
        self.stdscr = stdscr
        self.running = True
        
        # Initialize
        curses.curs_set(1)  # Show cursor
        self.init_colors()
        self.stdscr.timeout(100)  # Non-blocking input with 100ms timeout
        
        # Initial status
        self.status_pane.add_line("Term Coder TUI - Press F1 for help, Tab to switch modes")
        self.status_pane.add_line(f"Current mode: {self.current_mode}")
        
        # Log TUI start
        self.audit_logger.log_event("tui", "start", details={"mode": self.current_mode})
        
        try:
            while self.running:
                self.draw_screen()
                self.handle_input()
                self.update_progress()
                time.sleep(0.01)  # Small delay to prevent excessive CPU usage
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()
    
    def draw_screen(self) -> None:
        """Draw the entire screen."""
        if not self.stdscr:
            return
        
        height, width = self.stdscr.getmaxyx()
        self.stdscr.clear()
        
        # Calculate pane dimensions
        status_height = 3
        input_height = 3
        content_height = height - status_height - input_height - 2
        
        # Draw title bar
        title = f"Term Coder TUI - Mode: {self.current_mode.upper()}"
        self.stdscr.addstr(0, 0, title.center(width), curses.color_pair(1) | curses.A_BOLD)
        
        # Draw main content area
        if self.current_mode == "chat":
            self.draw_chat_pane(1, 0, content_height, width)
        elif self.current_mode == "search":
            self.draw_search_pane(1, 0, content_height, width)
        elif self.current_mode == "files":
            self.draw_files_pane(1, 0, content_height, width)
        elif self.current_mode == "help":
            self.draw_help_pane(1, 0, content_height, width)
        
        # Draw status area
        status_y = height - status_height - input_height
        self.draw_status_area(status_y, 0, status_height, width)
        
        # Draw input area
        input_y = height - input_height
        self.draw_input_area(input_y, 0, input_height, width)
        
        # Draw progress indicator if active
        if self.current_progress:
            progress_text = self.current_progress.get_display(width - 4)
            self.stdscr.addstr(height - 1, 2, progress_text, curses.color_pair(6))
        
        self.stdscr.refresh()
    
    def draw_chat_pane(self, y: int, x: int, height: int, width: int) -> None:
        """Draw the chat pane."""
        # Draw border
        self.stdscr.addstr(y, x, "┌" + "─" * (width - 2) + "┐")
        for i in range(1, height - 1):
            self.stdscr.addstr(y + i, x, "│")
            self.stdscr.addstr(y + i, x + width - 1, "│")
        self.stdscr.addstr(y + height - 1, x, "└" + "─" * (width - 2) + "┘")
        
        # Draw title
        title = " Chat History "
        title_x = x + (width - len(title)) // 2
        self.stdscr.addstr(y, title_x, title, curses.color_pair(1) | curses.A_BOLD)
        
        # Draw chat content
        content_height = height - 2
        content_width = width - 2
        visible_lines = self.get_visible_lines(self.chat_pane, content_height)
        
        for i, line in enumerate(visible_lines):
            if i >= content_height:
                break
            
            # Truncate line if too long
            display_line = line[:content_width] if len(line) > content_width else line
            
            # Color coding for different message types
            color = curses.color_pair(7)  # Default
            if line.startswith("You:"):
                color = curses.color_pair(1)  # Primary for user
            elif line.startswith("AI:"):
                color = curses.color_pair(2)  # Secondary for AI
            elif line.startswith("System:"):
                color = curses.color_pair(6)  # Info for system
            
            try:
                self.stdscr.addstr(y + 1 + i, x + 1, display_line, color)
            except curses.error:
                pass  # Ignore if we can't write to that position
    
    def draw_search_pane(self, y: int, x: int, height: int, width: int) -> None:
        """Draw the search pane."""
        # Similar to chat pane but for search results
        self.stdscr.addstr(y, x, "┌" + "─" * (width - 2) + "┐")
        for i in range(1, height - 1):
            self.stdscr.addstr(y + i, x, "│")
            self.stdscr.addstr(y + i, x + width - 1, "│")
        self.stdscr.addstr(y + height - 1, x, "└" + "─" * (width - 2) + "┘")
        
        title = " Search Results "
        title_x = x + (width - len(title)) // 2
        self.stdscr.addstr(y, title_x, title, curses.color_pair(1) | curses.A_BOLD)
        
        # Show search instructions
        instructions = [
            "Enter search query and press Enter",
            "Use 'semantic:query' for semantic search",
            "Use 'files:pattern' to search filenames",
            "",
            "Recent searches will appear here..."
        ]
        
        for i, line in enumerate(instructions):
            if i >= height - 2:
                break
            try:
                self.stdscr.addstr(y + 1 + i, x + 1, line, curses.color_pair(7))
            except curses.error:
                pass
    
    def draw_files_pane(self, y: int, x: int, height: int, width: int) -> None:
        """Draw the files pane."""
        self.stdscr.addstr(y, x, "┌" + "─" * (width - 2) + "┐")
        for i in range(1, height - 1):
            self.stdscr.addstr(y + i, x, "│")
            self.stdscr.addstr(y + i, x + width - 1, "│")
        self.stdscr.addstr(y + height - 1, x, "└" + "─" * (width - 2) + "┘")
        
        title = " File Browser "
        title_x = x + (width - len(title)) // 2
        self.stdscr.addstr(y, title_x, title, curses.color_pair(1) | curses.A_BOLD)
        
        # Show current directory files
        try:
            current_dir = Path.cwd()
            files = list(current_dir.iterdir())[:height - 3]  # Limit to visible area
            
            for i, file_path in enumerate(files):
                if i >= height - 2:
                    break
                
                file_name = file_path.name
                if len(file_name) > width - 4:
                    file_name = file_name[:width - 7] + "..."
                
                color = curses.color_pair(6) if file_path.is_dir() else curses.color_pair(7)
                prefix = "📁 " if file_path.is_dir() else "📄 "
                
                try:
                    self.stdscr.addstr(y + 1 + i, x + 1, f"{prefix}{file_name}", color)
                except curses.error:
                    pass
        except Exception:
            self.stdscr.addstr(y + 1, x + 1, "Error reading directory", curses.color_pair(5))
    
    def draw_help_pane(self, y: int, x: int, height: int, width: int) -> None:
        """Draw the help pane."""
        self.stdscr.addstr(y, x, "┌" + "─" * (width - 2) + "┐")
        for i in range(1, height - 1):
            self.stdscr.addstr(y + i, x, "│")
            self.stdscr.addstr(y + i, x + width - 1, "│")
        self.stdscr.addstr(y + height - 1, x, "└" + "─" * (width - 2) + "┘")
        
        title = " Help & Keyboard Shortcuts "
        title_x = x + (width - len(title)) // 2
        self.stdscr.addstr(y, title_x, title, curses.color_pair(1) | curses.A_BOLD)
        
        help_text = [
            "KEYBOARD SHORTCUTS:",
            "",
            "F1 - Help (this screen)",
            "F2 - Chat mode",
            "F3 - Search mode", 
            "F4 - File browser",
            "Tab - Switch between modes",
            "",
            "NAVIGATION:",
            "↑/↓ - Command history",
            "←/→ - Move cursor",
            "Home/End - Start/end of line",
            "Backspace - Delete character",
            "Enter - Submit command",
            "Esc - Cancel/exit",
            "",
            "CHAT COMMANDS:",
            "Type your message and press Enter",
            "Use @filename to include files",
            "Use /help for more commands",
        ]
        
        for i, line in enumerate(help_text):
            if i >= height - 2:
                break
            
            color = curses.color_pair(1) if line.endswith(":") else curses.color_pair(7)
            try:
                self.stdscr.addstr(y + 1 + i, x + 1, line, color)
            except curses.error:
                pass
    
    def draw_status_area(self, y: int, x: int, height: int, width: int) -> None:
        """Draw the status area."""
        # Draw horizontal line
        self.stdscr.addstr(y, x, "─" * width)
        
        # Show current status
        status_lines = self.get_visible_lines(self.status_pane, height - 1)
        for i, line in enumerate(status_lines):
            if i >= height - 1:
                break
            try:
                self.stdscr.addstr(y + 1 + i, x, line[:width], curses.color_pair(6))
            except curses.error:
                pass
    
    def draw_input_area(self, y: int, x: int, height: int, width: int) -> None:
        """Draw the input area."""
        # Draw horizontal line
        self.stdscr.addstr(y, x, "─" * width)
        
        # Draw prompt
        prompt = f"{self.current_mode}> "
        self.stdscr.addstr(y + 1, x, prompt, curses.color_pair(1) | curses.A_BOLD)
        
        # Draw input buffer
        input_x = x + len(prompt)
        input_width = width - len(prompt) - 1
        
        # Handle long input by scrolling
        display_buffer = self.input_buffer
        cursor_display_pos = self.cursor_pos
        
        if len(display_buffer) > input_width:
            # Scroll input to keep cursor visible
            if self.cursor_pos >= input_width:
                start_pos = self.cursor_pos - input_width + 1
                display_buffer = display_buffer[start_pos:]
                cursor_display_pos = input_width - 1
        
        self.stdscr.addstr(y + 1, input_x, display_buffer[:input_width], curses.color_pair(7))
        
        # Position cursor
        try:
            self.stdscr.move(y + 1, input_x + cursor_display_pos)
        except curses.error:
            pass
    
    def get_visible_lines(self, pane: Pane, max_lines: int) -> List[str]:
        """Get visible lines for a pane based on scroll position."""
        if not pane.content:
            return []
        
        start_idx = max(0, len(pane.content) - max_lines)
        if not pane.auto_scroll:
            start_idx = max(0, pane.scroll_pos - max_lines + 1)
        
        return pane.content[start_idx:start_idx + max_lines]
    
    def handle_input(self) -> None:
        """Handle keyboard input."""
        if not self.stdscr:
            return
        
        try:
            key = self.stdscr.getch()
            if key == -1:  # No input
                return
            
            # Handle special keys
            if key in self.key_bindings:
                self.key_bindings[key]()
            elif 32 <= key <= 126:  # Printable characters
                self.insert_char(chr(key))
            
        except curses.error:
            pass
    
    def insert_char(self, char: str) -> None:
        """Insert a character at the cursor position."""
        self.input_buffer = (
            self.input_buffer[:self.cursor_pos] + 
            char + 
            self.input_buffer[self.cursor_pos:]
        )
        self.cursor_pos += 1
    
    def backspace(self) -> None:
        """Handle backspace key."""
        if self.cursor_pos > 0:
            self.input_buffer = (
                self.input_buffer[:self.cursor_pos - 1] + 
                self.input_buffer[self.cursor_pos:]
            )
            self.cursor_pos -= 1
    
    def cursor_left(self) -> None:
        """Move cursor left."""
        self.cursor_pos = max(0, self.cursor_pos - 1)
    
    def cursor_right(self) -> None:
        """Move cursor right."""
        self.cursor_pos = min(len(self.input_buffer), self.cursor_pos + 1)
    
    def cursor_home(self) -> None:
        """Move cursor to start of line."""
        self.cursor_pos = 0
    
    def cursor_end(self) -> None:
        """Move cursor to end of line."""
        self.cursor_pos = len(self.input_buffer)
    
    def history_up(self) -> None:
        """Navigate up in command history."""
        if self.input_history and self.history_pos < len(self.input_history) - 1:
            self.history_pos += 1
            self.input_buffer = self.input_history[-(self.history_pos + 1)]
            self.cursor_pos = len(self.input_buffer)
    
    def history_down(self) -> None:
        """Navigate down in command history."""
        if self.history_pos > 0:
            self.history_pos -= 1
            self.input_buffer = self.input_history[-(self.history_pos + 1)]
            self.cursor_pos = len(self.input_buffer)
        elif self.history_pos == 0:
            self.history_pos = -1
            self.input_buffer = ""
            self.cursor_pos = 0
    
    def submit_input(self) -> None:
        """Submit the current input."""
        if not self.input_buffer.strip():
            return
        
        # Add to history
        self.input_history.append(self.input_buffer)
        if len(self.input_history) > 100:  # Limit history size
            self.input_history.pop(0)
        self.history_pos = -1
        
        # Process input based on current mode
        if self.current_mode == "chat":
            self.handle_chat_input(self.input_buffer)
        elif self.current_mode == "search":
            self.handle_search_input(self.input_buffer)
        elif self.current_mode == "files":
            self.handle_files_input(self.input_buffer)
        
        # Clear input
        self.input_buffer = ""
        self.cursor_pos = 0
    
    def handle_chat_input(self, input_text: str) -> None:
        """Handle chat input."""
        # Add user message to chat pane
        self.chat_pane.add_line(f"You: {input_text}")
        
        # Handle special commands
        if input_text.startswith("/"):
            self.handle_chat_command(input_text)
            return
        
        # Start progress indicator
        self.current_progress = ProgressIndicator(description="Generating response")
        
        # Process in background thread
        def process_chat():
            try:
                # Select context
                ctx = self.context_engine.select_context(
                    query=input_text,
                    budget_tokens=int(self.config.get("retrieval.max_tokens", 8000))
                )
                
                # Render prompt
                rp = render_chat_prompt(
                    input_text, 
                    ctx, 
                    history=self.chat_session.history_pairs(limit_chars=4000)
                )
                
                # Save user message
                self.chat_session.append("user", input_text)
                
                # Stream response
                self.chat_pane.add_line("AI: ", )
                response_parts = []
                
                for chunk in self.orchestrator.stream(rp.user):
                    response_parts.append(chunk)
                    # Update the last line with accumulated response
                    full_response = "".join(response_parts)
                    if self.chat_pane.content:
                        self.chat_pane.content[-1] = f"AI: {full_response}"
                    
                    self.current_progress.update()
                
                # Save assistant message
                self.chat_session.append("assistant", "".join(response_parts))
                self.chat_session.save()
                
                # Update status
                self.status_pane.add_line(f"Response generated ({len(response_parts)} chunks)")
                
            except Exception as e:
                self.chat_pane.add_line(f"System: Error - {str(e)}")
                self.status_pane.add_line(f"Error: {str(e)}")
            finally:
                self.current_progress = None
        
        # Start background thread
        thread = threading.Thread(target=process_chat, daemon=True)
        thread.start()
    
    def handle_chat_command(self, command: str) -> None:
        """Handle special chat commands."""
        if command == "/help":
            self.chat_pane.add_line("System: Available commands:")
            self.chat_pane.add_line("System: /help - Show this help")
            self.chat_pane.add_line("System: /clear - Clear chat history")
            self.chat_pane.add_line("System: /save - Save chat session")
            self.chat_pane.add_line("System: /quit - Exit TUI")
        elif command == "/clear":
            self.chat_pane.content.clear()
            self.chat_session.clear()
            self.chat_pane.add_line("System: Chat history cleared")
        elif command == "/save":
            self.chat_session.save()
            self.chat_pane.add_line("System: Chat session saved")
        elif command == "/quit":
            self.running = False
        else:
            self.chat_pane.add_line(f"System: Unknown command: {command}")
    
    def handle_search_input(self, input_text: str) -> None:
        """Handle search input."""
        # TODO: Implement search functionality
        self.status_pane.add_line(f"Search: {input_text}")
    
    def handle_files_input(self, input_text: str) -> None:
        """Handle files input."""
        # TODO: Implement file operations
        self.status_pane.add_line(f"Files: {input_text}")
    
    def switch_mode(self) -> None:
        """Switch to the next mode."""
        modes = ["chat", "search", "files", "help"]
        current_idx = modes.index(self.current_mode)
        next_idx = (current_idx + 1) % len(modes)
        self.set_mode(modes[next_idx])
    
    def set_mode(self, mode: str) -> None:
        """Set the current mode."""
        if mode in ["chat", "search", "files", "help"]:
            self.current_mode = mode
            self.status_pane.add_line(f"Switched to {mode} mode")
            
            # Log mode change
            self.audit_logger.log_event("tui", "mode_change", details={"new_mode": mode})
    
    def handle_escape(self) -> None:
        """Handle escape key."""
        if self.current_progress:
            # Cancel current operation
            self.current_progress = None
            self.status_pane.add_line("Operation cancelled")
        else:
            # Exit TUI
            self.running = False
    
    def delete_char(self) -> None:
        """Delete character at cursor position."""
        if self.cursor_pos < len(self.input_buffer):
            self.input_buffer = (
                self.input_buffer[:self.cursor_pos] + 
                self.input_buffer[self.cursor_pos + 1:]
            )
    
    def delete_word(self) -> None:
        """Delete word before cursor (Ctrl+W)."""
        if self.cursor_pos == 0:
            return
        
        # Find start of current word
        pos = self.cursor_pos - 1
        while pos > 0 and self.input_buffer[pos].isspace():
            pos -= 1
        while pos > 0 and not self.input_buffer[pos - 1].isspace():
            pos -= 1
        
        # Delete from word start to cursor
        self.input_buffer = self.input_buffer[:pos] + self.input_buffer[self.cursor_pos:]
        self.cursor_pos = pos
    
    def clear_line(self) -> None:
        """Clear entire input line (Ctrl+U)."""
        self.input_buffer = ""
        self.cursor_pos = 0
    
    def scroll_up(self) -> None:
        """Scroll current pane up (Page Up)."""
        current_pane = self.get_current_pane()
        if current_pane:
            current_pane.scroll_up(5)  # Scroll 5 lines at a time
    
    def scroll_down(self) -> None:
        """Scroll current pane down (Page Down)."""
        current_pane = self.get_current_pane()
        if current_pane:
            current_pane.scroll_down(5)  # Scroll 5 lines at a time
    
    def goto_top(self) -> None:
        """Go to top of current pane."""
        current_pane = self.get_current_pane()
        if current_pane:
            current_pane.scroll_pos = 0
            current_pane.auto_scroll = False
    
    def goto_bottom(self) -> None:
        """Go to bottom of current pane."""
        current_pane = self.get_current_pane()
        if current_pane:
            current_pane.scroll_to_bottom()
    
    def get_current_pane(self) -> Optional[Pane]:
        """Get the current active pane based on mode."""
        if self.current_mode == "chat":
            return self.chat_pane
        elif self.current_mode == "search":
            return self.output_pane  # Use output pane for search results
        elif self.current_mode == "files":
            return self.files_pane
        return None
    
    def start_search(self) -> None:
        """Start search in current pane."""
        self.in_search_mode = True
        self.search_query = ""
        self.status_pane.add_line("Search mode: Type query and press Enter")
    
    def next_search_result(self) -> None:
        """Go to next search result."""
        if self.search_results and self.search_index < len(self.search_results) - 1:
            self.search_index += 1
            self.jump_to_search_result()
    
    def prev_search_result(self) -> None:
        """Go to previous search result."""
        if self.search_results and self.search_index > 0:
            self.search_index -= 1
            self.jump_to_search_result()
    
    def jump_to_search_result(self) -> None:
        """Jump to current search result."""
        if self.search_results and 0 <= self.search_index < len(self.search_results):
            line_num = self.search_results[self.search_index]
            current_pane = self.get_current_pane()
            if current_pane:
                current_pane.scroll_pos = line_num
                current_pane.auto_scroll = False
                self.status_pane.add_line(f"Search result {self.search_index + 1}/{len(self.search_results)}")
    
    def handle_interrupt(self) -> None:
        """Handle Ctrl+C interrupt."""
        if self.current_progress:
            self.current_progress = None
            self.status_pane.add_line("Operation interrupted")
        else:
            self.status_pane.add_line("Press Esc to exit")
    
    def handle_eof(self) -> None:
        """Handle Ctrl+D EOF."""
        if not self.input_buffer:
            self.running = False
        else:
            self.status_pane.add_line("Use Esc to exit or clear input first")
    
    def refresh_screen(self) -> None:
        """Refresh screen (Ctrl+L)."""
        if self.stdscr:
            self.stdscr.clear()
            self.stdscr.refresh()

    def update_progress(self) -> None:
        """Update progress indicators."""
        if self.current_progress and not self.current_progress.is_complete():
            self.current_progress.update(0)  # Just update spinner
    
    def cleanup(self) -> None:
        """Cleanup before exit."""
        if self.chat_session:
            self.chat_session.save()
        
        # Log TUI end
        self.audit_logger.log_event("tui", "end", details={"mode": self.current_mode})


def run_tui(config: Config) -> None:
    """Run the TUI application."""
    app = TUIApplication(config)
    try:
        curses.wrapper(app.run)
    except Exception as e:
        print(f"TUI Error: {e}")
        raise
            current_pane = self.get_current_pane()
            if current_pane:
                current_pane.scroll_pos = line_num
                current_pane.auto_scroll = False
                self.status_pane.add_line(f"Search result {self.search_index + 1}/{len(self.search_results)}")
    
    def handle_interrupt(self) -> None:
        """Handle Ctrl+C interrupt."""
        if self.current_progress:
            self.current_progress = None
            self.status_pane.add_line("Operation interrupted")
        else:
            self.status_pane.add_line("Press Esc to exit")
    
    def handle_eof(self) -> None:
        """Handle Ctrl+D EOF."""
        if not self.input_buffer:
            self.running = False
        else:
            self.status_pane.add_line("Use Esc to exit or clear input first")
    
    def refresh_screen(self) -> None:
        """Refresh screen (Ctrl+L)."""
        if self.stdscr:
            self.stdscr.clear()
            self.stdscr.refresh()

    def update_progress(self) -> None:
        """Update progress indicators."""
        if self.current_progress and not self.current_progress.is_complete():
            self.current_progress.update(0)  # Just update spinner
    
    def cleanup(self) -> None:
        """Cleanup before exit."""
        if self.chat_session:
            self.chat_session.save()
        
        # Log TUI end
        self.audit_logger.log_event("tui", "end", details={"mode": self.current_mode})


def run_tui(config: Config) -> None:
    """Run the TUI application."""
    app = TUIApplication(config)
    try:
        curses.wrapper(app.run)
    except Exception as e:
        print(f"TUI Error: {e}")
        raise