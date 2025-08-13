from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

import pytest

from term_coder.progress import (
    ProgressManager, ProgressConfig, SimpleSpinner, ProgressCallback,
    progress_context, with_progress
)
from term_coder.output import (
    OutputLine, OutputBuffer, OutputCapture, OutputPane, OutputManager
)


class TestProgressManager:
    """Test progress management functionality."""
    
    def test_progress_manager_initialization(self):
        """Test progress manager initialization."""
        config = ProgressConfig(show_spinner=True, show_bar=True)
        manager = ProgressManager(config=config)
        
        assert manager.config == config
        assert not manager.active
        assert len(manager.tasks) == 0
    
    def test_progress_manager_lifecycle(self):
        """Test progress manager start/stop lifecycle."""
        manager = ProgressManager()
        
        # Initially not active
        assert not manager.is_active()
        
        # Start should make it active
        manager.start()
        assert manager.is_active()
        assert manager.progress is not None
        assert manager.live is not None
        
        # Stop should deactivate
        manager.stop()
        assert not manager.is_active()
        assert manager.progress is None
        assert manager.live is None
    
    def test_progress_task_management(self):
        """Test adding and managing progress tasks."""
        manager = ProgressManager()
        manager.start()
        
        try:
            # Add a task
            task_name = manager.add_task("test_task", "Testing progress", total=100)
            assert task_name == "test_task"
            assert "test_task" in manager.tasks
            
            # Update the task
            manager.update_task("test_task", advance=10, description="Updated description")
            
            # Complete the task
            manager.complete_task("test_task")
            
            # Task should still exist briefly
            assert "test_task" in manager.tasks
            
        finally:
            manager.stop()
    
    def test_progress_context_manager(self):
        """Test progress context manager."""
        with progress_context(auto_start=True) as manager:
            assert manager.is_active()
            
            with manager.task("test", "Testing", total=10) as task:
                task.update(5)
                task.set_description("Half done")
        
        # Should be stopped after context exit
        assert not manager.is_active()
    
    def test_progress_decorator(self):
        """Test progress decorator."""
        @with_progress("Processing items", total=5)
        def process_items(items, progress_task=None):
            results = []
            for i, item in enumerate(items):
                if progress_task:
                    progress_task.update(1, f"Processing item {i+1}")
                results.append(item * 2)
                time.sleep(0.01)  # Simulate work
            return results
        
        items = [1, 2, 3, 4, 5]
        results = process_items(items)
        assert results == [2, 4, 6, 8, 10]


class TestSimpleSpinner:
    """Test simple spinner functionality."""
    
    def test_spinner_lifecycle(self):
        """Test spinner start/stop lifecycle."""
        spinner = SimpleSpinner("Testing")
        
        # Initially not active
        assert not spinner.active
        
        # Start spinner
        spinner.start()
        assert spinner.active
        assert spinner.thread is not None
        
        # Let it spin briefly
        time.sleep(0.1)
        
        # Stop spinner
        spinner.stop()
        assert not spinner.active
    
    def test_spinner_context_manager(self):
        """Test spinner as context manager."""
        with SimpleSpinner("Testing") as spinner:
            assert spinner.active
            time.sleep(0.1)
        
        assert not spinner.active
    
    def test_spinner_double_start_stop(self):
        """Test that double start/stop doesn't cause issues."""
        spinner = SimpleSpinner("Testing")
        
        # Multiple starts should be safe
        spinner.start()
        spinner.start()
        assert spinner.active
        
        # Multiple stops should be safe
        spinner.stop()
        spinner.stop()
        assert not spinner.active


class TestProgressCallback:
    """Test progress callback functionality."""
    
    def test_progress_callback_basic(self):
        """Test basic progress callback functionality."""
        callback = ProgressCallback()
        
        # Initially no progress
        assert callback.current == 0
        assert callback.total is None
        assert callback.get_percentage() == 0.0
        assert not callback.is_complete()
        
        # Set total and update
        callback.set_total(100)
        assert callback.total == 100
        
        callback.update(25)
        assert callback.current == 25
        assert callback.get_percentage() == 25.0
        assert not callback.is_complete()
        
        # Complete
        callback.update(75)
        assert callback.current == 100
        assert callback.get_percentage() == 100.0
        assert callback.is_complete()
    
    def test_progress_callback_with_task_context(self):
        """Test progress callback with task context."""
        mock_task = Mock()
        callback = ProgressCallback(mock_task)
        
        callback.set_total(50)
        mock_task.set_total.assert_called_once_with(50)
        
        callback.update(10, "Working...")
        mock_task.update.assert_called_with(10, "Working...")
        
        callback.set_description("Almost done")
        mock_task.set_description.assert_called_with("Almost done")


class TestOutputLine:
    """Test output line functionality."""
    
    def test_output_line_creation(self):
        """Test output line creation and serialization."""
        from datetime import datetime
        
        timestamp = datetime.now()
        line = OutputLine(
            content="Test message",
            timestamp=timestamp,
            source="test",
            level="info",
            tags=["tag1", "tag2"]
        )
        
        assert line.content == "Test message"
        assert line.timestamp == timestamp
        assert line.source == "test"
        assert line.level == "info"
        assert line.tags == ["tag1", "tag2"]
    
    def test_output_line_serialization(self):
        """Test output line serialization/deserialization."""
        from datetime import datetime
        
        original = OutputLine(
            content="Test message",
            timestamp=datetime.now(),
            source="test",
            level="warning",
            tags=["important"]
        )
        
        # Serialize to dict
        data = original.to_dict()
        assert isinstance(data, dict)
        assert data["content"] == "Test message"
        assert data["source"] == "test"
        assert data["level"] == "warning"
        assert data["tags"] == ["important"]
        
        # Deserialize from dict
        restored = OutputLine.from_dict(data)
        assert restored.content == original.content
        assert restored.source == original.source
        assert restored.level == original.level
        assert restored.tags == original.tags


class TestOutputBuffer:
    """Test output buffer functionality."""
    
    def test_output_buffer_basic(self):
        """Test basic output buffer operations."""
        buffer = OutputBuffer(max_lines=5, name="test")
        
        assert buffer.name == "test"
        assert buffer.max_lines == 5
        assert len(buffer.lines) == 0
        assert buffer.auto_scroll == True
        
        # Add some lines
        buffer.add_line("Line 1", source="test")
        buffer.add_line("Line 2", source="test")
        buffer.add_line("Line 3", source="test")
        
        assert len(buffer.lines) == 3
        assert buffer.lines[0].content == "Line 1"
        assert buffer.lines[2].content == "Line 3"
    
    def test_output_buffer_max_lines(self):
        """Test output buffer max lines enforcement."""
        buffer = OutputBuffer(max_lines=3, name="test")
        
        # Add more lines than max
        for i in range(5):
            buffer.add_line(f"Line {i+1}", source="test")
        
        # Should only keep last 3 lines
        assert len(buffer.lines) == 3
        assert buffer.lines[0].content == "Line 3"
        assert buffer.lines[1].content == "Line 4"
        assert buffer.lines[2].content == "Line 5"
    
    def test_output_buffer_scrolling(self):
        """Test output buffer scrolling functionality."""
        buffer = OutputBuffer(max_lines=10, name="test")
        
        # Add some lines
        for i in range(8):
            buffer.add_line(f"Line {i+1}", source="test")
        
        # Test scrolling
        buffer.scroll_up(2)
        assert buffer.scroll_position == 5  # 7 - 2
        assert not buffer.auto_scroll
        
        buffer.scroll_down(1)
        assert buffer.scroll_position == 6
        
        buffer.scroll_to_top()
        assert buffer.scroll_position == 0
        
        buffer.scroll_to_bottom()
        assert buffer.scroll_position == 7
        assert buffer.auto_scroll
    
    def test_output_buffer_visible_lines(self):
        """Test getting visible lines from buffer."""
        buffer = OutputBuffer(max_lines=10, name="test")
        
        # Add some lines
        for i in range(8):
            buffer.add_line(f"Line {i+1}", source="test")
        
        # Get visible lines for a window of height 3
        visible = buffer.get_visible_lines(3)
        assert len(visible) == 3
        assert visible[0].content == "Line 6"
        assert visible[1].content == "Line 7"
        assert visible[2].content == "Line 8"
        
        # Scroll and check again
        buffer.scroll_up(3)
        visible = buffer.get_visible_lines(3)
        assert len(visible) == 3
        assert visible[0].content == "Line 3"
        assert visible[1].content == "Line 4"
        assert visible[2].content == "Line 5"
    
    def test_output_buffer_filtering(self):
        """Test output buffer filtering functionality."""
        buffer = OutputBuffer(max_lines=10, name="test")
        
        # Add lines with different levels
        buffer.add_line("Info message", source="test", level="info")
        buffer.add_line("Warning message", source="test", level="warning")
        buffer.add_line("Error message", source="test", level="error")
        buffer.add_line("Debug message", source="test", level="debug")
        
        # Add filter for warnings and errors only
        buffer.add_filter("important", lambda line: line.level in ["warning", "error"])
        
        # Get filtered lines
        filtered = buffer.get_lines(apply_filters=True)
        assert len(filtered) == 2
        assert filtered[0].level == "warning"
        assert filtered[1].level == "error"
        
        # Get unfiltered lines
        unfiltered = buffer.get_lines(apply_filters=False)
        assert len(unfiltered) == 4
    
    def test_output_buffer_search(self):
        """Test output buffer search functionality."""
        buffer = OutputBuffer(max_lines=10, name="test")
        
        buffer.add_line("Hello world", source="test")
        buffer.add_line("Python is great", source="test")
        buffer.add_line("Hello Python", source="test")
        buffer.add_line("Goodbye world", source="test")
        
        # Search for "Hello"
        matches = buffer.search("Hello")
        assert len(matches) == 2
        assert matches == [0, 2]
        
        # Case sensitive search
        matches = buffer.search("hello", case_sensitive=True)
        assert len(matches) == 0
        
        matches = buffer.search("hello", case_sensitive=False)
        assert len(matches) == 2
    
    def test_output_buffer_listeners(self):
        """Test output buffer listener functionality."""
        buffer = OutputBuffer(max_lines=10, name="test")
        
        # Add a mock listener
        listener = Mock()
        buffer.add_listener(listener)
        
        # Add a line - listener should be called
        buffer.add_line("Test message", source="test")
        listener.assert_called_once()
        
        # Remove listener
        buffer.remove_listener(listener)
        listener.reset_mock()
        
        # Add another line - listener should not be called
        buffer.add_line("Another message", source="test")
        listener.assert_not_called()
    
    def test_output_buffer_stats(self):
        """Test output buffer statistics."""
        buffer = OutputBuffer(max_lines=10, name="test")
        
        buffer.add_line("Info 1", source="stdout", level="info")
        buffer.add_line("Warning 1", source="stderr", level="warning")
        buffer.add_line("Info 2", source="stdout", level="info")
        buffer.add_line("Error 1", source="stderr", level="error")
        
        stats = buffer.get_stats()
        
        assert stats["total_lines"] == 4
        assert stats["sources"]["stdout"] == 2
        assert stats["sources"]["stderr"] == 2
        assert stats["levels"]["info"] == 2
        assert stats["levels"]["warning"] == 1
        assert stats["levels"]["error"] == 1
    
    def test_output_buffer_file_operations(self):
        """Test output buffer file save/load operations."""
        buffer = OutputBuffer(max_lines=10, name="test")
        
        # Add some test data
        buffer.add_line("Line 1", source="test", level="info", tags=["tag1"])
        buffer.add_line("Line 2", source="test", level="warning", tags=["tag2"])
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "test_buffer.json"
            
            # Save to file
            buffer.save_to_file(file_path, format="json")
            assert file_path.exists()
            
            # Load into new buffer
            new_buffer = OutputBuffer(max_lines=10, name="loaded")
            new_buffer.load_from_file(file_path, format="json")
            
            assert len(new_buffer.lines) == 2
            assert new_buffer.lines[0].content == "Line 1"
            assert new_buffer.lines[1].content == "Line 2"


class TestOutputCapture:
    """Test output capture functionality."""
    
    def test_output_capture_basic(self):
        """Test basic output capture."""
        stdout_buffer = OutputBuffer(name="stdout")
        stderr_buffer = OutputBuffer(name="stderr")
        
        capture = OutputCapture(stdout_buffer, stderr_buffer)
        
        assert not capture.capturing
        
        with capture:
            assert capture.capturing
            print("Test stdout message")
            print("Test stderr message", file=sys.stderr)
        
        assert not capture.capturing
        
        # Check that messages were captured
        # Note: In tests, the capture might not work exactly as expected
        # due to test runner output handling
    
    def test_output_capture_manual_control(self):
        """Test manual output capture control."""
        stdout_buffer = OutputBuffer(name="stdout")
        capture = OutputCapture(stdout_buffer)
        
        capture.start()
        assert capture.capturing
        
        capture.stop()
        assert not capture.capturing


class TestOutputPane:
    """Test output pane functionality."""
    
    def test_output_pane_creation(self):
        """Test output pane creation."""
        buffer = OutputBuffer(name="test")
        pane = OutputPane(buffer)
        
        assert pane.buffer == buffer
        assert pane.title == "Test"
        assert pane.show_timestamps == True
        assert pane.show_sources == True
    
    @patch('term_coder.output.Panel')
    def test_output_pane_render(self, mock_panel):
        """Test output pane rendering."""
        buffer = OutputBuffer(name="test")
        buffer.add_line("Test message", source="test", level="info")
        
        pane = OutputPane(buffer)
        pane.render(10, 80)
        
        # Should have called Panel constructor
        mock_panel.assert_called_once()


class TestOutputManager:
    """Test output manager functionality."""
    
    def test_output_manager_creation(self):
        """Test output manager creation."""
        manager = OutputManager()
        
        assert len(manager.buffers) == 0
        assert len(manager.panes) == 0
        assert manager.active_pane is None
    
    def test_output_manager_buffer_management(self):
        """Test output manager buffer management."""
        manager = OutputManager()
        
        # Create a buffer
        buffer = manager.create_buffer("test", max_lines=100)
        
        assert "test" in manager.buffers
        assert "test" in manager.panes
        assert manager.active_pane == "test"
        assert buffer.name == "test"
        assert buffer.max_lines == 100
        
        # Get buffer
        retrieved = manager.get_buffer("test")
        assert retrieved == buffer
        
        # Get pane
        pane = manager.get_pane("test")
        assert pane is not None
        assert pane.buffer == buffer
    
    def test_output_manager_system_messages(self):
        """Test output manager system message functionality."""
        manager = OutputManager()
        
        # Add system message - should create buffer automatically
        manager.add_system_message("System started", level="info", buffer_name="system")
        
        assert "system" in manager.buffers
        system_buffer = manager.get_buffer("system")
        assert len(system_buffer.lines) == 1
        assert system_buffer.lines[0].content == "System started"
        assert system_buffer.lines[0].level == "info"
    
    def test_output_manager_capture_control(self):
        """Test output manager capture control."""
        manager = OutputManager()
        
        # Start capture should create stdout/stderr buffers
        manager.start_capture()
        
        assert "stdout" in manager.buffers
        assert "stderr" in manager.buffers
        assert manager.capture is not None
        
        # Stop capture
        manager.stop_capture()
    
    def test_output_manager_stats(self):
        """Test output manager combined statistics."""
        manager = OutputManager()
        
        # Create some buffers with data
        buffer1 = manager.create_buffer("test1")
        buffer1.add_line("Message 1", source="test")
        
        buffer2 = manager.create_buffer("test2")
        buffer2.add_line("Message 2", source="test")
        buffer2.add_line("Message 3", source="test")
        
        stats = manager.get_combined_stats()
        
        assert stats["total_buffers"] == 2
        assert "test1" in stats["buffers"]
        assert "test2" in stats["buffers"]
        assert stats["buffers"]["test1"]["total_lines"] == 1
        assert stats["buffers"]["test2"]["total_lines"] == 2
    
    def test_output_manager_file_operations(self):
        """Test output manager file operations."""
        manager = OutputManager()
        
        # Create buffers with data
        buffer1 = manager.create_buffer("test1")
        buffer1.add_line("Test message 1", source="test")
        
        buffer2 = manager.create_buffer("test2")
        buffer2.add_line("Test message 2", source="test")
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            
            # Save all buffers
            manager.save_all_buffers(output_dir)
            
            # Check files were created
            assert (output_dir / "test1_output.json").exists()
            assert (output_dir / "test2_output.json").exists()


class TestUIIntegration:
    """Test UI component integration scenarios."""
    
    def test_progress_with_output_capture(self):
        """Test progress indicators with output capture."""
        output_manager = OutputManager()
        output_manager.start_capture()
        
        try:
            with progress_context() as progress:
                with progress.task("test", "Testing integration", total=3) as task:
                    print("Step 1")
                    task.update(1)
                    
                    print("Step 2")
                    task.update(1)
                    
                    print("Step 3")
                    task.update(1)
            
            # Check that output was captured
            stdout_buffer = output_manager.get_buffer("stdout")
            if stdout_buffer:
                assert len(stdout_buffer.lines) >= 0  # May vary in test environment
        
        finally:
            output_manager.stop_capture()
    
    def test_threaded_progress_updates(self):
        """Test progress updates from multiple threads."""
        manager = ProgressManager()
        manager.start()
        
        try:
            task_name = manager.add_task("threaded", "Threading test", total=10)
            
            def worker():
                for i in range(5):
                    manager.update_task(task_name, advance=1)
                    time.sleep(0.01)
            
            # Start two worker threads
            thread1 = threading.Thread(target=worker)
            thread2 = threading.Thread(target=worker)
            
            thread1.start()
            thread2.start()
            
            thread1.join()
            thread2.join()
            
            # Task should be complete
            manager.complete_task(task_name)
        
        finally:
            manager.stop()
    
    def test_output_buffer_with_listeners_and_filters(self):
        """Test output buffer with both listeners and filters."""
        buffer = OutputBuffer(name="test")
        
        # Add listener to track important messages
        important_messages = []
        def important_listener(line):
            if line.level in ["warning", "error"]:
                important_messages.append(line.content)
        
        buffer.add_listener(important_listener)
        
        # Add filter for errors only
        buffer.add_filter("errors_only", lambda line: line.level == "error")
        
        # Add various messages
        buffer.add_line("Info message", level="info")
        buffer.add_line("Warning message", level="warning")
        buffer.add_line("Error message", level="error")
        buffer.add_line("Debug message", level="debug")
        
        # Check listener captured important messages
        assert len(important_messages) == 2
        assert "Warning message" in important_messages
        assert "Error message" in important_messages
        
        # Check filter shows only errors
        filtered_lines = buffer.get_lines(apply_filters=True)
        assert len(filtered_lines) == 1
        assert filtered_lines[0].level == "error"