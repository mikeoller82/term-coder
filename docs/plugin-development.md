# Plugin Development Guide

Learn how to create custom plugins to extend term-coder's functionality.

## Plugin System Overview

Term-coder's plugin system allows you to:

- Add new CLI commands
- Extend existing functionality
- Integrate with external tools
- Customize behavior for specific workflows
- Share functionality with the community

## Plugin Architecture

Plugins are Python modules that follow a specific structure and API. They can:

1. **Register Commands**: Add new CLI commands
2. **Hook into Events**: React to system events
3. **Extend Context**: Modify context selection
4. **Add Formatters**: Custom code formatting
5. **Integrate Tools**: Connect external services

## Getting Started

### Plugin Directory Structure

Create a plugin directory in your project:

```
.term-coder/plugins/
├── my_plugin/
│   ├── __init__.py
│   ├── plugin.py
│   ├── commands.py
│   └── config.yaml
└── another_plugin/
    ├── __init__.py
    └── plugin.py
```

### Basic Plugin Template

Create a basic plugin (`my_plugin/plugin.py`):

```python
from term_coder.plugins import Plugin, command, hook
from term_coder.plugins.types import PluginContext, CommandResult
import typer

class MyPlugin(Plugin):
    """Example plugin demonstrating basic functionality."""
    
    name = "my_plugin"
    version = "1.0.0"
    description = "An example plugin"
    author = "Your Name"
    
    def initialize(self, context: PluginContext) -> None:
        """Initialize the plugin."""
        self.context = context
        self.logger = context.get_logger(self.name)
        self.logger.info(f"Initializing {self.name} v{self.version}")
    
    @command("hello")
    def hello_command(
        self,
        name: str = typer.Argument("World", help="Name to greet"),
        count: int = typer.Option(1, "--count", "-c", help="Number of greetings")
    ) -> CommandResult:
        """Say hello to someone."""
        for i in range(count):
            self.context.console.print(f"Hello, {name}!")
        
        return CommandResult(success=True, message=f"Greeted {name} {count} times")
    
    @hook("before_edit")
    def before_edit_hook(self, files: list[str], instruction: str) -> None:
        """Hook called before editing files."""
        self.logger.info(f"About to edit {len(files)} files: {instruction}")
    
    @hook("after_edit")
    def after_edit_hook(self, files: list[str], success: bool) -> None:
        """Hook called after editing files."""
        status = "successfully" if success else "failed"
        self.logger.info(f"Edit {status} completed for {len(files)} files")

# Plugin entry point
def create_plugin() -> MyPlugin:
    return MyPlugin()
```

### Plugin Configuration

Create a configuration file (`my_plugin/config.yaml`):

```yaml
name: my_plugin
version: 1.0.0
description: An example plugin
author: Your Name
email: your.email@example.com
license: MIT
homepage: https://github.com/yourname/my-plugin

# Plugin metadata
metadata:
  category: utility
  tags:
    - example
    - demo
  
# Dependencies
dependencies:
  term_coder: ">=1.0.0"
  python: ">=3.10"
  packages:
    - requests>=2.25.0

# Configuration schema
config_schema:
  greeting_prefix:
    type: string
    default: "Hello"
    description: "Prefix for greetings"
  
  max_greetings:
    type: integer
    default: 10
    description: "Maximum number of greetings"

# Permissions required
permissions:
  - file_read
  - file_write
  - network_access
```

## Plugin API Reference

### Base Plugin Class

```python
from term_coder.plugins import Plugin

class MyPlugin(Plugin):
    # Required attributes
    name: str = "my_plugin"
    version: str = "1.0.0"
    description: str = "Plugin description"
    
    # Optional attributes
    author: str = "Author Name"
    license: str = "MIT"
    homepage: str = "https://example.com"
    
    def initialize(self, context: PluginContext) -> None:
        """Called when plugin is loaded."""
        pass
    
    def cleanup(self) -> None:
        """Called when plugin is unloaded."""
        pass
```

### Command Registration

Use the `@command` decorator to register CLI commands:

```python
from term_coder.plugins import command
import typer

@command("my-command")
def my_command(
    arg1: str = typer.Argument(..., help="Required argument"),
    option1: str = typer.Option("default", help="Optional parameter")
) -> CommandResult:
    """Command description."""
    # Command implementation
    return CommandResult(success=True, data={"result": "success"})

# Command with subcommands
@command("my-group")
def my_group():
    """Command group description."""
    pass

@my_group.command("sub1")
def sub_command():
    """Subcommand description."""
    pass
```

### Event Hooks

React to system events with the `@hook` decorator:

```python
from term_coder.plugins import hook

@hook("before_edit")
def before_edit(files: list[str], instruction: str) -> None:
    """Called before editing files."""
    pass

@hook("after_edit")
def after_edit(files: list[str], success: bool, changes: dict) -> None:
    """Called after editing files."""
    pass

@hook("before_search")
def before_search(query: str, options: dict) -> dict:
    """Called before search. Can modify search options."""
    return options

@hook("after_search")
def after_search(query: str, results: list) -> list:
    """Called after search. Can modify results."""
    return results
```

### Available Hooks

| Hook Name | When Called | Parameters |
|-----------|-------------|------------|
| `before_edit` | Before editing files | `files`, `instruction` |
| `after_edit` | After editing files | `files`, `success`, `changes` |
| `before_search` | Before searching | `query`, `options` |
| `after_search` | After searching | `query`, `results` |
| `before_chat` | Before chat processing | `message`, `context` |
| `after_chat` | After chat processing | `message`, `response` |
| `before_commit` | Before git commit | `files`, `message` |
| `after_commit` | After git commit | `commit_hash`, `success` |
| `file_changed` | When files change | `file_path`, `change_type` |
| `config_changed` | When config changes | `key`, `old_value`, `new_value` |

### Context Access

The plugin context provides access to term-coder's functionality:

```python
def initialize(self, context: PluginContext) -> None:
    # Console for output
    self.console = context.console
    
    # Configuration access
    self.config = context.config
    
    # Logger
    self.logger = context.get_logger(self.name)
    
    # File system utilities
    self.fs = context.file_system
    
    # Search engine
    self.search = context.search_engine
    
    # LLM orchestrator
    self.llm = context.llm_orchestrator
    
    # Git integration
    self.git = context.git_integration
```

## Advanced Plugin Examples

### Custom Search Provider

```python
from term_coder.plugins import Plugin, hook
from term_coder.search import SearchResult

class CustomSearchPlugin(Plugin):
    name = "custom_search"
    version = "1.0.0"
    description = "Custom search provider"
    
    @hook("before_search")
    def enhance_search(self, query: str, options: dict) -> dict:
        """Add custom search logic."""
        if query.startswith("api:"):
            # Custom API search
            options["search_type"] = "api"
            options["api_query"] = query[4:]
        return options
    
    @hook("after_search")
    def filter_results(self, query: str, results: list) -> list:
        """Filter and enhance search results."""
        if query.startswith("important:"):
            # Only return results from important files
            important_patterns = ["/src/", "/lib/", "/core/"]
            results = [
                r for r in results 
                if any(pattern in str(r.file_path) for pattern in important_patterns)
            ]
        return results
```

### Code Quality Plugin

```python
from term_coder.plugins import Plugin, command, hook
import subprocess
import json

class CodeQualityPlugin(Plugin):
    name = "code_quality"
    version = "1.0.0"
    description = "Code quality analysis and improvements"
    
    @command("quality")
    def quality_check(
        self,
        files: list[str] = typer.Option(None, "--files", help="Files to check"),
        fix: bool = typer.Option(False, "--fix", help="Auto-fix issues")
    ) -> CommandResult:
        """Run code quality checks."""
        if not files:
            files = self._get_changed_files()
        
        issues = []
        for file_path in files:
            file_issues = self._check_file_quality(file_path)
            issues.extend(file_issues)
            
            if fix and file_issues:
                self._fix_file_issues(file_path, file_issues)
        
        self._report_issues(issues)
        return CommandResult(
            success=len(issues) == 0,
            data={"issues": len(issues), "files_checked": len(files)}
        )
    
    @hook("after_edit")
    def auto_quality_check(self, files: list[str], success: bool) -> None:
        """Automatically check quality after edits."""
        if success and self.config.get("auto_check", True):
            self.quality_check(files=files)
    
    def _check_file_quality(self, file_path: str) -> list:
        """Check quality of a single file."""
        issues = []
        
        # Example: Check line length
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if len(line) > 100:
                    issues.append({
                        "file": file_path,
                        "line": line_num,
                        "type": "line_too_long",
                        "message": f"Line {line_num} is {len(line)} characters long"
                    })
        
        return issues
```

### Integration Plugin

```python
from term_coder.plugins import Plugin, command
import requests

class JiraIntegrationPlugin(Plugin):
    name = "jira_integration"
    version = "1.0.0"
    description = "JIRA integration for issue tracking"
    
    def initialize(self, context: PluginContext) -> None:
        super().initialize(context)
        self.jira_url = self.config.get("jira_url")
        self.api_token = self.config.get("api_token")
    
    @command("jira")
    def jira_command(self):
        """JIRA integration commands."""
        pass
    
    @jira_command.command("create-issue")
    def create_issue(
        self,
        title: str = typer.Argument(..., help="Issue title"),
        description: str = typer.Option("", help="Issue description"),
        issue_type: str = typer.Option("Bug", help="Issue type")
    ) -> CommandResult:
        """Create a JIRA issue."""
        
        # Get current git context
        git_info = self._get_git_context()
        
        # Create issue payload
        payload = {
            "fields": {
                "project": {"key": self.config.get("project_key")},
                "summary": title,
                "description": f"{description}\n\nGit context:\n{git_info}",
                "issuetype": {"name": issue_type}
            }
        }
        
        # Make API request
        response = requests.post(
            f"{self.jira_url}/rest/api/2/issue",
            json=payload,
            auth=(self.config.get("username"), self.api_token)
        )
        
        if response.status_code == 201:
            issue_key = response.json()["key"]
            self.console.print(f"[green]Created issue: {issue_key}[/green]")
            return CommandResult(success=True, data={"issue_key": issue_key})
        else:
            self.console.print(f"[red]Failed to create issue: {response.text}[/red]")
            return CommandResult(success=False, message=response.text)
```

## Plugin Configuration

### Plugin-Specific Settings

Plugins can define their own configuration schema:

```python
# In plugin.py
class MyPlugin(Plugin):
    def get_config_schema(self) -> dict:
        return {
            "api_endpoint": {
                "type": "string",
                "required": True,
                "description": "API endpoint URL"
            },
            "timeout": {
                "type": "integer",
                "default": 30,
                "description": "Request timeout in seconds"
            },
            "enabled_features": {
                "type": "array",
                "items": {"type": "string"},
                "default": ["feature1", "feature2"],
                "description": "List of enabled features"
            }
        }
```

### User Configuration

Users can configure plugins in their main config file:

```yaml
# .term-coder/config.yaml
plugins:
  my_plugin:
    api_endpoint: "https://api.example.com"
    timeout: 60
    enabled_features:
      - "feature1"
      - "feature3"
```

## Testing Plugins

### Unit Testing

```python
# tests/test_my_plugin.py
import pytest
from unittest.mock import Mock
from my_plugin.plugin import MyPlugin
from term_coder.plugins.types import PluginContext

def test_plugin_initialization():
    context = Mock(spec=PluginContext)
    plugin = MyPlugin()
    plugin.initialize(context)
    
    assert plugin.context == context
    assert plugin.name == "my_plugin"

def test_hello_command():
    plugin = MyPlugin()
    context = Mock(spec=PluginContext)
    plugin.initialize(context)
    
    result = plugin.hello_command("Test", count=2)
    
    assert result.success is True
    assert "Test" in result.message
```

### Integration Testing

```python
# tests/test_integration.py
import subprocess
import tempfile
from pathlib import Path

def test_plugin_command_integration():
    """Test plugin command through CLI."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set up test environment
        config_dir = Path(tmpdir) / ".term-coder"
        config_dir.mkdir()
        
        # Install plugin
        plugin_dir = config_dir / "plugins" / "my_plugin"
        plugin_dir.mkdir(parents=True)
        
        # Copy plugin files
        # ... setup code ...
        
        # Test command
        result = subprocess.run(
            ["tc", "hello", "World"],
            cwd=tmpdir,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Hello, World!" in result.stdout
```

## Plugin Distribution

### Package Structure

Create a distributable plugin package:

```
my-term-coder-plugin/
├── setup.py
├── README.md
├── LICENSE
├── my_plugin/
│   ├── __init__.py
│   ├── plugin.py
│   └── config.yaml
└── tests/
    └── test_plugin.py
```

### Setup.py

```python
from setuptools import setup, find_packages

setup(
    name="my-term-coder-plugin",
    version="1.0.0",
    description="My custom term-coder plugin",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "term-coder>=1.0.0",
    ],
    entry_points={
        "term_coder.plugins": [
            "my_plugin = my_plugin.plugin:create_plugin",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
    ],
)
```

### Publishing

1. **Test locally**:
   ```bash
   pip install -e .
   tc plugins list
   ```

2. **Build package**:
   ```bash
   python setup.py sdist bdist_wheel
   ```

3. **Publish to PyPI**:
   ```bash
   twine upload dist/*
   ```

## Plugin Management

### Installing Plugins

```bash
# Install from PyPI
tc plugins install my-term-coder-plugin

# Install from Git
tc plugins install git+https://github.com/user/plugin.git

# Install locally
tc plugins install ./my-plugin/
```

### Managing Plugins

```bash
# List installed plugins
tc plugins list

# Enable/disable plugins
tc plugins enable my_plugin
tc plugins disable my_plugin

# Update plugins
tc plugins update my_plugin
tc plugins update --all

# Remove plugins
tc plugins remove my_plugin
```

### Plugin Configuration

```bash
# Configure plugin
tc plugins config my_plugin api_endpoint "https://api.example.com"

# View plugin config
tc plugins config my_plugin

# Reset plugin config
tc plugins config my_plugin --reset
```

## Best Practices

### 1. Follow Naming Conventions

- Plugin names: `snake_case`
- Commands: `kebab-case`
- Configuration keys: `snake_case`

### 2. Handle Errors Gracefully

```python
@command("my-command")
def my_command(self) -> CommandResult:
    try:
        # Command logic
        return CommandResult(success=True)
    except Exception as e:
        self.logger.error(f"Command failed: {e}")
        return CommandResult(success=False, message=str(e))
```

### 3. Respect User Privacy

```python
def initialize(self, context: PluginContext) -> None:
    # Check privacy settings
    if context.config.get("privacy.offline_mode"):
        self.disable_network_features()
    
    if not context.config.get("privacy.consent.analytics"):
        self.disable_analytics()
```

### 4. Provide Good Documentation

- Clear command descriptions
- Helpful examples
- Configuration documentation
- Error messages with suggestions

### 5. Test Thoroughly

- Unit tests for all functions
- Integration tests for CLI commands
- Test error conditions
- Test with different configurations

### 6. Version Compatibility

```python
class MyPlugin(Plugin):
    min_term_coder_version = "1.0.0"
    max_term_coder_version = "2.0.0"
    
    def check_compatibility(self, term_coder_version: str) -> bool:
        # Version compatibility check
        return self._version_in_range(term_coder_version)
```

## Debugging Plugins

### Enable Debug Logging

```yaml
# .term-coder/config.yaml
debug:
  enabled: true
  log_level: DEBUG
  
plugins:
  debug_mode: true
```

### Plugin Development Mode

```bash
# Enable development mode
export TERM_CODER_PLUGIN_DEBUG=true

# Reload plugins without restart
tc plugins reload my_plugin
```

### Common Issues

1. **Plugin not loading**
   - Check plugin directory structure
   - Verify `__init__.py` files
   - Check for syntax errors

2. **Commands not registering**
   - Ensure `@command` decorator is used
   - Check command name conflicts
   - Verify plugin is enabled

3. **Hooks not firing**
   - Check hook name spelling
   - Verify hook signature matches
   - Ensure plugin is initialized

## Community and Support

- **Plugin Registry**: Browse available plugins
- **Documentation**: Comprehensive API docs
- **Examples**: Sample plugins and templates
- **Support**: Community forums and GitHub issues
- **Contributing**: Guidelines for contributing to the plugin ecosystem

Happy plugin development! 🔌