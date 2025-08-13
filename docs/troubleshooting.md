# Troubleshooting Guide

Common issues and solutions for term-coder.

## Installation Issues

### "No module named 'term_coder'"

**Problem**: Term-coder is not installed or not in Python path.

**Solutions**:
```bash
# Install from PyPI
pip install term-coder

# Or install from source
git clone https://github.com/your-org/term-coder.git
cd term-coder
pip install -e .

# Check installation
tc --version
```

**If still not working**:
```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Check if term-coder is installed
pip list | grep term-coder

# Try with full path
python -m term_coder.cli --help
```

### Permission Denied Errors

**Problem**: Cannot write to configuration directory or files.

**Solutions**:
```bash
# Check permissions
ls -la .term-coder/

# Fix permissions
chmod 755 .term-coder/
chmod 644 .term-coder/config.yaml

# If in system directory, use user directory
mkdir -p ~/.term-coder
export TERM_CODER_CONFIG=~/.term-coder/config.yaml
```

### Python Version Issues

**Problem**: Term-coder requires Python 3.10+.

**Solutions**:
```bash
# Check Python version
python --version

# Use specific Python version
python3.10 -m pip install term-coder

# Or use pyenv
pyenv install 3.10.0
pyenv local 3.10.0
```

## Configuration Issues

### "Config not found" Error

**Problem**: Configuration file doesn't exist or can't be found.

**Solutions**:
```bash
# Initialize configuration
tc init

# Check if config exists
ls -la .term-coder/config.yaml

# Use custom config location
export TERM_CODER_CONFIG=/path/to/config.yaml
tc init
```

### Invalid YAML Syntax

**Problem**: Configuration file has syntax errors.

**Solutions**:
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('.term-coder/config.yaml'))"

# Or use online YAML validator
# Copy content to https://yamlchecker.com/

# Common issues:
# - Incorrect indentation (use spaces, not tabs)
# - Missing quotes around special characters
# - Unescaped colons in strings
```

**Example fixes**:
```yaml
# Wrong
llm:
  api_key: sk-abc123:def456

# Right
llm:
  api_key: "sk-abc123:def456"

# Wrong (tabs)
llm:
	default_model: "openai:gpt-4o"

# Right (spaces)
llm:
  default_model: "openai:gpt-4o"
```

### API Key Issues

**Problem**: API keys not working or not found.

**Solutions**:
```bash
# Set environment variable
export OPENAI_API_KEY="your-key-here"

# Test API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models

# Check config file
cat .term-coder/config.yaml | grep api_key

# Use environment variable in config
llm:
  openai_api_key: "${OPENAI_API_KEY}"
```

## Search and Indexing Issues

### "No search results" or Poor Search Quality

**Problem**: Search returns no results or irrelevant results.

**Solutions**:
```bash
# Rebuild index
tc index

# Check index file
ls -la .term-coder/index.tsv
wc -l .term-coder/index.tsv

# Try different search modes
tc search "your query" --semantic
tc search "your query" --hybrid

# Check file patterns
tc search "your query" --include "**/*.py"
```

### Slow Search Performance

**Problem**: Search takes too long.

**Solutions**:
```bash
# Install ripgrep for faster lexical search
# macOS
brew install ripgrep

# Ubuntu/Debian
sudo apt install ripgrep

# Windows
choco install ripgrep

# Check if ripgrep is available
rg --version

# Use lexical search for speed
tc search "query" --top 10
```

### Semantic Search Not Working

**Problem**: Semantic search fails or gives errors.

**Solutions**:
```bash
# Check if embeddings are enabled
tc diagnostics | grep embeddings

# Install sentence-transformers
pip install sentence-transformers

# Try offline mode if network issues
tc privacy offline_mode true

# Check embedding model
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

## LLM and API Issues

### "API key invalid" or Authentication Errors

**Problem**: Cannot authenticate with LLM providers.

**Solutions**:
```bash
# Check API key format
echo $OPENAI_API_KEY | wc -c  # Should be ~51 characters

# Test API key directly
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models

# Check account status and billing
# Visit https://platform.openai.com/account/billing

# Try different model
tc chat "test" --model "openai:gpt-3.5-turbo"
```

### Rate Limiting or Quota Exceeded

**Problem**: API requests are being rate limited.

**Solutions**:
```bash
# Check usage
# Visit https://platform.openai.com/account/usage

# Use cheaper model
tc config set llm.default_model "openai:gpt-4o-mini"

# Enable offline mode temporarily
tc privacy offline_mode true

# Wait and retry
sleep 60
tc chat "test message"
```

### Connection Timeouts

**Problem**: API requests timeout.

**Solutions**:
```bash
# Check internet connection
ping api.openai.com

# Check proxy settings
echo $HTTP_PROXY
echo $HTTPS_PROXY

# Increase timeout in config
llm:
  timeout: 60  # seconds

# Try different model provider
tc chat "test" --model "anthropic:claude-3-haiku"
```

### Model Not Available

**Problem**: Requested model is not available.

**Solutions**:
```bash
# List available models
tc config list-models

# Check model name spelling
tc chat "test" --model "openai:gpt-4o-mini"  # Correct
# Not: "openai:gpt4-mini"  # Wrong

# Use fallback model
tc config set llm.default_model "openai:gpt-3.5-turbo"
```

## File and Edit Issues

### "Permission denied" When Editing Files

**Problem**: Cannot modify files.

**Solutions**:
```bash
# Check file permissions
ls -la src/main.py

# Make file writable
chmod 644 src/main.py

# Check if file is locked by another process
lsof src/main.py

# Try editing different file
tc edit "add comment" --files README.md
```

### Edit Proposals Not Generated

**Problem**: `tc edit` doesn't generate any changes.

**Solutions**:
```bash
# Check if files exist
ls -la src/main.py

# Try more specific instruction
tc edit "add a print statement at the beginning of the main function" --files src/main.py

# Check file size limits
wc -c src/main.py  # Should be < 1MB by default

# Try without LLM
tc edit "format code" --files src/main.py --no-llm
```

### Backup and Apply Issues

**Problem**: Cannot apply changes or restore backups.

**Solutions**:
```bash
# Check backup directory
ls -la .term-coder/backups/

# Check pending changes
tc diff

# Apply with verbose output
tc apply --verbose

# Restore from backup
tc restore --backup-id <backup-id>

# Check disk space
df -h .
```

## Git Integration Issues

### "Not a git repository"

**Problem**: Git commands fail because not in a git repo.

**Solutions**:
```bash
# Initialize git repository
git init

# Check if in git repo
git status

# Use term-coder without git features
tc chat "help" --no-git-context
```

### Git Commands Fail

**Problem**: Git integration doesn't work.

**Solutions**:
```bash
# Check git installation
git --version

# Check git configuration
git config --list

# Test git operations
git status
git log --oneline -5

# Disable git integration temporarily
git:
  enabled: false
```

## Performance Issues

### Slow Response Times

**Problem**: Commands take too long to execute.

**Solutions**:
```bash
# Check system resources
top
df -h

# Reduce context size
retrieval:
  max_tokens: 4000
  max_files: 10

# Use faster model
tc config set llm.default_model "openai:gpt-4o-mini"

# Enable caching
performance:
  enable_caching: true
```

### High Memory Usage

**Problem**: Term-coder uses too much memory.

**Solutions**:
```bash
# Check memory usage
ps aux | grep term-coder

# Reduce embedding cache
search:
  cache_embeddings: false

# Limit file size
safety:
  max_file_size: 524288  # 512KB

# Restart term-coder session
```

### Large Repository Issues

**Problem**: Performance issues with large codebases.

**Solutions**:
```bash
# Exclude large directories
tc index --exclude "node_modules/**" --exclude "**/*.log"

# Use .term-coder/ignore file
echo "node_modules/" >> .term-coder/ignore
echo "*.log" >> .term-coder/ignore

# Increase resource limits
performance:
  max_workers: 8
  max_cache_size: 500  # MB
```

## Network and Connectivity Issues

### Offline Mode Problems

**Problem**: Features don't work in offline mode.

**Solutions**:
```bash
# Check offline mode status
tc privacy

# Disable features that require network
privacy:
  offline_mode: true

search:
  enable_semantic: false  # If using cloud embeddings

# Use local models
llm:
  default_model: "ollama:codellama"
```

### Proxy Configuration

**Problem**: Cannot connect through corporate proxy.

**Solutions**:
```bash
# Set proxy environment variables
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080

# Or in config
network:
  proxy:
    http: "http://proxy.company.com:8080"
    https: "http://proxy.company.com:8080"

# Test connectivity
curl -x $HTTP_PROXY https://api.openai.com/v1/models
```

## Plugin Issues

### Plugin Not Loading

**Problem**: Custom plugins don't load.

**Solutions**:
```bash
# Check plugin directory
ls -la .term-coder/plugins/

# Check plugin structure
ls -la .term-coder/plugins/my_plugin/

# Enable plugin debug mode
plugins:
  debug_mode: true

# Check plugin logs
tail -f .term-coder/logs/plugins.log
```

### Plugin Command Not Found

**Problem**: Plugin commands don't appear in CLI.

**Solutions**:
```bash
# List loaded plugins
tc plugins list

# Reload plugins
tc plugins reload

# Check plugin registration
tc --help | grep my-command

# Enable plugin
tc plugins enable my_plugin
```

## Diagnostic Commands

### System Health Check

```bash
# Run comprehensive diagnostics
tc diagnostics

# Check specific components
tc lsp status
tc git status
tc config validate
```

### Debug Information

```bash
# Enable debug mode
export TERM_CODER_DEBUG=true

# Check logs
tail -f .term-coder/logs/debug.log

# Export error report
tc export-errors --output debug_report.json
```

### Configuration Validation

```bash
# Validate configuration
tc config validate

# Test API connections
tc config test-connection

# Show effective configuration
tc config show --resolved
```

## Getting Help

### Built-in Help

```bash
# General help
tc --help

# Command-specific help
tc chat --help
tc edit --help

# Show version and build info
tc --version --verbose
```

### Log Files

Check these log files for detailed error information:

```bash
# Main application log
tail -f .term-coder/logs/term-coder.log

# Audit log
tail -f .term-coder/audit/audit.jsonl

# Debug log (if enabled)
tail -f .term-coder/logs/debug.log
```

### Community Support

- **GitHub Issues**: Report bugs and request features
- **Discussions**: Ask questions and share tips
- **Documentation**: Check latest docs for updates
- **Discord/Slack**: Real-time community support

### Reporting Bugs

When reporting issues, include:

1. **System information**:
   ```bash
   tc diagnostics > system_info.txt
   ```

2. **Error logs**:
   ```bash
   tc export-errors --output error_report.json
   ```

3. **Configuration** (redact sensitive info):
   ```bash
   cat .term-coder/config.yaml
   ```

4. **Steps to reproduce**:
   - Exact commands run
   - Expected vs actual behavior
   - Any error messages

5. **Environment details**:
   - Operating system
   - Python version
   - Term-coder version
   - Relevant dependencies

## Quick Fixes Checklist

When something isn't working, try these in order:

1. **Check basics**:
   ```bash
   tc --version
   tc diagnostics
   ```

2. **Validate configuration**:
   ```bash
   tc config validate
   ```

3. **Rebuild index**:
   ```bash
   tc index
   ```

4. **Check permissions**:
   ```bash
   ls -la .term-coder/
   ```

5. **Test with minimal config**:
   ```bash
   mv .term-coder/config.yaml .term-coder/config.yaml.backup
   tc init
   ```

6. **Check logs**:
   ```bash
   tail -20 .term-coder/logs/term-coder.log
   ```

7. **Try offline mode**:
   ```bash
   tc privacy offline_mode true
   ```

8. **Restart with clean state**:
   ```bash
   rm -rf .term-coder/cache/
   tc index
   ```

Most issues can be resolved with these steps. If problems persist, check the community resources or file a bug report with diagnostic information.