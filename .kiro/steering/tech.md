# Technology Stack

## Build System & Package Management

- **Build system**: setuptools with `pyproject.toml` configuration
- **Python version**: Requires Python 3.10+
- **Package structure**: Source layout with `src/term_coder/` package directory
- **Entry point**: CLI accessible via `tc` command after installation

## Core Dependencies

- **CLI Framework**: Typer with Rich for colorized terminal output
- **Configuration**: PyYAML for YAML config files
- **Git Integration**: GitPython for repository operations
- **Tokenization**: tiktoken for token counting and budget management
- **Embeddings**: sentence-transformers for semantic search (optional, falls back to hash-based)
- **Search**: ripgrep integration for fast lexical search

## Architecture Patterns

- **Modular design**: Clear separation between CLI, business logic, and external integrations
- **Adapter pattern**: LLM adapters for different model providers (OpenAI, Anthropic, local)
- **Plugin system**: Extensible architecture for custom tools and hooks
- **Safety-first**: All file modifications go through diff/patch review workflow
- **Streaming responses**: Real-time output for better user experience

## Common Commands

### Development Setup
```bash
# Install in development mode
pip install -e .

# Run tests
python -m pytest tests/

# Build package
python -m build
```

### Application Usage
```bash
# Initialize configuration
tc init

# Build search index
tc index

# Chat with repo context
tc chat "explain this function"

# Safe file editing workflow
tc edit "add error handling" --files src/module.py
tc diff  # Review proposed changes
tc apply # Apply after review

# Search repository
tc search "error handling" --semantic
tc search "TODO" --type py

# Git integration
tc review --range HEAD~3..HEAD
tc commit  # AI-generated commit message
```

## Configuration

- **Config location**: `.term-coder/config.yaml`
- **Default models**: gpt-4o-mini (default), gpt-4.1 (heavy tasks)
- **Offline mode**: Configurable for privacy-conscious development
- **Safety settings**: Backup creation, confirmation prompts, file size limits
- **Formatters**: Configurable per-language (black/isort for Python, prettier for JS)

## Testing Strategy

- **Unit tests**: Individual component functionality with mocked dependencies
- **Integration tests**: End-to-end workflows in isolated test environments
- **Test utilities**: Custom fixtures for repository setup and command execution
- **Pytest framework**: Standard Python testing with fixtures and parametrization