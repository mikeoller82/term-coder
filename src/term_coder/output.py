from __future__ import annotations

import io
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TextIO, Union
from datetime import datetime
from pathlib import Path
import json

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns
from rich.layout import Layout


@dataclass
class OutputLine:
    """Represents a line of output with metadata."""
    content: str
    timestamp: datetime
    source: str  # stdout, stderr, system, etc.
    level: str = "info"  # info, warning, error, debug
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "level": self.level,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OutputLine":
        """Create from dictionary."""
        return cls(
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data["source"],
            level=data.get("level", "info"),
            tags=data.get("tags", [])
        )


class OutputBuffer:
    """Buffer for capturing and managing output with scrollback."""
    
    def __init__(self, max_lines: int = 10000, name: str = "default"):
        self.max_lines = max_lines
        self.name = name
        self.lines: List[OutputLine] = []
        self.scroll_position = 0
        self.auto_scroll = True
        self.filters: Dict[str, Callable[[OutputLine], bool]] = {}
        self._lock = threading.RLock()
        self.listeners: List[Callable[[OutputLine], None]] = []
    
    def add_line(self, content: str, source: str = "system", level: str = "info", tags: Optional[List[str]] = None) -> None:
        """Add a line to the buffer."""
        with self._lock:
            line = OutputLine(
                content=content,
                timestamp=datetime.now(),
                source=source,
                level=level,
                tags=tags or []
            )
            
            self.lines.append(line)
            
            # Trim buffer if too large
            if len(self.lines) > self.max_lines:
                self.lines.pop(0)
                if self.scroll_position > 0:
                    self.scroll_position -= 1
            
            # Auto-scroll to bottom if enabled
            if self.auto_scroll:
                self.scroll_position = len(self.lines) - 1
            
            # Notify listeners
            for listener in self.listeners:
                try:
                    listener(line)
                except Exception:
                    pass  # Ignore listener errors
    
    def get_lines(self, start: Optional[int] = None, end: Optional[int] = None, 
                  apply_filters: bool = True) -> List[OutputLine]:
        """Get lines from the buffer with optional filtering."""
        with self._lock:
            lines = self.lines[start:end] if start is not None or end is not None else self.lines
            
            if apply_filters and self.filters:
                for filter_func in self.filters.values():
                    lines = [line for line in lines if filter_func(line)]
            
            return lines.copy()
    
    def get_visible_lines(self, height: int, apply_filters: bool = True) -> List[OutputLine]:
        """Get lines visible in a window of given height."""
        with self._lock:
            if not self.lines:
                return []
            
            end_pos = min(len(self.lines), self.scroll_position + height)
            start_pos = max(0, end_pos - height)
            
            return self.get_lines(start_pos, end_pos, apply_filters)
    
    def scroll_up(self, lines: int = 1) -> None:
        """Scroll up by specified number of lines."""
        with self._lock:
            self.scroll_position = max(0, self.scroll_position - lines)
            self.auto_scroll = False
    
    def scroll_down(self, lines: int = 1) -> None:
        """Scroll down by specified number of lines."""
        with self._lock:
            max_pos = len(self.lines) - 1
            self.scroll_position = min(max_pos, self.scroll_position + lines)
            
            # Re-enable auto-scroll if at bottom
            if self.scroll_position >= max_pos:
                self.auto_scroll = True
    
    def scroll_to_top(self) -> None:
        """Scroll to the top of the buffer."""
        with self._lock:
            self.scroll_position = 0
            self.auto_scroll = False
    
    def scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the buffer."""
        with self._lock:
            self.scroll_position = max(0, len(self.lines) - 1)
            self.auto_scroll = True
    
    def add_filter(self, name: str, filter_func: Callable[[OutputLine], bool]) -> None:
        """Add a filter function."""
        with self._lock:
            self.filters[name] = filter_func
    
    def remove_filter(self, name: str) -> None:
        """Remove a filter function."""
        with self._lock:
            self.filters.pop(name, None)
    
    def clear_filters(self) -> None:
        """Clear all filters."""
        with self._lock:
            self.filters.clear()
    
    def add_listener(self, listener: Callable[[OutputLine], None]) -> None:
        """Add a listener for new lines."""
        with self._lock:
            self.listeners.append(listener)
    
    def remove_listener(self, listener: Callable[[OutputLine], None]) -> None:
        """Remove a listener."""
        with self._lock:
            if listener in self.listeners:
                self.listeners.remove(listener)
    
    def clear(self) -> None:
        """Clear all lines from the buffer."""
        with self._lock:
            self.lines.clear()
            self.scroll_position = 0
            self.auto_scroll = True
    
    def search(self, query: str, case_sensitive: bool = False) -> List[int]:
        """Search for lines containing the query. Returns line indices."""
        with self._lock:
            if not case_sensitive:
                query = query.lower()
            
            matches = []
            for i, line in enumerate(self.lines):
                content = line.content if case_sensitive else line.content.lower()
                if query in content:
                    matches.append(i)
            
            return matches
    
    def get_stats(self) -> Dict[str, Any]:
        """Get buffer statistics."""
        with self._lock:
            stats = {
                "total_lines": len(self.lines),
                "scroll_position": self.scroll_position,
                "auto_scroll": self.auto_scroll,
                "max_lines": self.max_lines,
                "sources": {},
                "levels": {}
            }
            
            for line in self.lines:
                stats["sources"][line.source] = stats["sources"].get(line.source, 0) + 1
                stats["levels"][line.level] = stats["levels"].get(line.level, 0) + 1
            
            return stats
    
    def save_to_file(self, file_path: Path, format: str = "json") -> None:
        """Save buffer contents to file."""
        with self._lock:
            if format == "json":
                data = {
                    "name": self.name,
                    "timestamp": datetime.now().isoformat(),
                    "lines": [line.to_dict() for line in self.lines]
                }
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
            
            elif format == "text":
                with open(file_path, 'w') as f:
                    for line in self.lines:
                        f.write(f"[{line.timestamp.isoformat()}] {line.source}: {line.content}\n")
    
    def load_from_file(self, file_path: Path, format: str = "json") -> None:
        """Load buffer contents from file."""
        with self._lock:
            if format == "json":
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                self.lines = [OutputLine.from_dict(line_data) for line_data in data["lines"]]
                self.scroll_position = len(self.lines) - 1 if self.lines else 0
            
            elif format == "text":
                # Simple text format parsing
                with open(file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self.add_line(line, source="file", level="info")


class OutputCapture:
    """Captures stdout/stderr and redirects to output buffers."""
    
    def __init__(self, stdout_buffer: Optional[OutputBuffer] = None, 
                 stderr_buffer: Optional[OutputBuffer] = None):
        self.stdout_buffer = stdout_buffer or OutputBuffer(name="stdout")
        self.stderr_buffer = stderr_buffer or OutputBuffer(name="stderr")
        
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.capturing = False
        
        # Create custom file-like objects
        self.stdout_capture = self._create_capture_stream("stdout", self.stdout_buffer)
        self.stderr_capture = self._create_capture_stream("stderr", self.stderr_buffer)
    
    def _create_capture_stream(self, source: str, buffer: OutputBuffer) -> TextIO:
        """Create a file-like object that captures to a buffer."""
        class CaptureStream(io.StringIO):
            def __init__(self, source: str, buffer: OutputBuffer, original: TextIO):
                super().__init__()
                self.source = source
                self.buffer = buffer
                self.original = original
            
            def write(self, text: str) -> int:
                # Write to original stream
                result = self.original.write(text)
                self.original.flush()
                
                # Capture to buffer
                if text.strip():  # Only capture non-empty lines
                    lines = text.splitlines()
                    for line in lines:
                        if line.strip():
                            self.buffer.add_line(line, source=self.source)
                
                return result
            
            def flush(self) -> None:
                self.original.flush()
        
        return CaptureStream(source, buffer, getattr(sys, source))
    
    def start(self) -> None:
        """Start capturing output."""
        if self.capturing:
            return
        
        sys.stdout = self.stdout_capture
        sys.stderr = self.stderr_capture
        self.capturing = True
    
    def stop(self) -> None:
        """Stop capturing output."""
        if not self.capturing:
            return
        
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        self.capturing = False
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class OutputPane:
    """Rich-based output pane with scrollback and filtering."""
    
    def __init__(self, buffer: OutputBuffer, console: Optional[Console] = None):
        self.buffer = buffer
        self.console = console or Console()
        self.title = buffer.name.title()
        self.show_timestamps = True
        self.show_sources = True
        self.show_levels = True
        self.color_map = {
            "info": "white",
            "warning": "yellow",
            "error": "red",
            "debug": "dim white",
            "success": "green"
        }
    
    def render(self, height: int, width: int) -> Panel:
        """Render the output pane as a Rich panel."""
        lines = self.buffer.get_visible_lines(height - 2)  # Account for panel borders
        
        if not lines:
            content = Text("No output", style="dim")
        else:
            content_lines = []
            for line in lines:
                text_parts = []
                
                if self.show_timestamps:
                    timestamp = line.timestamp.strftime("%H:%M:%S")
                    text_parts.append(Text(f"[{timestamp}]", style="dim"))
                
                if self.show_sources:
                    text_parts.append(Text(f"{line.source}:", style="cyan"))
                
                if self.show_levels and line.level != "info":
                    level_style = self.color_map.get(line.level, "white")
                    text_parts.append(Text(f"[{line.level.upper()}]", style=level_style))
                
                # Main content
                content_style = self.color_map.get(line.level, "white")
                text_parts.append(Text(line.content, style=content_style))
                
                # Combine parts
                line_text = Text(" ").join(text_parts)
                
                # Truncate if too long
                if len(line_text) > width - 4:
                    line_text = line_text[:width - 7] + Text("...", style="dim")
                
                content_lines.append(line_text)
            
            content = Text("\n").join(content_lines)
        
        # Create panel with scroll indicator
        stats = self.buffer.get_stats()
        scroll_info = ""
        if not self.buffer.auto_scroll:
            scroll_info = f" (scroll: {self.buffer.scroll_position}/{stats['total_lines']})"
        
        title = f"{self.title}{scroll_info}"
        
        return Panel(
            content,
            title=title,
            border_style="blue",
            height=height
        )
    
    def render_split(self, other_pane: "OutputPane", height: int, width: int) -> Layout:
        """Render this pane split with another pane."""
        layout = Layout()
        layout.split_row(
            Layout(self.render(height, width // 2), name="left"),
            Layout(other_pane.render(height, width // 2), name="right")
        )
        return layout


class OutputManager:
    """Manages multiple output buffers and panes."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.buffers: Dict[str, OutputBuffer] = {}
        self.panes: Dict[str, OutputPane] = {}
        self.active_pane: Optional[str] = None
        self.capture: Optional[OutputCapture] = None
    
    def create_buffer(self, name: str, max_lines: int = 10000) -> OutputBuffer:
        """Create a new output buffer."""
        buffer = OutputBuffer(max_lines=max_lines, name=name)
        self.buffers[name] = buffer
        self.panes[name] = OutputPane(buffer, self.console)
        
        if self.active_pane is None:
            self.active_pane = name
        
        return buffer
    
    def get_buffer(self, name: str) -> Optional[OutputBuffer]:
        """Get an output buffer by name."""
        return self.buffers.get(name)
    
    def get_pane(self, name: str) -> Optional[OutputPane]:
        """Get an output pane by name."""
        return self.panes.get(name)
    
    def set_active_pane(self, name: str) -> None:
        """Set the active pane."""
        if name in self.panes:
            self.active_pane = name
    
    def start_capture(self) -> None:
        """Start capturing stdout/stderr."""
        if self.capture is None:
            stdout_buffer = self.buffers.get("stdout") or self.create_buffer("stdout")
            stderr_buffer = self.buffers.get("stderr") or self.create_buffer("stderr")
            self.capture = OutputCapture(stdout_buffer, stderr_buffer)
        
        self.capture.start()
    
    def stop_capture(self) -> None:
        """Stop capturing stdout/stderr."""
        if self.capture:
            self.capture.stop()
    
    def render_active_pane(self, height: int, width: int) -> Optional[Panel]:
        """Render the active pane."""
        if self.active_pane and self.active_pane in self.panes:
            return self.panes[self.active_pane].render(height, width)
        return None
    
    def render_split_view(self, pane1: str, pane2: str, height: int, width: int) -> Optional[Layout]:
        """Render two panes in split view."""
        if pane1 in self.panes and pane2 in self.panes:
            return self.panes[pane1].render_split(self.panes[pane2], height, width)
        return None
    
    def add_system_message(self, message: str, level: str = "info", buffer_name: str = "system") -> None:
        """Add a system message to a buffer."""
        if buffer_name not in self.buffers:
            self.create_buffer(buffer_name)
        
        self.buffers[buffer_name].add_line(message, source="system", level=level)
    
    def clear_all_buffers(self) -> None:
        """Clear all output buffers."""
        for buffer in self.buffers.values():
            buffer.clear()
    
    def save_all_buffers(self, directory: Path) -> None:
        """Save all buffers to files."""
        directory.mkdir(parents=True, exist_ok=True)
        
        for name, buffer in self.buffers.items():
            file_path = directory / f"{name}_output.json"
            buffer.save_to_file(file_path)
    
    def get_combined_stats(self) -> Dict[str, Any]:
        """Get combined statistics for all buffers."""
        combined_stats = {
            "total_buffers": len(self.buffers),
            "active_pane": self.active_pane,
            "buffers": {}
        }
        
        for name, buffer in self.buffers.items():
            combined_stats["buffers"][name] = buffer.get_stats()
        
        return combined_stats


# Global output manager instance
_global_output_manager: Optional[OutputManager] = None


def get_global_output_manager() -> OutputManager:
    """Get the global output manager instance."""
    global _global_output_manager
    if _global_output_manager is None:
        _global_output_manager = OutputManager()
    return _global_output_manager