from __future__ import annotations

import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from term_coder.errors import (
    TermCoderError, ErrorCategory, ErrorSeverity, ErrorContext,
    ConfigurationError, NetworkError, LLMAPIError, LSPError,
    ErrorHandler, ErrorSuggestion, RecoveryAction
)
from term_coder.recovery import (
    ComponentRecovery, RetryMechanism, RetryConfig,
    CircuitBreaker, CircuitBreakerConfig, HealthChecker
)


class TestTermCoderError:
    """Test TermCoderError functionality."""
    
    def test_error_creation(self):
        """Test basic error creation."""
        error = TermCoderError(
            "Test error message",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH
        )
        
        assert error.message == "Test error message"
        assert error.category == ErrorCategory.CONFIGURATION
        assert error.severity == ErrorSeverity.HIGH
        assert error.error_id is not None
        assert len(error.error_id) == 8
    
    def test_error_with_context(self):
        """Test error with context information."""
        context = ErrorContext(
            command="test_command",
            file_path=Path("/test/file.py"),
            line_number=42,
            user_input="test input"
        )
        
        error = TermCoderError(
            "Test error with context",
            context=context
        )
        
        assert error.context.command == "test_command"
        assert error.context.file_path == Path("/test/file.py")
        assert error.context.line_number == 42
        assert error.context.user_input == "test input"
    
    def test_error_with_suggestions(self):
        """Test error with suggestions."""
        suggestions = [
            ErrorSuggestion(
                title="Fix Configuration",
                description="Run tc init to fix configuration",
                command="tc init",
                priority=1
            )
        ]
        
        error = TermCoderError(
            "Configuration error",
            suggestions=suggestions
        )
        
        assert len(error.suggestions) == 1
        assert error.suggestions[0].title == "Fix Configuration"
        assert error.suggestions[0].command == "tc init"
    
    def test_error_serialization(self):
        """Test error serialization to dictionary."""
        context = ErrorContext(command="test")
        error = TermCoderError(
            "Test error",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            context=context
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["message"] == "Test error"
        assert error_dict["category"] == "network"
        assert error_dict["severity"] == "medium"
        assert error_dict["error_id"] == error.error_id
        assert "timestamp" in error_dict
        assert "context" in error_dict


class TestSpecificErrors:
    """Test specific error types."""
    
    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Config file not found")
        
        assert error.category == ErrorCategory.CONFIGURATION
        assert error.severity == ErrorSeverity.HIGH
        assert "Config file not found" in error.message
    
    def test_network_error(self):
        """Test NetworkError."""
        error = NetworkError("Connection timeout")
        
        assert error.category == ErrorCategory.NETWORK
        assert error.severity == ErrorSeverity.MEDIUM
        assert "Connection timeout" in error.message
    
    def test_llm_api_error(self):
        """Test LLMAPIError."""
        error = LLMAPIError("API key invalid")
        
        assert error.category == ErrorCategory.LLM_API
        assert error.severity == ErrorSeverity.HIGH
        assert "API key invalid" in error.message
    
    def test_lsp_error(self):
        """Test LSPError."""
        error = LSPError("Language server crashed")
        
        assert error.category == ErrorCategory.LSP
        assert error.severity == ErrorSeverity.LOW
        assert "Language server crashed" in error.message


class TestErrorHandler:
    """Test ErrorHandler functionality."""
    
    def test_error_handler_initialization(self):
        """Test error handler initialization."""
        handler = ErrorHandler()
        
        assert handler.console is not None
        assert isinstance(handler.error_history, list)
        assert isinstance(handler.recovery_strategies, dict)
        assert isinstance(handler.fallback_strategies, dict)
    
    def test_handle_term_coder_error(self):
        """Test handling TermCoderError."""
        handler = ErrorHandler()
        error = TermCoderError("Test error")
        
        # Mock display and logging
        with patch.object(handler, '_display_error') as mock_display, \
             patch.object(handler, '_log_error') as mock_log, \
             patch.object(handler, '_attempt_recovery', return_value=True) as mock_recovery:
            
            result = handler.handle_error(error)
            
            assert result == True
            mock_display.assert_called_once_with(error)
            mock_log.assert_called_once_with(error)
            mock_recovery.assert_called_once_with(error)
            assert error in handler.error_history
    
    def test_handle_regular_exception(self):
        """Test handling regular Python exceptions."""
        handler = ErrorHandler()
        exception = ValueError("Test value error")
        
        with patch.object(handler, '_display_error') as mock_display, \
             patch.object(handler, '_log_error') as mock_log, \
             patch.object(handler, '_attempt_recovery', return_value=False) as mock_recovery:
            
            result = handler.handle_error(exception)
            
            assert result == False
            mock_display.assert_called_once()
            mock_log.assert_called_once()
            mock_recovery.assert_called_once()
            assert len(handler.error_history) == 1
            assert isinstance(handler.error_history[0], TermCoderError)
    
    def test_error_categorization(self):
        """Test automatic error categorization."""
        handler = ErrorHandler()
        
        # Network error
        network_error = ConnectionError("Connection failed")
        term_error = handler._convert_exception(network_error)
        assert term_error.category == ErrorCategory.NETWORK
        
        # File system error
        file_error = FileNotFoundError("File not found")
        term_error = handler._convert_exception(file_error)
        assert term_error.category == ErrorCategory.FILE_SYSTEM
        
        # Permission error
        perm_error = PermissionError("Permission denied")
        term_error = handler._convert_exception(perm_error)
        assert term_error.category == ErrorCategory.FILE_SYSTEM
    
    def test_suggestion_generation(self):
        """Test automatic suggestion generation."""
        handler = ErrorHandler()
        
        # Configuration error
        config_error = Exception("config not found")
        suggestions = handler._generate_suggestions(config_error, ErrorCategory.CONFIGURATION)
        
        assert len(suggestions) > 0
        assert any("tc init" in s.command for s in suggestions if s.command)
        
        # Network error
        network_error = Exception("connection timeout")
        suggestions = handler._generate_suggestions(network_error, ErrorCategory.NETWORK)
        
        assert len(suggestions) > 0
        assert any("offline" in s.description.lower() for s in suggestions)
    
    def test_error_statistics(self):
        """Test error statistics collection."""
        handler = ErrorHandler()
        
        # Add some test errors
        handler.error_history.extend([
            TermCoderError("Error 1", category=ErrorCategory.NETWORK),
            TermCoderError("Error 2", category=ErrorCategory.NETWORK),
            TermCoderError("Error 3", category=ErrorCategory.CONFIGURATION),
            TermCoderError("Error 4", category=ErrorCategory.LLM_API, severity=ErrorSeverity.HIGH)
        ])
        
        stats = handler.get_error_statistics()
        
        assert stats["total_errors"] == 4
        assert stats["by_category"]["network"] == 2
        assert stats["by_category"]["configuration"] == 1
        assert stats["by_category"]["llm_api"] == 1
        assert stats["by_severity"]["high"] == 1
        assert stats["by_severity"]["medium"] == 3  # Default severity


if __name__ == "__main__":
    pytest.main([__file__])