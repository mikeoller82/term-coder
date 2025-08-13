from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Union
from contextlib import contextmanager

from rich.console import Console
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, MofNCompleteColumn
from rich.live import Live


@dataclass
class ProgressConfig:
    """Configuration for progress indicators."""
    show_spinner: bool = True
    show_bar: bool = True
    show_time: bool = True
    show_count: bool = True
    refresh_rate: float = 10.0  # Updates per second
    auto_refresh: bool = True


class ProgressManager:
    """Manages progress indicators for long-running operations."""
    
    def __init__(self, console: Optional[Console] = None, config: Optional[ProgressConfig] = None):
        self.console = console or Console()
        self.config = config or ProgressConfig()
        self.progress: Optional[Progress] = None
        self.live: Optional[Live] = None
        self.tasks: Dict[str, TaskID] = {}
        self.active = False
        self._lock = threading.Lock()
    
    def start(self) -> None:
        """Start the progress display."""
        with self._lock:
            if self.active:
                return
            
            columns = []
            
            if self.config.show_spinner:
                columns.append(SpinnerColumn())
            
            columns.append(TextColumn("[progress.description]{task.description}"))
            
            if self.config.show_bar:
                columns.append(BarColumn())
            
            if self.config.show_count:
                columns.append(MofNCompleteColumn())
            
            if self.config.show_time:
                columns.append(TimeElapsedColumn())
            
            self.progress = Progress(
                *columns,
                console=self.console,
                refresh_per_second=self.config.refresh_rate,
                auto_refresh=self.config.auto_refresh
            )
            
            self.live = Live(self.progress, console=self.console, refresh_per_second=self.config.refresh_rate)
            self.live.start()
            self.active = True
    
    def stop(self) -> None:
        """Stop the progress display."""
        with self._lock:
            if not self.active:
                return
            
            if self.live:
                self.live.stop()
                self.live = None
            
            self.progress = None
            self.tasks.clear()
            self.active = False
    
    def add_task(self, name: str, description: str, total: Optional[int] = None) -> str:
        """Add a new progress task."""
        with self._lock:
            if not self.active or not self.progress:
                return name
            
            task_id = self.progress.add_task(description, total=total)
            self.tasks[name] = task_id
            return name
    
    def update_task(self, name: str, advance: int = 1, description: Optional[str] = None, **kwargs) -> None:
        """Update a progress task."""
        with self._lock:
            if not self.active or not self.progress or name not in self.tasks:
                return
            
            task_id = self.tasks[name]
            update_kwargs = {"advance": advance}
            
            if description is not None:
                update_kwargs["description"] = description
            
            update_kwargs.update(kwargs)
            self.progress.update(task_id, **update_kwargs)
    
    def complete_task(self, name: str) -> None:
        """Mark a task as complete."""
        with self._lock:
            if not self.active or not self.progress or name not in self.tasks:
                return
            
            task_id = self.tasks[name]
            task = self.progress.tasks[task_id]
            if task.total is not None:
                remaining = task.total - task.completed
                if remaining > 0:
                    self.progress.update(task_id, advance=remaining)
            
            # Remove from active tasks after a short delay
            def remove_task():
                time.sleep(1)
                with self._lock:
                    if self.active and self.progress and name in self.tasks:
                        self.progress.remove_task(self.tasks[name])
                        del self.tasks[name]
            
            threading.Thread(target=remove_task, daemon=True).start()
    
    def remove_task(self, name: str) -> None:
        """Remove a progress task."""
        with self._lock:
            if not self.active or not self.progress or name not in self.tasks:
                return
            
            self.progress.remove_task(self.tasks[name])
            del self.tasks[name]
    
    @contextmanager
    def task(self, name: str, description: str, total: Optional[int] = None):
        """Context manager for a progress task."""
        task_name = self.add_task(name, description, total)
        try:
            yield ProgressTaskContext(self, task_name)
        finally:
            self.complete_task(task_name)
    
    def is_active(self) -> bool:
        """Check if progress display is active."""
        return self.active


class ProgressTaskContext:
    """Context for updating a specific progress task."""
    
    def __init__(self, manager: ProgressManager, task_name: str):
        self.manager = manager
        self.task_name = task_name
    
    def update(self, advance: int = 1, description: Optional[str] = None, **kwargs) -> None:
        """Update the task progress."""
        self.manager.update_task(self.task_name, advance, description, **kwargs)
    
    def set_total(self, total: int) -> None:
        """Set the total for the task."""
        self.manager.update_task(self.task_name, advance=0, total=total)
    
    def set_description(self, description: str) -> None:
        """Set the task description."""
        self.manager.update_task(self.task_name, advance=0, description=description)


class SimpleSpinner:
    """Simple spinner for basic progress indication."""
    
    def __init__(self, description: str = "Processing", console: Optional[Console] = None):
        self.description = description
        self.console = console or Console()
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.current_char = 0
        self.active = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def start(self) -> None:
        """Start the spinner."""
        if self.active:
            return
        
        self.active = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()
    
    def stop(self) -> None:
        """Stop the spinner."""
        if not self.active:
            return
        
        self.active = False
        self._stop_event.set()
        
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None
        
        # Clear the spinner line
        self.console.print("\r" + " " * (len(self.description) + 10) + "\r", end="")
    
    def _spin(self) -> None:
        """Spinner animation loop."""
        while not self._stop_event.is_set():
            char = self.spinner_chars[self.current_char]
            self.console.print(f"\r{char} {self.description}", end="", style="cyan")
            self.current_char = (self.current_char + 1) % len(self.spinner_chars)
            time.sleep(0.1)
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


@contextmanager
def progress_context(
    console: Optional[Console] = None,
    config: Optional[ProgressConfig] = None,
    auto_start: bool = True
):
    """Context manager for progress operations."""
    manager = ProgressManager(console, config)
    
    if auto_start:
        manager.start()
    
    try:
        yield manager
    finally:
        if manager.is_active():
            manager.stop()


def with_progress(
    description: str,
    total: Optional[int] = None,
    console: Optional[Console] = None
):
    """Decorator for functions that should show progress."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with progress_context(console=console) as progress:
                with progress.task("main", description, total) as task:
                    # Inject progress task into function if it accepts it
                    import inspect
                    sig = inspect.signature(func)
                    if 'progress_task' in sig.parameters:
                        kwargs['progress_task'] = task
                    
                    return func(*args, **kwargs)
        return wrapper
    return decorator


class ProgressCallback:
    """Callback interface for progress updates."""
    
    def __init__(self, task_context: Optional[ProgressTaskContext] = None):
        self.task_context = task_context
        self.current = 0
        self.total: Optional[int] = None
    
    def set_total(self, total: int) -> None:
        """Set the total number of items."""
        self.total = total
        if self.task_context:
            self.task_context.set_total(total)
    
    def update(self, increment: int = 1, description: Optional[str] = None) -> None:
        """Update progress by increment."""
        self.current += increment
        if self.task_context:
            self.task_context.update(increment, description)
    
    def set_description(self, description: str) -> None:
        """Set the current description."""
        if self.task_context:
            self.task_context.set_description(description)
    
    def get_percentage(self) -> float:
        """Get current percentage complete."""
        if self.total is None or self.total == 0:
            return 0.0
        return min(100.0, (self.current / self.total) * 100.0)
    
    def is_complete(self) -> bool:
        """Check if progress is complete."""
        return self.total is not None and self.current >= self.total


# Global progress manager instance
_global_progress_manager: Optional[ProgressManager] = None


def get_global_progress_manager() -> ProgressManager:
    """Get the global progress manager instance."""
    global _global_progress_manager
    if _global_progress_manager is None:
        _global_progress_manager = ProgressManager()
    return _global_progress_manager


def start_global_progress() -> None:
    """Start the global progress manager."""
    get_global_progress_manager().start()


def stop_global_progress() -> None:
    """Stop the global progress manager."""
    global _global_progress_manager
    if _global_progress_manager:
        _global_progress_manager.stop()
        _global_progress_manager = None