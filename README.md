# Term-Coder 🤖

**The AI coding assistant that speaks your language.** Just tell it what you want to do!

Term-coder is a revolutionary terminal-based coding assistant that understands natural language and provides intelligent, repo-aware assistance. No complex commands to memorize - just talk to it like you would a human colleague.

## 🚀 Quick Start

```bash
# Install term-coder
pip install term-coder

# Navigate to your project and just start talking!
cd your-project
tc "debug for errors"
tc "fix the authentication bug"
tc "explain how the login system works"
tc "add error handling to main.py"
```

**That's it!** Term-coder understands what you want and figures out how to do it.

## 💬 Natural Language Interface

Just run `tc` and start talking naturally:

```bash
# Start interactive mode
tc

# Or give direct commands
tc "search for TODO comments"
tc "review my recent changes"  
tc "generate tests for the user service"
tc "optimize the database queries"
```

**No need to learn complex syntax** - term-coder understands:
- "Debug for errors" → Finds and analyzes error patterns
- "Fix the login bug" → Identifies and fixes authentication issues  
- "Explain main.py" → Provides detailed code explanations
- "Add logging" → Implements appropriate logging throughout your code

## ✨ Key Features

- **🧠 Repo-Aware Context**: Intelligent context selection using hybrid search (lexical + semantic)
- **🛡️ Safe Editing**: All modifications go through diff/patch review loops before application
- **🔍 Powerful Search**: Fast lexical search with ripgrep + semantic search with embeddings
- **⚡ Streaming Responses**: Real-time AI responses with progress indicators
- **🔒 Privacy-First**: Offline mode, secret detection, and comprehensive audit logging
- **🎯 Multi-Model Support**: OpenAI, Anthropic, and local models via Ollama
- **🔧 Framework-Aware**: Automatic detection and integration with popular frameworks
- **📊 Comprehensive Diagnostics**: Built-in error handling and system health monitoring

## 📖 Documentation

- [Getting Started Guide](docs/getting-started.md) - Complete setup and first steps
- [CLI Reference](docs/cli-reference.md) - Comprehensive command documentation
- [Configuration Guide](docs/configuration.md) - Settings and customization
- [Plugin Development](docs/plugin-development.md) - Creating custom plugins
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions
- [Advanced Usage](docs/advanced-usage.md) - Power user features and workflows

## 🏗️ Architecture

Term-coder follows a modular architecture with clear separation of concerns:

- **CLI Layer**: Typer-based command interface with Rich output
- **Context Engine**: Intelligent file selection and token budget management
- **Search System**: Three-tier search (lexical, semantic, hybrid)
- **LLM Orchestrator**: Multi-provider adapter with streaming support
- **Edit System**: Safe patch generation and application with backups
- **Security Layer**: Privacy controls, secret detection, and audit logging

## 🛠️ Installation

### Requirements

- Python 3.10+
- Git (for repository operations)
- Optional: ripgrep (for faster search)

### Install from PyPI

```bash
pip install term-coder
```

### Install from Source

```bash
git clone https://github.com/your-org/term-coder.git
cd term-coder
pip install -e .
```

### Development Setup

```bash
git clone https://github.com/your-org/term-coder.git
cd term-coder
pip install -e ".[dev]"
python -m pytest tests/
```

## 🎯 Core Commands

| Command | Description | Example |
|---------|-------------|---------|
| `tc init` | Initialize configuration | `tc init` |
| `tc chat` | Interactive chat with repo context | `tc chat "explain this function"` |
| `tc search` | Search across repository | `tc search "error handling" --semantic` |
| `tc edit` | Generate edit proposals | `tc edit "add logging" --files src/main.py` |
| `tc diff` | Show pending changes | `tc diff` |
| `tc apply` | Apply pending changes | `tc apply` |
| `tc run` | Execute commands safely | `tc run pytest tests/` |
| `tc test` | Run tests with analysis | `tc test` |
| `tc review` | AI code review | `tc review --range HEAD~3..HEAD` |
| `tc commit` | Generate commit messages | `tc commit` |

## 🔧 Configuration

Term-coder uses a YAML configuration file at `.term-coder/config.yaml`:

```yaml
# LLM Configuration
llm:
  default_model: "openai:gpt-4o-mini"
  openai_api_key: "${OPENAI_API_KEY}"
  
# Privacy Settings
privacy:
  offline_mode: false
  redact_secrets: true
  audit_level: "standard"

# Search Configuration
retrieval:
  max_tokens: 8000
  hybrid_weight: 0.7
  
# Safety Settings
safety:
  create_backups: true
  max_file_size: 1048576
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/)
- Search powered by [ripgrep](https://github.com/BurntSushi/ripgrep)
- Semantic search using [sentence-transformers](https://www.sbert.net/)
- Git integration via [GitPython](https://gitpython.readthedocs.io/)