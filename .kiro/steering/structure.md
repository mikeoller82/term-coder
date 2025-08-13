# Project Structure

## Directory Layout

```
term-coder/
├── .kiro/                    # Kiro IDE configuration
├── .term-coder/              # Application runtime data
│   ├── config.yaml          # Main configuration file
│   ├── index.tsv            # File index for search
│   ├── vectors.jsonl        # Semantic embeddings cache
│   └── sessions/            # Chat session history
├── src/term_coder/          # Main package (source layout)
│   ├── __init__.py          # Package exports
│   ├── cli.py               # Typer-based CLI commands
│   ├── config.py            # Configuration management
│   ├── context.py           # Context selection engine
│   ├── llm.py               # LLM orchestrator and adapters
│   ├── index.py             # File indexing system
│   ├── search.py            # Lexical search (ripgrep)
│   ├── semantic.py          # Semantic search (embeddings)
│   ├── editor.py            # Edit proposal generation
│   ├── patcher.py           # Patch application system
│   ├── runner.py            # Sandboxed command execution
│   ├── gittools.py          # Git integration
│   ├── agent.py             # Repo intent recognition
│   ├── fixer.py             # Error analysis and fixes
│   ├── tester.py            # Test runner integration
│   ├── explain.py           # Code explanation
│   ├── refactor.py          # Refactoring engine
│   ├── generator.py         # Code scaffolding
│   ├── prompts.py           # Prompt templates
│   ├── session.py           # Chat session management
│   ├── tokens.py            # Token counting utilities
│   └── utils.py             # Common utilities
├── tests/                   # Test suite
│   ├── test_context.py      # Context engine tests
│   ├── test_hybrid.py       # Hybrid search tests
│   ├── test_llm.py          # LLM adapter tests
│   └── test_semantic.py     # Semantic search tests
├── build/                   # Build artifacts
├── pyproject.toml           # Package configuration
├── design.md                # Architecture documentation
├── requirements.md          # Requirements specification
└── tasks.md                 # Implementation roadmap
```

## Code Organization Principles

### Module Responsibilities

- **cli.py**: Single entry point for all commands, minimal business logic
- **config.py**: Configuration loading, validation, and runtime management
- **context.py**: Intelligent file selection based on queries and budgets
- **llm.py**: Model abstraction layer with streaming support
- **index.py + search.py + semantic.py**: Three-tier search architecture
- **editor.py + patcher.py**: Safe editing workflow (propose → review → apply)
- **runner.py**: Sandboxed execution with resource limits
- **gittools.py**: Git operations and workflow assistance

### Naming Conventions

- **Classes**: PascalCase (e.g., `ContextEngine`, `LLMOrchestrator`)
- **Functions/methods**: snake_case (e.g., `select_context`, `build_index`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_CONFIG`, `CONFIG_PATH`)
- **Files**: snake_case matching primary class/function (e.g., `context.py` → `ContextEngine`)

### Import Patterns

- Use `from __future__ import annotations` for forward references
- Relative imports within package: `from .config import Config`
- External dependencies imported at module level
- Type hints using standard library types where possible

### Error Handling

- Custom exceptions inherit from built-in exceptions
- Graceful degradation for optional features (e.g., semantic search in offline mode)
- User-friendly error messages with actionable suggestions
- Comprehensive logging for debugging

### Configuration Management

- Single source of truth: `.term-coder/config.yaml`
- Hierarchical configuration with dot notation (e.g., `retrieval.max_tokens`)
- Runtime configuration updates via `tc config` command
- Environment-specific overrides supported

### Testing Structure

- Test files mirror source structure: `test_context.py` tests `context.py`
- Use pytest fixtures for common setup (temporary directories, mock configs)
- Integration tests use real file systems in isolated environments
- Mock external dependencies (LLM APIs, network calls) in unit tests