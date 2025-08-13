# Configuration Guide

Complete guide to configuring term-coder for your needs.

## Configuration File Location

Term-coder uses a YAML configuration file located at:

```
.term-coder/config.yaml
```

This file is created when you run `tc init` and contains all customizable settings.

## Configuration Structure

Here's a complete example configuration with all available options:

```yaml
# LLM Configuration
llm:
  # Default model to use for all operations
  default_model: "openai:gpt-4o-mini"

  # Model for heavy/complex tasks
  heavy_model: "openai:gpt-4o"

  # API Keys (use environment variables for security)
  openai_api_key: "${OPENAI_API_KEY}"
  anthropic_api_key: "${ANTHROPIC_API_KEY}"

  # Model-specific settings
  models:
    "openai:gpt-4o-mini":
      max_tokens: 4096
      temperature: 0.1
    "openai:gpt-4o":
      max_tokens: 8192
      temperature: 0.1
    "anthropic:claude-3-sonnet":
      max_tokens: 4096
      temperature: 0.1

# Privacy and Security Settings
privacy:
  # Enable offline mode (no external API calls)
  offline_mode: false

  # Automatically redact secrets in logs and outputs
  redact_secrets: true

  # Audit logging level: minimal, standard, detailed
  audit_level: "standard"

  # Data usage consent
  consent:
    data_collection: true
    analytics: false
    model_training: false
    error_reporting: true

# Context and Retrieval Settings
retrieval:
  # Maximum tokens to include in context
  max_tokens: 8000

  # Weight for hybrid search (0.0 = pure lexical, 1.0 = pure semantic)
  hybrid_weight: 0.7

  # Maximum number of files to include in context
  max_files: 20

  # Boost factor for recently modified files
  recency_boost: 1.2

  # File size limits
  max_file_size: 1048576 # 1MB
  max_line_length: 1000

# Search Configuration
search:
  # Enable semantic search (requires embeddings)
  enable_semantic: true

  # Embedding model for semantic search
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"

  # Cache embeddings to disk
  cache_embeddings: true

  # Lexical search settings
  lexical:
    # Use ripgrep if available
    use_ripgrep: true

    # Case sensitivity
    case_sensitive: false

    # Include binary files
    include_binary: false

# Safety and Backup Settings
safety:
  # Always create backups before applying changes
  create_backups: true

  # Maximum number of backups to keep
  max_backups: 10

  # Require confirmation for destructive operations
  require_confirmation: true

  # Maximum file size for edits (bytes)
  max_edit_size: 1048576

  # Patterns to exclude from editing
  edit_exclude_patterns:
    - "*.lock"
    - "*.log"
    - ".git/**"
    - "node_modules/**"

# Code Formatting
formatting:
  # Enable automatic formatting after edits
  auto_format: true

  # Formatter configurations
  formatters:
    python:
      - command: ["black", "--quiet", "-"]
        stdin: true
      - command: ["isort", "--quiet", "-"]
        stdin: true
    javascript:
      - command: ["prettier", "--stdin-filepath", "{file}"]
        stdin: true
    typescript:
      - command: ["prettier", "--stdin-filepath", "{file}"]
        stdin: true
    go:
      - command: ["gofmt"]
        stdin: true

# Framework Detection and Integration
frameworks:
  # Enable automatic framework detection
  auto_detect: true

  # Framework-specific settings
  python:
    # Test command patterns
    test_commands:
      - "python -m pytest"
      - "python -m unittest"
      - "python test.py"

    # Virtual environment detection
    venv_paths:
      - ".venv"
      - "venv"
      - ".env"

  javascript:
    test_commands:
      - "npm test"
      - "yarn test"
      - "jest"

    package_files:
      - "package.json"
      - "yarn.lock"

  go:
    test_commands:
      - "go test ./..."
      - "go test"

# Language Server Protocol (LSP) Settings
lsp:
  # Enable LSP integration
  enabled: true

  # Timeout for LSP operations (seconds)
  timeout: 10

  # Server configurations
  servers:
    python:
      command: ["pylsp"]
      filetypes: ["python"]
    javascript:
      command: ["typescript-language-server", "--stdio"]
      filetypes: ["javascript", "typescript"]
    go:
      command: ["gopls"]
      filetypes: ["go"]

# Git Integration Settings
git:
  # Enable git integration
  enabled: true

  # Automatically stage files after successful edits
  auto_stage: false

  # Include git context in prompts
  include_git_context: true

  # Commit message templates
  commit_templates:
    feat: "feat: {description}"
    fix: "fix: {description}"
    docs: "docs: {description}"
    refactor: "refactor: {description}"

# Audit and Logging
audit:
  # Enable audit logging
  enabled: true

  # Log file location (relative to .term-coder/)
  log_file: "audit/audit.jsonl"

  # Log rotation settings
  max_log_size: 10485760 # 10MB
  max_log_files: 5

  # What to log
  log_events:
    - "command_execution"
    - "file_access"
    - "llm_requests"
    - "errors"
    - "privacy_changes"

# Performance Settings
performance:
  # Enable response caching
  enable_caching: true

  # Cache duration (seconds)
  cache_duration: 3600

  # Maximum cache size (MB)
  max_cache_size: 100

  # Background indexing
  background_indexing: true

  # Parallel processing
  max_workers: 4

# UI and Output Settings
ui:
  # Color theme: auto, light, dark
  theme: "auto"

  # Enable progress bars
  show_progress: true

  # Enable streaming output
  streaming: true

  # Pager for long output
  pager: "auto" # auto, less, more, none

  # Terminal width override
  width: null # null for auto-detect

# Plugin Settings
plugins:
  # Enable plugin system
  enabled: true

  # Plugin directories
  directories:
    - ".term-coder/plugins"
    - "~/.term-coder/plugins"

  # Auto-load plugins
  auto_load: true

  # Plugin-specific settings
  settings: {}
```

## Model Configuration

### Available Models

Term-coder supports multiple model providers:

#### OpenAI Models

```yaml
llm:
  default_model: "openai:gpt-4o-mini" # Fast, cost-effective
  # default_model: "openai:gpt-4o"        # Most capable
  # default_model: "openai:gpt-3.5-turbo" # Legacy, cheaper
```

#### Anthropic Models

```yaml
llm:
  default_model: "anthropic:claude-3-haiku" # Fast, cost-effective
  # default_model: "anthropic:claude-3-sonnet" # Balanced
  # default_model: "anthropic:claude-3-opus"   # Most capable
```

#### Local Models (via Ollama)

```yaml
llm:
  default_model: "ollama:codellama"
  # default_model: "ollama:llama2"
  # default_model: "ollama:mistral"
```

### Model-Specific Settings

Configure individual models:

```yaml
llm:
  models:
    "openai:gpt-4o":
      max_tokens: 8192
      temperature: 0.1
      top_p: 1.0
      frequency_penalty: 0.0
      presence_penalty: 0.0

    "anthropic:claude-3-sonnet":
      max_tokens: 4096
      temperature: 0.1

    "ollama:codellama":
      max_tokens: 2048
      temperature: 0.2
      num_ctx: 4096
```

## Privacy Configuration

### Offline Mode

Enable offline mode for complete privacy:

```yaml
privacy:
  offline_mode: true
```

This disables:

- All external API calls
- Semantic search (unless using local embeddings)
- Online model usage

### Secret Redaction

Configure automatic secret detection:

```yaml
privacy:
  redact_secrets: true

  # Custom secret patterns
  secret_patterns:
    - name: "custom_api_key"
      pattern: "CUSTOM_API_[A-Z0-9]{32}"
      replacement: "CUSTOM_API_[REDACTED]"
```

### Audit Levels

Control logging detail:

```yaml
privacy:
  audit_level: "standard" # minimal, standard, detailed
```

- **minimal**: Only errors and critical events
- **standard**: Normal operations and changes
- **detailed**: All operations including prompts

## Search Configuration

### Hybrid Search Tuning

Balance between lexical and semantic search:

```yaml
retrieval:
  hybrid_weight: 0.7 # 0.0 = pure lexical, 1.0 = pure semantic
```

Recommended values:

- `0.3`: Favor lexical search (exact matches)
- `0.7`: Balanced (recommended)
- `0.9`: Favor semantic search (meaning-based)

### Embedding Models

Choose embedding model for semantic search:

```yaml
search:
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2" # Fast, good quality
  # embedding_model: "sentence-transformers/all-mpnet-base-v2"  # Better quality, slower
```

## Safety Configuration

### Backup Settings

Configure automatic backups:

```yaml
safety:
  create_backups: true
  max_backups: 10
  backup_location: ".term-coder/backups"
```

### File Size Limits

Prevent processing of large files:

```yaml
safety:
  max_file_size: 1048576 # 1MB
  max_edit_size: 524288 # 512KB
```

### Exclusion Patterns

Exclude files from processing:

```yaml
safety:
  edit_exclude_patterns:
    - "*.lock"
    - "*.log"
    - ".git/**"
    - "node_modules/**"
    - "**/__pycache__/**"
```

## Framework Integration

### Python Projects

```yaml
frameworks:
  python:
    test_commands:
      - "python -m pytest tests/"
      - "python -m unittest discover"

    formatters:
      - "black"
      - "isort"

    linters:
      - "flake8"
      - "mypy"
```

### JavaScript/Node.js Projects

```yaml
frameworks:
  javascript:
    test_commands:
      - "npm test"
      - "yarn test"
      - "jest"

    formatters:
      - "prettier"

    linters:
      - "eslint"
```

### Go Projects

```yaml
frameworks:
  go:
    test_commands:
      - "go test ./..."

    formatters:
      - "gofmt"
      - "goimports"
```

## Environment Variables

Override configuration with environment variables:

```bash
# API Keys
export OPENAI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"

# Configuration overrides
export TERM_CODER_OFFLINE="true"
export TERM_CODER_MODEL="anthropic:claude-3-sonnet"
export TERM_CODER_CONFIG="/path/to/custom/config.yaml"

# Debug settings
export TERM_CODER_DEBUG="true"
export TERM_CODER_LOG_LEVEL="DEBUG"
```

## Configuration Validation

Validate your configuration:

```bash
tc config validate
```

This checks:

- YAML syntax
- Required fields
- Model availability
- API key validity
- File permissions

## Configuration Templates

### Minimal Configuration

For basic usage:

```yaml
llm:
  default_model: "openai:gpt-4o-mini"
  openai_api_key: "${OPENAI_API_KEY}"

privacy:
  redact_secrets: true

safety:
  create_backups: true
```

### Privacy-Focused Configuration

For maximum privacy:

```yaml
llm:
  default_model: "ollama:codellama"

privacy:
  offline_mode: true
  redact_secrets: true
  audit_level: "minimal"
  consent:
    data_collection: false
    analytics: false
    model_training: false
    error_reporting: false

search:
  enable_semantic: false
```

### Performance-Optimized Configuration

For large repositories:

```yaml
llm:
  default_model: "openai:gpt-4o-mini"

retrieval:
  max_tokens: 16000
  max_files: 50

search:
  cache_embeddings: true

performance:
  enable_caching: true
  background_indexing: true
  max_workers: 8

safety:
  max_file_size: 2097152 # 2MB
```

## Troubleshooting Configuration

### Common Issues

1. **Invalid YAML syntax**

   ```bash
   tc config validate
   ```

2. **Missing API keys**

   ```bash
   export OPENAI_API_KEY="your-key"
   tc config test-connection
   ```

3. **Permission errors**

   ```bash
   chmod 600 .term-coder/config.yaml
   ```

4. **Model not available**
   ```bash
   tc config list-models
   ```

### Configuration Debugging

Enable debug mode:

```yaml
debug:
  enabled: true
  log_level: "DEBUG"
  log_file: ".term-coder/debug.log"
```

Or use environment variable:

```bash
export TERM_CODER_DEBUG=true
tc chat "test message"
```

## Best Practices

1. **Use environment variables for secrets**

   ```yaml
   llm:
     openai_api_key: "${OPENAI_API_KEY}"
   ```

2. **Start with defaults, customize gradually**

   ```bash
   tc init  # Creates default config
   # Modify specific settings as needed
   ```

3. **Version control your configuration**

   ```bash
   git add .term-coder/config.yaml
   ```

4. **Use different configs for different projects**

   ```bash
   cp .term-coder/config.yaml .term-coder/config.backup.yaml
   ```

5. **Regular validation**

   ```bash
   tc config validate
   ```

6. **Monitor usage and costs**
   ```bash
   tc audit --days 30
   ```
