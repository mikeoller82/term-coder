from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union
import logging
import subprocess
import shutil

from .errors import (
    TermCoderError, ErrorCategory, ErrorSeverity, ErrorContext,
    ConfigurationError, NetworkError, LLMAPIError, LSPError, GitError
)


@dataclass
class RetryConfig:
    """Configuration for retry mechanisms."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3


class CircuitBreakerState:
    """Circuit breaker state management."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.half_open_calls = 0
        self.logger = logging.getLogger("circuit_breaker")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with circuit breaker protection."""
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time > self.config.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
                self.logger.info("Circuit breaker transitioning to half-open")
            else:
                raise TermCoderError(
                    "Circuit breaker is open - service unavailable",
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.HIGH
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.config.half_open_max_calls:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.logger.info("Circuit breaker closed - service recovered")
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class RetryMechanism:
    """Retry mechanism with exponential backoff and jitter."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.logger = logging.getLogger("retry_mechanism")
    
    def execute(
        self,
        func: Callable,
        *args,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
        **kwargs
    ) -> Any:
        """Execute a function with retry logic."""
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                return func(*args, **kwargs)
            except retryable_exceptions as e:
                last_exception = e
                
                if attempt == self.config.max_attempts - 1:
                    # Last attempt failed
                    break
                
                delay = self._calculate_delay(attempt)
                self.logger.info(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}")
                time.sleep(delay)
        
        # All attempts failed
        raise TermCoderError(
            f"Operation failed after {self.config.max_attempts} attempts",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            cause=last_exception
        )
    
    async def execute_async(
        self,
        func: Callable,
        *args,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
        **kwargs
    ) -> Any:
        """Execute an async function with retry logic."""
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except retryable_exceptions as e:
                last_exception = e
                
                if attempt == self.config.max_attempts - 1:
                    break
                
                delay = self._calculate_delay(attempt)
                self.logger.info(f"Async attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}")
                await asyncio.sleep(delay)
        
        raise TermCoderError(
            f"Async operation failed after {self.config.max_attempts} attempts",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            cause=last_exception
        )
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the next retry attempt."""
        delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter
        
        return delay


class HealthChecker:
    """Health checker for system components."""
    
    def __init__(self):
        self.logger = logging.getLogger("health_checker")
        self.checks: Dict[str, Callable[[], bool]] = {}
        self.last_check_results: Dict[str, bool] = {}
        self.last_check_time: Dict[str, float] = {}
    
    def register_check(self, name: str, check_func: Callable[[], bool]) -> None:
        """Register a health check function."""
        self.checks[name] = check_func
    
    def run_check(self, name: str, cache_duration: float = 30.0) -> bool:
        """Run a specific health check."""
        current_time = time.time()
        
        # Use cached result if within cache duration
        if (name in self.last_check_time and 
            current_time - self.last_check_time[name] < cache_duration):
            return self.last_check_results.get(name, False)
        
        try:
            result = self.checks[name]()
            self.last_check_results[name] = result
            self.last_check_time[name] = current_time
            return result
        except Exception as e:
            self.logger.error(f"Health check '{name}' failed: {e}")
            self.last_check_results[name] = False
            self.last_check_time[name] = current_time
            return False
    
    def run_all_checks(self) -> Dict[str, bool]:
        """Run all registered health checks."""
        results = {}
        for name in self.checks:
            results[name] = self.run_check(name)
        return results
    
    def is_healthy(self) -> bool:
        """Check if all components are healthy."""
        results = self.run_all_checks()
        return all(results.values())


class ComponentRecovery:
    """Recovery mechanisms for specific components."""
    
    def __init__(self):
        self.logger = logging.getLogger("component_recovery")
        self.health_checker = HealthChecker()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_mechanisms: Dict[str, RetryMechanism] = {}
        
        # Set up default health checks
        self._setup_health_checks()
        
        # Set up default circuit breakers
        self._setup_circuit_breakers()
        
        # Set up default retry mechanisms
        self._setup_retry_mechanisms()
    
    def _setup_health_checks(self) -> None:
        """Set up health checks for various components."""
        
        # Configuration health check
        def check_config():
            try:
                from .config import Config
                Config.load()
                return True
            except Exception:
                return False
        
        self.health_checker.register_check("config", check_config)
        
        # File system health check
        def check_filesystem():
            try:
                test_file = Path(".term-coder/.health_check")
                test_file.parent.mkdir(parents=True, exist_ok=True)
                test_file.write_text("test")
                test_file.unlink()
                return True
            except Exception:
                return False
        
        self.health_checker.register_check("filesystem", check_filesystem)
        
        # Network health check
        def check_network():
            try:
                import socket
                socket.create_connection(("8.8.8.8", 53), timeout=3)
                return True
            except Exception:
                return False
        
        self.health_checker.register_check("network", check_network)
        
        # Git health check
        def check_git():
            try:
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
            except Exception:
                return False
        
        self.health_checker.register_check("git", check_git)
    
    def _setup_circuit_breakers(self) -> None:
        """Set up circuit breakers for external services."""
        
        # LLM API circuit breaker
        self.circuit_breakers["llm_api"] = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30.0,
                half_open_max_calls=2
            )
        )
        
        # LSP circuit breaker
        self.circuit_breakers["lsp"] = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60.0,
                half_open_max_calls=3
            )
        )
        
        # Network operations circuit breaker
        self.circuit_breakers["network"] = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=20.0,
                half_open_max_calls=2
            )
        )
    
    def _setup_retry_mechanisms(self) -> None:
        """Set up retry mechanisms for different operation types."""
        
        # Network operations retry
        self.retry_mechanisms["network"] = RetryMechanism(
            RetryConfig(
                max_attempts=3,
                base_delay=1.0,
                max_delay=10.0,
                exponential_base=2.0,
                jitter=True
            )
        )
        
        # File operations retry
        self.retry_mechanisms["file"] = RetryMechanism(
            RetryConfig(
                max_attempts=2,
                base_delay=0.5,
                max_delay=2.0,
                exponential_base=1.5,
                jitter=False
            )
        )
        
        # LLM API retry
        self.retry_mechanisms["llm_api"] = RetryMechanism(
            RetryConfig(
                max_attempts=3,
                base_delay=2.0,
                max_delay=30.0,
                exponential_base=2.0,
                jitter=True
            )
        )
    
    def recover_configuration(self, error: ConfigurationError) -> bool:
        """Recover from configuration errors."""
        self.logger.info("Attempting configuration recovery")
        
        try:
            # Check if config directory exists
            config_dir = Path(".term-coder")
            if not config_dir.exists():
                config_dir.mkdir(parents=True)
                self.logger.info("Created .term-coder directory")
            
            # Check if config file exists
            config_file = config_dir / "config.yaml"
            if not config_file.exists():
                from .config import ensure_initialized
                ensure_initialized()
                self.logger.info("Initialized default configuration")
                return True
            
            # Try to load and validate config
            from .config import Config
            config = Config.load()
            self.logger.info("Configuration loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration recovery failed: {e}")
            return False
    
    def recover_network_connection(self, error: NetworkError) -> bool:
        """Recover from network connection errors."""
        self.logger.info("Attempting network recovery")
        
        # Check basic connectivity
        if not self.health_checker.run_check("network"):
            self.logger.warning("Network connectivity check failed")
            return False
        
        # Test specific endpoints
        test_urls = [
            "https://api.openai.com",
            "https://api.anthropic.com",
            "https://httpbin.org/status/200"
        ]
        
        for url in test_urls:
            try:
                import urllib.request
                with urllib.request.urlopen(url, timeout=5) as response:
                    if response.status == 200:
                        self.logger.info(f"Successfully connected to {url}")
                        return True
            except Exception:
                continue
        
        self.logger.warning("All network connectivity tests failed")
        return False
    
    def recover_llm_api(self, error: LLMAPIError) -> bool:
        """Recover from LLM API errors."""
        self.logger.info("Attempting LLM API recovery")
        
        # Check API keys
        import os
        api_keys = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY")
        }
        
        available_keys = {k: v for k, v in api_keys.items() if v}
        
        if not available_keys:
            self.logger.warning("No API keys found - switching to mock mode")
            return True  # Mock mode is available
        
        # Test API connectivity
        for key_name, key_value in available_keys.items():
            if self._test_api_key(key_name, key_value):
                self.logger.info(f"API key {key_name} is working")
                return True
        
        self.logger.warning("All API keys failed - switching to mock mode")
        return True  # Mock mode fallback
    
    def _test_api_key(self, key_name: str, key_value: str) -> bool:
        """Test if an API key is working."""
        try:
            if key_name == "OPENAI_API_KEY":
                # Test OpenAI API
                import urllib.request
                import json
                
                req = urllib.request.Request(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {key_value}"}
                )
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    return response.status == 200
            
            elif key_name == "ANTHROPIC_API_KEY":
                # Test Anthropic API (simplified)
                return len(key_value) > 20  # Basic validation
            
        except Exception:
            return False
        
        return False
    
    def recover_lsp_server(self, error: LSPError) -> bool:
        """Recover from LSP server errors."""
        self.logger.info("Attempting LSP server recovery")
        
        # Check if LSP servers are installed
        lsp_servers = {
            "pylsp": ["python", "-m", "pylsp", "--help"],
            "typescript-language-server": ["typescript-language-server", "--version"],
            "rust-analyzer": ["rust-analyzer", "--version"],
            "gopls": ["gopls", "version"],
            "clangd": ["clangd", "--version"]
        }
        
        working_servers = []
        for server_name, test_command in lsp_servers.items():
            try:
                result = subprocess.run(
                    test_command,
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    working_servers.append(server_name)
                    self.logger.info(f"LSP server {server_name} is available")
            except Exception:
                continue
        
        if working_servers:
            self.logger.info(f"Found working LSP servers: {working_servers}")
            return True
        
        self.logger.warning("No LSP servers found - using fallback parsing")
        return True  # Fallback parsing is available
    
    def recover_git_repository(self, error: GitError) -> bool:
        """Recover from Git repository errors."""
        self.logger.info("Attempting Git repository recovery")
        
        try:
            # Check if we're in a git repository
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                self.logger.info("Git repository is available")
                return True
            
            # Not in a git repository - check if we can initialize one
            if "not a git repository" in error.message.lower():
                self.logger.info("Not in a git repository - some features will be limited")
                return True  # Non-git operations can continue
            
        except Exception as e:
            self.logger.error(f"Git recovery check failed: {e}")
        
        return False
    
    def recover_file_system(self, error: Exception) -> bool:
        """Recover from file system errors."""
        self.logger.info("Attempting file system recovery")
        
        # Check basic file system health
        if not self.health_checker.run_check("filesystem"):
            self.logger.error("File system health check failed")
            return False
        
        # Check disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage(".")
            free_gb = free // (1024**3)
            
            if free_gb < 1:
                self.logger.warning(f"Low disk space: {free_gb}GB free")
                return False
            
            self.logger.info(f"Disk space OK: {free_gb}GB free")
            return True
            
        except Exception as e:
            self.logger.error(f"Disk space check failed: {e}")
            return False
    
    def get_recovery_status(self) -> Dict[str, Any]:
        """Get the current recovery status of all components."""
        health_results = self.health_checker.run_all_checks()
        
        circuit_breaker_status = {}
        for name, cb in self.circuit_breakers.items():
            circuit_breaker_status[name] = {
                "state": cb.state,
                "failure_count": cb.failure_count,
                "last_failure": cb.last_failure_time
            }
        
        return {
            "health_checks": health_results,
            "circuit_breakers": circuit_breaker_status,
            "overall_health": all(health_results.values())
        }
    
    def run_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive diagnostics."""
        diagnostics = {
            "timestamp": time.time(),
            "health_status": self.get_recovery_status(),
            "system_info": self._get_system_info(),
            "dependencies": self._check_dependencies()
        }
        
        return diagnostics
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for diagnostics."""
        import platform
        import sys
        
        return {
            "platform": platform.platform(),
            "python_version": sys.version,
            "python_executable": sys.executable,
            "working_directory": str(Path.cwd()),
            "home_directory": str(Path.home())
        }
    
    def _check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are available."""
        dependencies = {}
        
        # Check Python packages
        python_packages = [
            "typer", "rich", "pyyaml", "gitpython", "tiktoken"
        ]
        
        for package in python_packages:
            try:
                __import__(package)
                dependencies[f"python_{package}"] = True
            except ImportError:
                dependencies[f"python_{package}"] = False
        
        # Check system commands
        system_commands = [
            "git", "python", "pip"
        ]
        
        for command in system_commands:
            dependencies[f"system_{command}"] = shutil.which(command) is not None
        
        return dependencies


# Global recovery instance
_global_recovery: Optional[ComponentRecovery] = None


def get_recovery_manager() -> ComponentRecovery:
    """Get the global recovery manager instance."""
    global _global_recovery
    if _global_recovery is None:
        _global_recovery = ComponentRecovery()
    return _global_recovery