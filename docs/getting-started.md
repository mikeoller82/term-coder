# Getting Started with Term-Coder

This guide will help you get up and running with term-coder in minutes.

## Prerequisites

Before installing term-coder, ensure you have:

- **Python 3.10 or higher**
- **Git** (for repository operations)
- **An OpenAI API key** (optional, for cloud models)

## Installation

### Option 1: Install from PyPI (Recommended)

```bash
pip install term-coder
```

### Option 2: Install from Source

```bash
git clone https://github.com/your-org/term-coder.git
cd term-coder
pip install -e .
```

## Initial Setup

### 1. Initialize Configuration

Navigate to your project directory and initialize term-coder:

```bash
cd your-project
tc init
```

This creates a `.term-coder/config.yaml` file with default settings.

### 2. Configure API Keys (Optional)

If you want to use cloud models, set your API keys:

```bash
# For OpenAI models
export OPENAI_API_KEY="your-api-key-here"

# For Anthropic models
export ANTHROPIC_API_KEY="your-api-key-here"
```

Or add them to your configuration file:

```yaml
# .term-coder/config.yaml
llm:
  openai_api_key: "${OPENAI_API_KEY}"
  anthropic_api_key: "${ANTHROPIC_API_KEY}"
```

### 3. Build Search Index

Build an index of your repository for fast search:

```bash
tc index
```

This creates a `.term-coder/index.tsv` file with metadata about your files.

## Your First Commands

### Chat with Your Codebase

Start a conversation about your code:

```bash
tc chat "What does this project do?"
```

```bash
tc chat "Explain the main function" --files src/main.py
```

### Search Your Repository

Find files and code snippets:

```bash
# Lexical search (default)
tc search "error handling"

# Semantic search
tc search "authentication logic" --semantic

# Hybrid search (combines both)
tc search "database connection" --hybrid
```

### Make Safe Edits

Generate and review code changes:

```bash
# Generate an edit proposal
tc edit "add input validation to the login function" --files src/auth.py

# Review the proposed changes
tc diff

# Apply the changes if they look good
tc apply
```

### Run Commands Safely

Execute commands in a sandboxed environment:

```bash
tc run "python -m pytest tests/"
tc run "npm test" --timeout 60
```

## Understanding the Workflow

Term-coder follows a safe, review-based workflow:

1. **Context Selection**: Automatically selects relevant files based on your query
2. **AI Processing**: Sends context to your chosen AI model
3. **Proposal Generation**: Creates edit proposals or responses
4. **Review Phase**: Shows you exactly what will change
5. **Safe Application**: Applies changes with automatic backups

## Configuration Basics

Your `.term-coder/config.yaml` file controls term-coder's behavior:

```yaml
# Model selection
llm:
  default_model: "openai:gpt-4o-mini"  # Fast, cost-effective
  # default_model: "openai:gpt-4o"     # More capable
  # default_model: "anthropic:claude-3-sonnet"  # Alternative

# Privacy settings
privacy:
  offline_mode: false      # Set to true for local-only operation
  redact_secrets: true     # Automatically redact API keys, passwords
  audit_level: "standard"  # Track usage for debugging

# Search configuration
retrieval:
  max_tokens: 8000        # Context window size
  hybrid_weight: 0.7      # Balance between lexical/semantic search

# Safety settings
safety:
  create_backups: true    # Always backup before changes
  max_file_size: 1048576  # 1MB file size limit
```

## Working with Sessions

Term-coder maintains conversation history in sessions:

```bash
# Use default session
tc chat "Hello"

# Use named session
tc chat "What's the architecture?" --session architecture

# Continue previous conversation
tc chat "Can you elaborate on that?" --session architecture
```

Sessions are stored in `.term-coder/sessions/` and persist between runs.

## Privacy and Security

Term-coder is designed with privacy in mind:

- **Offline Mode**: Use `privacy.offline_mode: true` for local-only operation
- **Secret Detection**: Automatically detects and redacts sensitive information
- **Audit Logging**: Tracks all operations for transparency
- **No Training**: Your code is never used to train models (when using OpenAI/Anthropic)

## Next Steps

Now that you have term-coder set up:

1. **Explore Commands**: Try `tc --help` to see all available commands
2. **Customize Configuration**: Adjust settings in `.term-coder/config.yaml`
3. **Read Advanced Usage**: Check out [advanced-usage.md](advanced-usage.md) for power user features
4. **Join the Community**: Get help and share tips with other users

## Common Issues

### "No module named 'term_coder'"

Make sure you installed term-coder correctly:

```bash
pip install term-coder
# or
pip install -e . # if installing from source
```

### "API key not found"

Set your API key as an environment variable:

```bash
export OPENAI_API_KEY="your-key-here"
```

### "Permission denied" errors

Ensure you have write permissions in your project directory and that files aren't locked by other processes.

### Slow search performance

Install ripgrep for faster search:

```bash
# macOS
brew install ripgrep

# Ubuntu/Debian
sudo apt install ripgrep

# Windows
choco install ripgrep
```

## Getting Help

- **CLI Help**: Use `tc --help` or `tc <command> --help`
- **Troubleshooting**: See [troubleshooting.md](troubleshooting.md)
- **Configuration**: See [configuration.md](configuration.md)
- **Issues**: Report bugs on GitHub

Happy coding with term-coder! 🚀