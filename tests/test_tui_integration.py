from __future__ import annotations

import curses
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

import pytest

from term_coder.config import Config
from term_coder.tui import TUIApplication, UITheme, Pane, ProgressIndicator


class TestProgressIndicator:
    """Test progress indicator functionality."""
    
    def test_progress_indicator_determinate(self):
        """Test determinate progress indicator."""
        progress = ProgressIndicator(total=100, description="Testing")
        
        assert progress.total == 100
        assert progress.current == 0
        assert progress.description == "Testing"
        assert not progress.is_indeterminate
        assert not progress.is_complete()
        
        # Update progress
        progress.update(25)
        assert progress.current == 25
        assert not progress.is_complete()
        
        # Complete progress
        progress.update(75)
        assert progress.current == 100
        assert progress.is_complete()
        
        # Test display
        display = progress.get_display(width=20)
        assert "Testing" in display
        assert "100.0%" in display
    
    def test_progress_indicator_indeterminate(self):
        """Test indeterminate progress indicator."""
        progress = ProgressIndicator(description="Loading")
        
        assert progress.total is None
        assert progress.is_indeterminate
        assert not progress.is_complete()
        
        # Update should advance spinner
        old_pos = progress.spinner_pos
        progress.update()
        assert progress.spinner_pos != old_pos
        
        # Display should show spinner
        display = progress.get_display()
        assert "Loading" in display
        assert any(char in display for char in progress.spinner_chars)


class TestPane:
    """Test pane functionality."""
    
    def test_pane_creation(self):
        """Test pane creation and basic properties."""
        pane = Pane("Test Pane", [])
        
        assert pane.title == "Test Pane"
        assert pane.content == []
        assert pane.scroll_pos == 0
        assert pane.max_lines == 100
        assert pane.auto_scroll == True
    
    def test_pane_add_line(self):
        """Test adding lines to pane."""
        pane = Pane("Test", [])
        
        pane.add_line("Line 1")
        pane.add_line("Line 2")
        pane.add_line("Line 3")
        
        assert len(pane.content) == 3
        assert pane.content[0] == "Line 1"
        assert pane.content[2] == "Line 3"
        assert pane.scroll_pos == 2  # Auto-scrolled to bottom
    
    def test_pane_max_lines_enforcement(self):
        """Test that pane enforces max lines limit."""
        pane = Pane("Test", [], max_lines=3)
        
        # Add more lines than max
        for i in range(5):
            pane.add_line(f"Line {i+1}")
        
        # Should only keep last 3 lines
        assert len(pane.content) == 3
        assert pane.content[0] == "Line 3"
        assert pane.content[1] == "Line 4"
        assert pane.content[2] == "Line 5"
    
    def test_pane_scrolling(self):
        """Test pane scrolling functionality."""
        pane = Pane("Test", [])
        
        # Add some content
        for i in range(10):
            pane.add_line(f"Line {i+1}")
        
        # Test scroll up
        pane.scroll_up(3)
        assert pane.scroll_pos == 6  # 9 - 3
        assert not pane.auto_scroll
        
        # Test scroll down
        pane.scroll_down(2)
        assert pane.scroll_pos == 8
        
        # Test scroll to bottom
        pane.scroll_to_bottom()
        assert pane.scroll_pos == 9
        assert pane.auto_scroll


class TestUITheme:
    """Test UI theme functionality."""
    
    def test_ui_theme_defaults(self):
        """Test UI theme default values."""
        theme = UITheme()
        
        assert theme.primary == curses.COLOR_CYAN
        assert theme.secondary == curses.COLOR_MAGENTA
        assert theme.success == curses.COLOR_GREEN
        assert theme.warning == curses.COLOR_YELLOW
        assert theme.error == curses.COLOR_RED
        assert theme.info == curses.COLOR_BLUE
        assert theme.text == curses.COLOR_WHITE
        assert theme.background == curses.COLOR_BLACK
    
    def test_ui_theme_custom(self):
        """Test custom UI theme."""
        theme = UITheme(
            primary=curses.COLOR_BLUE,
            secondary=curses.COLOR_GREEN,
            success=curses.COLOR_CYAN
        )
        
        assert theme.primary == curses.COLOR_BLUE
        assert theme.secondary == curses.COLOR_GREEN
        assert theme.success == curses.COLOR_CYAN
        # Other values should remain default
        assert theme.warning == curses.COLOR_YELLOW


class TestTUIApplication:
    """Test TUI application functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        
    def test_tui_application_initialization(self):
        """Test TUI application initialization."""
        app = TUIApplication(self.config)
        
        assert app.config == self.config
        assert app.current_mode == "chat"
        assert app.running == False
        assert app.input_buffer == ""
        assert app.cursor_pos == 0
        assert len(app.input_history) == 0
        
        # Check panes are created
        assert app.chat_pane.title == "Chat"
        assert app.output_pane.title == "Output"
        assert app.files_pane.title == "Files"
        assert app.status_pane.title == "Status"
    
    def test_tui_key_bindings(self):
        """Test TUI key bindings setup."""
        app = TUIApplication(self.config)
        
        # Check that key bindings are set up
        assert ord('\t') in app.key_bindings  # Tab key
        assert curses.KEY_F1 in app.key_bindings  # F1 key
        assert curses.KEY_UP in app.key_bindings  # Up arrow
        assert curses.KEY_DOWN in app.key_bindings  # Down arrow
        assert ord('\n') in app.key_bindings  # Enter key
        assert 27 in app.key_bindings  # Escape key
    
    def test_tui_input_handling(self):
        """Test TUI input handling."""
        app = TUIApplication(self.config)
        
        # Test character insertion
        app.insert_char('H')
        app.insert_char('i')
        assert app.input_buffer == "Hi"
        assert app.cursor_pos == 2
        
        # Test backspace
        app.backspace()
        assert app.input_buffer == "H"
        assert app.cursor_pos == 1
        
        # Test cursor movement
        app.insert_char('e')
        app.insert_char('l')
        app.insert_char('l')
        app.insert_char('o')
        assert app.input_buffer == "Hello"
        
        app.cursor_left()
        app.cursor_left()
        assert app.cursor_pos == 3
        
        app.cursor_right()
        assert app.cursor_pos == 4
        
        app.cursor_home()
        assert app.cursor_pos == 0
        
        app.cursor_end()
        assert app.cursor_pos == 5
    
    def test_tui_history_navigation(self):
        """Test TUI command history navigation."""
        app = TUIApplication(self.config)
        
        # Add some history
        app.input_history = ["command1", "command2", "command3"]
        
        # Navigate up in history
        app.history_up()
        assert app.input_buffer == "command3"
        assert app.history_pos == 0
        
        app.history_up()
        assert app.input_buffer == "command2"
        assert app.history_pos == 1
        
        app.history_up()
        assert app.input_buffer == "command1"
        assert app.history_pos == 2
        
        # Navigate down in history
        app.history_down()
        assert app.input_buffer == "command2"
        assert app.history_pos == 1
        
        app.history_down()
        assert app.input_buffer == "command3"
        assert app.history_pos == 0
        
        app.history_down()
        assert app.input_buffer == ""
        assert app.history_pos == -1
    
    def test_tui_mode_switching(self):
        """Test TUI mode switching."""
        app = TUIApplication(self.config)
        
        assert app.current_mode == "chat"
        
        # Switch modes
        app.switch_mode()
        assert app.current_mode == "search"
        
        app.switch_mode()
        assert app.current_mode == "files"
        
        app.switch_mode()
        assert app.current_mode == "help"
        
        app.switch_mode()
        assert app.current_mode == "chat"  # Should wrap around
        
        # Set specific mode
        app.set_mode("files")
        assert app.current_mode == "files"
    
    def test_tui_chat_commands(self):
        """Test TUI chat command handling."""
        app = TUIApplication(self.config)
        
        # Test help command
        app.handle_chat_command("/help")
        assert any("Available commands" in line for line in app.chat_pane.content)
        
        # Test clear command
        app.chat_pane.add_line("Test message")
        app.handle_chat_command("/clear")
        assert len(app.chat_pane.content) == 1  # Only the "cleared" message
        assert "cleared" in app.chat_pane.content[0].lower()
        
        # Test save command
        app.handle_chat_command("/save")
        assert any("saved" in line.lower() for line in app.chat_pane.content)
        
        # Test unknown command
        app.handle_chat_command("/unknown")
        assert any("Unknown command" in line for line in app.chat_pane.content)
    
    @patch('threading.Thread')
    def test_tui_chat_input_processing(self, mock_thread):
        """Test TUI chat input processing."""
        app = TUIApplication(self.config)
        
        # Mock the orchestrator to avoid actual LLM calls
        app.orchestrator = Mock()
        app.orchestrator.stream.return_value = iter(["Hello", " ", "world", "!"])
        
        # Handle chat input
        app.handle_chat_input("Test message")
        
        # Should add user message to chat pane
        assert any("You: Test message" in line for line in app.chat_pane.content)
        
        # Should start a background thread
        mock_thread.assert_called_once()
        thread_args = mock_thread.call_args
        assert thread_args[1]['daemon'] == True
    
    def test_tui_progress_indicator_integration(self):
        """Test TUI progress indicator integration."""
        app = TUIApplication(self.config)
        
        # Create progress indicator
        progress = ProgressIndicator(total=10, description="Testing")
        app.current_progress = progress
        
        # Update progress
        app.update_progress()
        
        # Progress should be updated
        assert progress.spinner_pos > 0 or progress.current > 0
    
    def test_tui_visible_lines_calculation(self):
        """Test TUI visible lines calculation."""
        app = TUIApplication(self.config)
        
        # Add content to chat pane
        for i in range(20):
            app.chat_pane.add_line(f"Message {i+1}")
        
        # Get visible lines for different heights
        visible_5 = app.get_visible_lines(app.chat_pane, 5)
        assert len(visible_5) == 5
        assert visible_5[-1] == "Message 20"  # Should show last 5 messages
        
        visible_10 = app.get_visible_lines(app.chat_pane, 10)
        assert len(visible_10) == 10
        assert visible_10[-1] == "Message 20"
        assert visible_10[0] == "Message 11"
        
        # Test with scrolling
        app.chat_pane.scroll_up(5)
        visible_scrolled = app.get_visible_lines(app.chat_pane, 5)
        assert len(visible_scrolled) == 5
        # Should show earlier messages due to scrolling


class TestTUIIntegration:
    """Test TUI integration with other components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
    
    @patch('curses.wrapper')
    def test_tui_run_function(self, mock_wrapper):
        """Test TUI run function."""
        from term_coder.tui import run_tui
        
        # Should call curses.wrapper with app.run
        run_tui(self.config)
        mock_wrapper.assert_called_once()
    
    def test_tui_with_privacy_and_audit(self):
        """Test TUI integration with privacy and audit systems."""
        app = TUIApplication(self.config)
        
        # Should have privacy manager and audit logger
        assert app.privacy_manager is not None
        assert app.audit_logger is not None
        
        # Should have orchestrator with privacy integration
        assert app.orchestrator.privacy_manager is not None
        assert app.orchestrator.audit_logger is not None
    
    def test_tui_session_management(self):
        """Test TUI chat session management."""
        app = TUIApplication(self.config)
        
        # Should have chat session
        assert app.chat_session is not None
        assert app.chat_session.session_name == "tui_session"
        
        # Test session operations
        app.chat_session.append("user", "Test message")
        app.chat_session.append("assistant", "Test response")
        
        history = app.chat_session.history_pairs()
        assert len(history) == 1
        assert history[0][0] == "Test message"
        assert history[0][1] == "Test response"
    
    def test_tui_context_engine_integration(self):
        """Test TUI integration with context engine."""
        app = TUIApplication(self.config)
        
        # Should have context engine
        assert app.context_engine is not None
        assert app.context_engine.config == self.config
    
    def test_tui_cleanup_on_exit(self):
        """Test TUI cleanup on exit."""
        app = TUIApplication(self.config)
        
        # Mock chat session save
        app.chat_session.save = Mock()
        
        # Call cleanup
        app.cleanup()
        
        # Should save chat session
        app.chat_session.save.assert_called_once()
    
    def test_tui_error_handling(self):
        """Test TUI error handling."""
        app = TUIApplication(self.config)
        
        # Test escape key handling
        app.current_progress = ProgressIndicator(description="Test")
        app.handle_escape()
        assert app.current_progress is None
        
        # Test escape when no progress
        app.handle_escape()
        assert not app.running
    
    def test_tui_audit_logging(self):
        """Test TUI audit logging."""
        app = TUIApplication(self.config)
        
        # Mock audit logger
        app.audit_logger = Mock()
        
        # Test mode change logging
        app.set_mode("search")
        app.audit_logger.log_event.assert_called_with(
            "tui", "mode_change", details={"new_mode": "search"}
        )
    
    def test_tui_with_different_themes(self):
        """Test TUI with different themes."""
        app = TUIApplication(self.config)
        
        # Test custom theme
        custom_theme = UITheme(
            primary=curses.COLOR_BLUE,
            secondary=curses.COLOR_GREEN
        )
        app.theme = custom_theme
        
        assert app.theme.primary == curses.COLOR_BLUE
        assert app.theme.secondary == curses.COLOR_GREEN
    
    def test_tui_long_input_handling(self):
        """Test TUI handling of long input."""
        app = TUIApplication(self.config)
        
        # Create very long input
        long_input = "a" * 200
        for char in long_input:
            app.insert_char(char)
        
        assert app.input_buffer == long_input
        assert app.cursor_pos == 200
        
        # Test cursor movement with long input
        app.cursor_home()
        assert app.cursor_pos == 0
        
        app.cursor_end()
        assert app.cursor_pos == 200
    
    def test_tui_multiple_pane_updates(self):
        """Test TUI with multiple pane updates."""
        app = TUIApplication(self.config)
        
        # Add content to multiple panes
        app.chat_pane.add_line("Chat message 1")
        app.output_pane.add_line("Output message 1")
        app.status_pane.add_line("Status message 1")
        
        # All panes should have content
        assert len(app.chat_pane.content) == 1
        assert len(app.output_pane.content) == 1
        assert len(app.status_pane.content) >= 1  # May have initial status messages
        
        # Test pane scrolling
        for i in range(10):
            app.chat_pane.add_line(f"Message {i+2}")
        
        app.chat_pane.scroll_up(5)
        visible = app.get_visible_lines(app.chat_pane, 5)
        assert len(visible) == 5
        assert "Message 6" in visible[0] or "Message 7" in visible[0]  # Approximate check


class TestTUIKeyboardShortcuts:
    """Test TUI keyboard shortcuts and interactive elements."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.app = TUIApplication(self.config)
    
    def test_function_key_shortcuts(self):
        """Test function key shortcuts."""
        # F1 - Help
        self.app.key_bindings[curses.KEY_F1]()
        assert self.app.current_mode == "help"
        
        # F2 - Chat
        self.app.key_bindings[curses.KEY_F2]()
        assert self.app.current_mode == "chat"
        
        # F3 - Search
        self.app.key_bindings[curses.KEY_F3]()
        assert self.app.current_mode == "search"
        
        # F4 - Files
        self.app.key_bindings[curses.KEY_F4]()
        assert self.app.current_mode == "files"
    
    def test_navigation_shortcuts(self):
        """Test navigation shortcuts."""
        # Set up input buffer
        self.app.input_buffer = "test input"
        self.app.cursor_pos = 5
        
        # Left arrow
        self.app.key_bindings[curses.KEY_LEFT]()
        assert self.app.cursor_pos == 4
        
        # Right arrow
        self.app.key_bindings[curses.KEY_RIGHT]()
        assert self.app.cursor_pos == 5
        
        # Home key
        self.app.key_bindings[curses.KEY_HOME]()
        assert self.app.cursor_pos == 0
        
        # End key
        self.app.key_bindings[curses.KEY_END]()
        assert self.app.cursor_pos == len(self.app.input_buffer)
    
    def test_history_shortcuts(self):
        """Test history navigation shortcuts."""
        # Set up history
        self.app.input_history = ["cmd1", "cmd2", "cmd3"]
        
        # Up arrow
        self.app.key_bindings[curses.KEY_UP]()
        assert self.app.input_buffer == "cmd3"
        
        # Down arrow
        self.app.key_bindings[curses.KEY_DOWN]()
        assert self.app.input_buffer == ""
    
    def test_editing_shortcuts(self):
        """Test editing shortcuts."""
        # Set up input
        self.app.input_buffer = "hello"
        self.app.cursor_pos = 5
        
        # Backspace
        self.app.key_bindings[curses.KEY_BACKSPACE]()
        assert self.app.input_buffer == "hell"
        assert self.app.cursor_pos == 4
        
        # DEL key (127)
        self.app.cursor_pos = 2
        self.app.key_bindings[127]()
        assert self.app.input_buffer == "hel"
        assert self.app.cursor_pos == 2
    
    def test_submit_shortcuts(self):
        """Test submit shortcuts."""
        self.app.input_buffer = "test command"
        
        # Mock the submit handler
        original_submit = self.app.submit_input
        submit_called = False
        
        def mock_submit():
            nonlocal submit_called
            submit_called = True
        
        self.app.submit_input = mock_submit
        
        # Enter key (\n)
        self.app.key_bindings[ord('\n')]()
        assert submit_called
        
        # Reset and test carriage return (\r)
        submit_called = False
        self.app.key_bindings[ord('\r')]()
        assert submit_called
        
        # Restore original
        self.app.submit_input = original_submit
    
    def test_mode_switching_shortcut(self):
        """Test mode switching shortcut."""
        assert self.app.current_mode == "chat"
        
        # Tab key
        self.app.key_bindings[ord('\t')]()
        assert self.app.current_mode == "search"
        
        self.app.key_bindings[ord('\t')]()
        assert self.app.current_mode == "files"
    
    def test_escape_shortcut(self):
        """Test escape key shortcut."""
        # With progress active
        self.app.current_progress = ProgressIndicator(description="Test")
        self.app.key_bindings[27]()  # ESC key
        assert self.app.current_progress is None
        
        # Without progress - should exit
        self.app.running = True
        self.app.key_bindings[27]()
        assert not self.app.running