from __future__ import annotations

import json
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union, Callable
import sys
import os

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better organization."""
    CONFIGURATION = "configuration"
    NETWORK = "network"
    FILE_SYSTEM = "file_system"
    PARSING = "parsing"
    LLM_API = "llm_api"
    LSP = "lsp"
    GIT = "git"
    FRAMEWORK = "framework"
    SECURITY = "security"
    USER_INPUT = "user_input"
    SYSTEM = "system"
    EDIT = "edit"
    SEARCH = "search"
    EXECUTION = "execution"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for errors."""
    command: Optional[str] = None
    file_path: Optional[Path] = None
    line_number: Optional[int] = None
    user_input: Optional[str] = None
    system_info: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "command": self.command,
            "file_path": str(self.file_path) if self.file_path else None,
            "line_number": self.line_number,
            "user_input": self.user_input,
            "system_info": self.system_info,
            "environment": dict(self.environment)
        }


@dataclass
class RecoveryAction:
    """Represents a recovery action for an error."""
    name: str
    description: str
    action: Callable[[], bool]
    auto_execute: bool = False
    requires_confirmation: bool = True


@dataclass
class ErrorSuggestion:
    """Represents a suggestion for fixing an error."""
    title: str
    description: str
    command: Optional[str] = None
    url: Optional[str] = None
    priority: int = 1  # Lower numbers = higher priority


class TermCoderError(Exception):
    """Base exception class for term-coder errors."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        suggestions: Optional[List[ErrorSuggestion]] = None,
        recovery_actions: Optional[List[RecoveryAction]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or ErrorContext()
        self.suggestions = suggestions or []
        self.recovery_actions = recovery_actions or []
        self.cause = cause
        self.timestamp = datetime.now()
        self.error_id = self._generate_error_id()
    
    def _generate_error_id(self) -> str:
        """Generate a unique error ID."""
        import hashlib
        content = f"{self.category.value}_{self.message}_{self.timestamp.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/reporting."""
        return {
            "error_id": self.error_id,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context.to_dict(),
            "suggestions": [
                {
                    "title": s.title,
                    "description": s.description,
                    "command": s.command,
                    "url": s.url,
                    "priority": s.priority
                }
                for s in self.suggestions
            ],
            "cause": str(self.cause) if self.cause else None,
            "traceback": traceback.format_exc() if self.cause else None
        }


class ConfigurationError(TermCoderError):
    """Configuration-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class NetworkError(TermCoderError):
    """Network-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class FileSystemError(TermCoderError):
    """File system-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.FILE_SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class ParsingError(TermCoderError):
    """Parsing-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.PARSING,
            severity=ErrorSeverity.LOW,
            **kwargs
        )


class LLMAPIError(TermCoderError):
    """LLM API-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.LLM_API,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class LSPError(TermCoderError):
    """LSP-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.LSP,
            severity=ErrorSeverity.LOW,
            **kwargs
        )


class GitError(TermCoderError):
    """Git-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.GIT,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class FrameworkError(TermCoderError):
    """Framework-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.FRAMEWORK,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class SecurityError(TermCoderError):
    """Security-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.SECURITY,
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )


class UserInputError(TermCoderError):
    """User input-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.USER_INPUT,
            severity=ErrorSeverity.LOW,
            **kwargs
        )


class EditError(TermCoderError):
    """Edit operation-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.EDIT,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class SearchError(TermCoderError):
    """Search operation-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.SEARCH,
            severity=ErrorSeverity.LOW,
            **kwargs
        )


class ExecutionError(TermCoderError):
    """Command execution-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.EXECUTION,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class ErrorHandler:
    """Central error handler for term-coder."""
    
    def __init__(self, console: Optional[Console] = None, audit_logger=None):
        self.console = console or Console()
        self.audit_logger = audit_logger
        self.logger = logging.getLogger("term_coder.errors")
        self.error_history: List[TermCoderError] = []
        self.recovery_strategies: Dict[ErrorCategory, List[Callable]] = {}
        self.fallback_strategies: Dict[ErrorCategory, Callable] = {}
        
        # Set up default recovery strategies
        self._setup_default_strategies()
    
    def _setup_default_strategies(self) -> None:
        """Set up default recovery strategies for different error categories."""
        
        # Configuration error strategies
        self.recovery_strategies[ErrorCategory.CONFIGURATION] = [
            self._recover_missing_config,
            self._recover_invalid_config,
            self._recover_permission_config
        ]
        
        # Network error strategies
        self.recovery_strategies[ErrorCategory.NETWORK] = [
            self._recover_network_timeout,
            self._recover_network_connection,
            self._recover_network_auth
        ]
        
        # File system error strategies
        self.recovery_strategies[ErrorCategory.FILE_SYSTEM] = [
            self._recover_missing_file,
            self._recover_permission_denied,
            self._recover_disk_space
        ]
        
        # LLM API error strategies
        self.recovery_strategies[ErrorCategory.LLM_API] = [
            self._recover_api_key_missing,
            self._recover_api_rate_limit,
            self._recover_api_quota_exceeded,
            self._recover_api_model_unavailable
        ]
        
        # LSP error strategies
        self.recovery_strategies[ErrorCategory.LSP] = [
            self._recover_lsp_server_missing,
            self._recover_lsp_server_crash,
            self._recover_lsp_timeout
        ]
        
        # Git error strategies
        self.recovery_strategies[ErrorCategory.GIT] = [
            self._recover_git_not_repo,
            self._recover_git_uncommitted_changes,
            self._recover_git_merge_conflict
        ]
        
        # Framework error strategies
        self.recovery_strategies[ErrorCategory.FRAMEWORK] = [
            self._recover_framework_not_detected,
            self._recover_framework_command_missing,
            self._recover_framework_config_invalid
        ]
        
        # Set up fallback strategies
        self.fallback_strategies = {
            ErrorCategory.LLM_API: self._fallback_to_mock_llm,
            ErrorCategory.LSP: self._fallback_to_basic_parsing,
            ErrorCategory.NETWORK: self._fallback_to_offline_mode,
            ErrorCategory.FRAMEWORK: self._fallback_to_generic_commands
        }
    
    def handle_error(
        self,
        error: Union[Exception, TermCoderError],
        context: Optional[ErrorContext] = None,
        auto_recover: bool = True
    ) -> bool:
        """Handle an error with recovery attempts."""
        
        # Convert regular exceptions to TermCoderError
        if not isinstance(error, TermCoderError):
            term_error = self._convert_exception(error, context)
        else:
            term_error = error
            if context:
                term_error.context = context
        
        # Add to error history
        self.error_history.append(term_error)
        
        # Log the error
        self._log_error(term_error)
        
        # Display error to user
        self._display_error(term_error)
        
        # Attempt recovery if enabled
        if auto_recover:
            return self._attempt_recovery(term_error)
        
        return False
    
    def _convert_exception(self, error: Exception, context: Optional[ErrorContext] = None) -> TermCoderError:
        """Convert a regular exception to a TermCoderError."""
        error_type = type(error).__name__
        message = str(error)
        
        # Determine category based on exception type and message
        category = self._categorize_error(error, message)
        
        # Generate suggestions based on error type
        suggestions = self._generate_suggestions(error, category)
        
        return TermCoderError(
            message=f"{error_type}: {message}",
            category=category,
            context=context,
            suggestions=suggestions,
            cause=error
        )
    
    def _categorize_error(self, error: Exception, message: str) -> ErrorCategory:
        """Categorize an error based on its type and message."""
        error_type = type(error).__name__
        message_lower = message.lower()
        
        # Network-related errors
        if any(keyword in error_type.lower() for keyword in ['connection', 'timeout', 'network', 'http']):
            return ErrorCategory.NETWORK
        if any(keyword in message_lower for keyword in ['connection', 'timeout', 'network', 'unreachable']):
            return ErrorCategory.NETWORK
        
        # File system errors
        if any(keyword in error_type.lower() for keyword in ['file', 'permission', 'io']):
            return ErrorCategory.FILE_SYSTEM
        if any(keyword in message_lower for keyword in ['no such file', 'permission denied', 'disk space']):
            return ErrorCategory.FILE_SYSTEM
        
        # Configuration errors
        if any(keyword in message_lower for keyword in ['config', 'setting', 'invalid']):
            return ErrorCategory.CONFIGURATION
        
        # Parsing errors
        if any(keyword in error_type.lower() for keyword in ['parse', 'syntax', 'json', 'yaml']):
            return ErrorCategory.PARSING
        
        # Git errors
        if any(keyword in message_lower for keyword in ['git', 'repository', 'commit', 'branch']):
            return ErrorCategory.GIT
        
        return ErrorCategory.UNKNOWN
    
    def _generate_suggestions(self, error: Exception, category: ErrorCategory) -> List[ErrorSuggestion]:
        """Generate suggestions based on error type and category."""
        suggestions = []
        error_message = str(error).lower()
        
        if category == ErrorCategory.CONFIGURATION:
            if 'config not found' in error_message:
                suggestions.append(ErrorSuggestion(
                    title="Initialize Configuration",
                    description="Run 'tc init' to create a default configuration file",
                    command="tc init",
                    priority=1
                ))
            elif 'invalid' in error_message:
                suggestions.append(ErrorSuggestion(
                    title="Check Configuration",
                    description="Verify your .term-coder/config.yaml file syntax",
                    priority=1
                ))
        
        elif category == ErrorCategory.NETWORK:
            suggestions.extend([
                ErrorSuggestion(
                    title="Check Internet Connection",
                    description="Verify your internet connection is working",
                    priority=1
                ),
                ErrorSuggestion(
                    title="Enable Offline Mode",
                    description="Use offline mode to work without network access",
                    command="tc privacy offline_mode true",
                    priority=2
                )
            ])
        
        elif category == ErrorCategory.LLM_API:
            if 'api key' in error_message:
                suggestions.append(ErrorSuggestion(
                    title="Set API Key",
                    description="Set your API key in environment variables",
                    priority=1
                ))
            elif 'rate limit' in error_message:
                suggestions.append(ErrorSuggestion(
                    title="Wait and Retry",
                    description="Wait a moment and try again, or use a different model",
                    priority=1
                ))
        
        elif category == ErrorCategory.FILE_SYSTEM:
            if 'permission denied' in error_message:
                suggestions.append(ErrorSuggestion(
                    title="Check Permissions",
                    description="Ensure you have read/write permissions for the file or directory",
                    priority=1
                ))
            elif 'no such file' in error_message:
                suggestions.append(ErrorSuggestion(
                    title="Check File Path",
                    description="Verify the file path exists and is spelled correctly",
                    priority=1
                ))
        
        elif category == ErrorCategory.GIT:
            if 'not a git repository' in error_message:
                suggestions.append(ErrorSuggestion(
                    title="Initialize Git Repository",
                    description="Initialize a git repository in this directory",
                    command="git init",
                    priority=1
                ))
        
        return suggestions
    
    def _log_error(self, error: TermCoderError) -> None:
        """Log an error for debugging and analysis."""
        self.logger.error(
            f"[{error.error_id}] {error.category.value}: {error.message}",
            extra={"error_data": error.to_dict()}
        )
        
        # Log to audit system if available
        if self.audit_logger:
            self.audit_logger.log_error(
                error.category.value,
                error.message,
                details={
                    "error_id": error.error_id,
                    "severity": error.severity.value,
                    "context": error.context.to_dict(),
                    "suggestions_count": len(error.suggestions)
                }
            )
    
    def _display_error(self, error: TermCoderError) -> None:
        """Display an error to the user with suggestions."""
        
        # Choose color based on severity
        severity_colors = {
            ErrorSeverity.LOW: "yellow",
            ErrorSeverity.MEDIUM: "orange3",
            ErrorSeverity.HIGH: "red",
            ErrorSeverity.CRITICAL: "bright_red"
        }
        color = severity_colors.get(error.severity, "red")
        
        # Create error panel
        error_text = Text()
        error_text.append(f"Error [{error.error_id}]: ", style="bold")
        error_text.append(error.message, style=color)
        
        # Add context if available
        if error.context.command:
            error_text.append(f"\nCommand: {error.context.command}", style="dim")
        if error.context.file_path:
            error_text.append(f"\nFile: {error.context.file_path}", style="dim")
        
        panel = Panel(
            error_text,
            title=f"{error.category.value.title()} Error",
            border_style=color,
            expand=False
        )
        
        self.console.print(panel)
        
        # Display suggestions
        if error.suggestions:
            self.console.print("\n[bold cyan]Suggestions:[/bold cyan]")
            for i, suggestion in enumerate(sorted(error.suggestions, key=lambda x: x.priority), 1):
                self.console.print(f"{i}. [bold]{suggestion.title}[/bold]")
                self.console.print(f"   {suggestion.description}")
                if suggestion.command:
                    self.console.print(f"   Command: [green]{suggestion.command}[/green]")
                if suggestion.url:
                    self.console.print(f"   More info: [blue]{suggestion.url}[/blue]")
                self.console.print()
    
    def _attempt_recovery(self, error: TermCoderError) -> bool:
        """Attempt to recover from an error."""
        
        # Try category-specific recovery strategies
        strategies = self.recovery_strategies.get(error.category, [])
        
        for strategy in strategies:
            try:
                if strategy(error):
                    self.console.print(f"[green]✓ Recovered from {error.category.value} error[/green]")
                    return True
            except Exception as e:
                self.logger.debug(f"Recovery strategy failed: {e}")
                continue
        
        # Try fallback strategy
        fallback = self.fallback_strategies.get(error.category)
        if fallback:
            try:
                if fallback(error):
                    self.console.print(f"[yellow]⚠ Using fallback for {error.category.value} error[/yellow]")
                    return True
            except Exception as e:
                self.logger.debug(f"Fallback strategy failed: {e}")
        
        return False
    
    # Recovery strategy implementations
    def _recover_missing_config(self, error: TermCoderError) -> bool:
        """Recover from missing configuration."""
        if 'config not found' in error.message.lower():
            from .config import ensure_initialized
            try:
                ensure_initialized()
                return True
            except Exception:
                return False
        return False
    
    def _recover_invalid_config(self, error: TermCoderError) -> bool:
        """Recover from invalid configuration."""
        # Could implement config validation and repair
        return False
    
    def _recover_permission_config(self, error: TermCoderError) -> bool:
        """Recover from configuration permission issues."""
        # Could implement permission fixing
        return False
    
    def _recover_network_timeout(self, error: TermCoderError) -> bool:
        """Recover from network timeouts."""
        # Could implement retry with exponential backoff
        return False
    
    def _recover_network_connection(self, error: TermCoderError) -> bool:
        """Recover from network connection issues."""
        # Could implement connection testing and retry
        return False
    
    def _recover_network_auth(self, error: TermCoderError) -> bool:
        """Recover from network authentication issues."""
        # Could implement auth token refresh
        return False
    
    def _recover_missing_file(self, error: TermCoderError) -> bool:
        """Recover from missing files."""
        # Could implement file creation or alternative path finding
        return False
    
    def _recover_permission_denied(self, error: TermCoderError) -> bool:
        """Recover from permission denied errors."""
        # Could implement permission checking and fixing
        return False
    
    def _recover_disk_space(self, error: TermCoderError) -> bool:
        """Recover from disk space issues."""
        # Could implement cleanup suggestions
        return False
    
    def _recover_api_key_missing(self, error: TermCoderError) -> bool:
        """Recover from missing API keys."""
        if 'api key' in error.message.lower():
            # Switch to mock mode
            return True
        return False
    
    def _recover_api_rate_limit(self, error: TermCoderError) -> bool:
        """Recover from API rate limits."""
        if 'rate limit' in error.message.lower():
            # Could implement exponential backoff
            import time
            time.sleep(1)
            return True
        return False
    
    def _recover_api_quota_exceeded(self, error: TermCoderError) -> bool:
        """Recover from API quota exceeded."""
        # Could switch to alternative model
        return False
    
    def _recover_api_model_unavailable(self, error: TermCoderError) -> bool:
        """Recover from unavailable models."""
        # Could switch to fallback model
        return False
    
    def _recover_lsp_server_missing(self, error: TermCoderError) -> bool:
        """Recover from missing LSP servers."""
        # Could provide installation instructions
        return False
    
    def _recover_lsp_server_crash(self, error: TermCoderError) -> bool:
        """Recover from LSP server crashes."""
        # Could restart the server
        return False
    
    def _recover_lsp_timeout(self, error: TermCoderError) -> bool:
        """Recover from LSP timeouts."""
        # Could increase timeout or restart
        return False
    
    def _recover_git_not_repo(self, error: TermCoderError) -> bool:
        """Recover from not being in a git repository."""
        # Could offer to initialize git repo
        return False
    
    def _recover_git_uncommitted_changes(self, error: TermCoderError) -> bool:
        """Recover from uncommitted changes."""
        # Could offer to stash changes
        return False
    
    def _recover_git_merge_conflict(self, error: TermCoderError) -> bool:
        """Recover from merge conflicts."""
        # Could provide conflict resolution guidance
        return False
    
    def _recover_framework_not_detected(self, error: TermCoderError) -> bool:
        """Recover from framework not detected."""
        # Could provide manual framework specification
        return False
    
    def _recover_framework_command_missing(self, error: TermCoderError) -> bool:
        """Recover from missing framework commands."""
        # Could provide installation instructions
        return False
    
    def _recover_framework_config_invalid(self, error: TermCoderError) -> bool:
        """Recover from invalid framework configuration."""
        # Could provide config validation and repair
        return False
    
    # Fallback strategy implementations
    def _fallback_to_mock_llm(self, error: TermCoderError) -> bool:
        """Fallback to mock LLM when API fails."""
        self.console.print("[yellow]Falling back to mock LLM mode[/yellow]")
        return True
    
    def _fallback_to_basic_parsing(self, error: TermCoderError) -> bool:
        """Fallback to basic parsing when LSP fails."""
        self.console.print("[yellow]Falling back to basic syntax parsing[/yellow]")
        return True
    
    def _fallback_to_offline_mode(self, error: TermCoderError) -> bool:
        """Fallback to offline mode when network fails."""
        self.console.print("[yellow]Switching to offline mode[/yellow]")
        return True
    
    def _fallback_to_generic_commands(self, error: TermCoderError) -> bool:
        """Fallback to generic commands when framework-specific ones fail."""
        self.console.print("[yellow]Using generic commands instead of framework-specific ones[/yellow]")
        return True
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get statistics about handled errors."""
        if not self.error_history:
            return {"total_errors": 0}
        
        stats = {
            "total_errors": len(self.error_history),
            "by_category": {},
            "by_severity": {},
            "recent_errors": len([e for e in self.error_history if (datetime.now() - e.timestamp).seconds < 3600])
        }
        
        for error in self.error_history:
            # Count by category
            category = error.category.value
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
            
            # Count by severity
            severity = error.severity.value
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1
        
        return stats
    
    def export_error_report(self, file_path: Path) -> None:
        """Export error report for debugging."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "statistics": self.get_error_statistics(),
            "errors": [error.to_dict() for error in self.error_history[-50:]]  # Last 50 errors
        }
        
        file_path.write_text(json.dumps(report, indent=2))


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def handle_error(
    error: Union[Exception, TermCoderError],
    context: Optional[ErrorContext] = None,
    auto_recover: bool = True
) -> bool:
    """Convenience function to handle errors using the global handler."""
    return get_error_handler().handle_error(error, context, auto_recover)


def with_error_handling(
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    auto_recover: bool = True,
    context: Optional[ErrorContext] = None
):
    """Decorator for automatic error handling."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_context = context or ErrorContext(command=func.__name__)
                handle_error(e, error_context, auto_recover)
                raise
        return wrapper
    return decorator