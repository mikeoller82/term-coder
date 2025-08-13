# Frequently Asked Questions (FAQ)

Common questions and answers about term-coder.

## General Questions

### What is term-coder?

Term-coder is a terminal-based coding assistant that provides repository-aware context and safe, non-destructive file editing capabilities. It enables developers to interact with their codebase through natural language, perform code analysis, execute commands safely, and manage git workflows with AI assistance.

### How is term-coder different from other AI coding tools?

Term-coder is unique in several ways:

- **Repository-aware**: Understands your entire codebase context
- **Safety-first**: All changes go through review before application
- **Terminal-native**: Designed for command-line workflows
- **Privacy-focused**: Supports offline mode and comprehensive audit logging
- **Multi-model**: Works with OpenAI, Anthropic, and local models
- **Framework-agnostic**: Works with any programming language or framework

### Is term-coder free to use?

Term-coder itself is open-source and free. However, you may incur costs from:
- AI model providers (OpenAI, Anthropic) for API usage
- Local compute resources if using local models

You can use term-coder completely offline with local models to avoid any external costs.

## Installation and Setup

### What are the system requirements?

- **Python**: 3.10 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: 2GB RAM minimum, 4GB recommended
- **Storage**: 100MB for installation, additional space for indexes and cache
- **Optional**: Git for version control features

### How do I install term-coder?

```bash
# Install from PyPI (recommended)
pip install term-coder

# Or install from source
git clone https://github.com/your-org/term-coder.git
cd term-coder
pip install -e .
```

### Do I need an API key to use term-coder?

No, API keys are optional. You can:
- Use cloud models (OpenAI, Anthropic) with API keys
- Use local models (via Ollama) without API keys
- Use offline mode for complete privacy

### How do I set up API keys?

```bash
# Environment variables (recommended)
export OPENAI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"

# Or in configuration file
# .term-coder/config.yaml
llm:
  openai_api_key: "${OPENAI_API_KEY}"
  anthropic_api_key: "${ANTHROPIC_API_KEY}"
```

## Usage Questions

### How do I get started with term-coder?

1. Install term-coder: `pip install term-coder`
2. Navigate to your project: `cd your-project`
3. Initialize: `tc init`
4. Build index: `tc index`
5. Start chatting: `tc chat "What does this project do?"`

See our [Getting Started Guide](getting-started.md) for detailed instructions.

### What commands are available?

Key commands include:
- `tc chat` - Interactive conversation
- `tc search` - Find code and files
- `tc edit` - Generate code changes
- `tc diff` - Review proposed changes
- `tc apply` - Apply changes
- `tc review` - AI code review
- `tc test` - Run tests with analysis

See the [CLI Reference](cli-reference.md) for complete documentation.

### How does the edit workflow work?

Term-coder uses a safe, three-step process:

1. **Generate**: `tc edit "instruction" --files file.py` creates a proposal
2. **Review**: `tc diff` shows exactly what will change
3. **Apply**: `tc apply` makes the changes with automatic backup

This ensures you always see and approve changes before they're made.

### Can I undo changes?

Yes! Term-coder creates automatic backups:

```bash
# List backups
tc backups list

# Restore from backup
tc restore --backup-id backup_20240101_120000_abc123

# Or use git if available
git checkout -- file.py
```

## Privacy and Security

### Is my code sent to external services?

Only if you choose to use cloud models (OpenAI, Anthropic). You can:
- Use offline mode: `tc privacy offline_mode true`
- Use local models: Configure Ollama or similar
- Review audit logs: `tc audit`

### How does secret detection work?

Term-coder automatically detects and redacts common secrets:
- API keys
- Passwords
- Database URLs
- JWT tokens
- Custom patterns you define

Enable with: `tc privacy redact_secrets true`

### What data is logged?

Term-coder logs:
- Commands executed
- Files accessed
- Errors encountered
- Privacy setting changes

You control logging detail with `audit_level` setting. Logs are stored locally in `.term-coder/audit/`.

### Can I use term-coder in enterprise environments?

Yes! Term-coder supports:
- Offline operation
- Comprehensive audit logging
- Secret detection and redaction
- Custom privacy policies
- Air-gapped deployments

## Performance and Optimization

### Why is term-coder slow?

Common causes and solutions:

**Large repository**:
```bash
# Exclude unnecessary files
tc index --exclude "node_modules/**" --exclude "**/*.log"
```

**Slow model**:
```bash
# Use faster model
tc config set llm.default_model "openai:gpt-4o-mini"
```

**Network issues**:
```bash
# Use offline mode
tc privacy offline_mode true
```

### How can I improve search quality?

1. **Keep index updated**: `tc index` after major changes
2. **Use hybrid search**: `tc search "query" --hybrid`
3. **Be specific**: Include context in search terms
4. **Use file filters**: `--type py --include "src/**"`

### How much does it cost to use cloud models?

Costs vary by provider and usage:

**OpenAI GPT-4o-mini**: ~$0.15 per 1M input tokens
**OpenAI GPT-4o**: ~$2.50 per 1M input tokens
**Anthropic Claude-3-Haiku**: ~$0.25 per 1M input tokens

Typical session costs:
- Simple chat: $0.01-0.05
- Code edit: $0.05-0.20
- Large refactoring: $0.20-1.00

Use `tc audit` to monitor usage.

## Troubleshooting

### "No module named 'term_coder'" error

```bash
# Check installation
pip list | grep term-coder

# Reinstall if needed
pip install --upgrade term-coder

# Check Python path
python -c "import sys; print(sys.path)"
```

### "Config not found" error

```bash
# Initialize configuration
tc init

# Check if config exists
ls -la .term-coder/config.yaml

# Check permissions
chmod 644 .term-coder/config.yaml
```

### Search returns no results

```bash
# Rebuild index
tc index

# Check index file
wc -l .term-coder/index.tsv

# Try different search mode
tc search "query" --semantic
```

### API errors or timeouts

```bash
# Check API key
echo $OPENAI_API_KEY

# Test connection
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# Use offline mode
tc privacy offline_mode true
```

### Permission denied errors

```bash
# Check file permissions
ls -la .term-coder/

# Fix permissions
chmod 755 .term-coder/
chmod 644 .term-coder/config.yaml

# Check disk space
df -h .
```

## Advanced Usage

### Can I use multiple AI models?

Yes! Configure different models for different tasks:

```yaml
llm:
  default_model: "openai:gpt-4o-mini"
  heavy_model: "openai:gpt-4o"
  
  task_models:
    chat: "openai:gpt-4o-mini"
    edit: "openai:gpt-4o"
    review: "anthropic:claude-3-sonnet"
```

### How do I create custom plugins?

See our [Plugin Development Guide](plugin-development.md). Basic steps:

1. Create plugin directory: `.term-coder/plugins/my_plugin/`
2. Implement plugin class with commands and hooks
3. Register plugin in `__init__.py`
4. Enable plugin: `tc plugins enable my_plugin`

### Can I integrate with CI/CD?

Yes! Term-coder works well in CI/CD pipelines:

```bash
# In your CI script
tc init --ci-mode
tc review --range origin/main..HEAD --format json
tc scan-secrets --fail-on-secrets
tc test --coverage --format junit
```

### How do I handle large repositories?

Optimization strategies:

1. **Selective indexing**: Use `--include` and `--exclude` patterns
2. **Resource limits**: Configure memory and CPU limits
3. **Caching**: Enable response and embedding caching
4. **Parallel processing**: Increase worker counts
5. **File size limits**: Exclude very large files

## Integration Questions

### Does term-coder work with my IDE?

Term-coder is terminal-based but can integrate with IDEs:

- **VS Code**: Create tasks and keybindings
- **Vim/Neovim**: Use terminal integration
- **Emacs**: Shell command integration
- **JetBrains**: External tools configuration

### Can I use term-coder with Docker?

Yes! Example Dockerfile:

```dockerfile
FROM python:3.11-slim

RUN pip install term-coder
WORKDIR /workspace

# Copy your project
COPY . .

# Initialize term-coder
RUN tc init --ci-mode
RUN tc index

CMD ["bash"]
```

### Does it work with monorepos?

Yes, but consider:
- Use selective indexing for performance
- Configure appropriate context limits
- Consider separate configurations per service
- Use directory-specific sessions

## Model and Provider Questions

### Which AI model should I use?

**For most users**: `openai:gpt-4o-mini` (fast, cost-effective)
**For complex tasks**: `openai:gpt-4o` (most capable)
**For privacy**: Local models via Ollama
**For alternatives**: `anthropic:claude-3-sonnet`

### How do I use local models?

1. Install Ollama: https://ollama.ai/
2. Pull a model: `ollama pull codellama`
3. Configure term-coder:
   ```yaml
   llm:
     default_model: "ollama:codellama"
   ```

### Can I switch models mid-conversation?

Yes! Use the `--model` flag:

```bash
tc chat "simple question" --model "openai:gpt-4o-mini"
tc chat "complex analysis" --model "openai:gpt-4o"
```

## Contributing and Community

### How can I contribute to term-coder?

We welcome contributions! Ways to help:

- **Report bugs**: File issues on GitHub
- **Suggest features**: Open feature requests
- **Write documentation**: Improve guides and examples
- **Create plugins**: Extend functionality
- **Submit code**: Fix bugs and add features

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

### Where can I get help?

- **Documentation**: Comprehensive guides and references
- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Community Q&A and tips
- **Discord/Slack**: Real-time community support

### How do I report bugs?

1. Check existing issues first
2. Run diagnostics: `tc diagnostics`
3. Export error report: `tc export-errors`
4. File issue with:
   - System information
   - Steps to reproduce
   - Expected vs actual behavior
   - Error logs and diagnostics

### Can I request new features?

Absolutely! We prioritize features based on:
- Community demand
- Implementation complexity
- Alignment with project goals
- Maintainability

File feature requests on GitHub with detailed use cases.

## Licensing and Legal

### What license is term-coder under?

Term-coder is released under the MIT License, which allows:
- Commercial use
- Modification
- Distribution
- Private use

### Can I use term-coder commercially?

Yes! The MIT license permits commercial use. However:
- AI model providers may have their own terms
- Ensure compliance with your organization's policies
- Consider privacy implications for proprietary code

### What about data privacy?

Term-coder is designed with privacy in mind:
- Local operation by default
- Comprehensive audit logging
- Secret detection and redaction
- User control over data sharing
- Offline mode available

Review our [Privacy Policy](privacy-policy.md) for details.

---

## Still Have Questions?

If you can't find the answer here:

1. **Search the documentation** - Use the search function
2. **Check GitHub issues** - Someone may have asked already
3. **Ask the community** - Join our discussions
4. **File an issue** - We're happy to help!

We're constantly updating this FAQ based on user questions, so check back regularly for new information.