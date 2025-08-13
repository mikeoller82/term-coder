# Advanced Usage Guide

Power user features and advanced workflows for term-coder.

## Advanced Configuration

### Multi-Model Workflows

Configure different models for different tasks:

```yaml
llm:
  default_model: "openai:gpt-4o-mini"  # Fast, cost-effective
  heavy_model: "openai:gpt-4o"         # Complex tasks
  
  # Task-specific models
  task_models:
    chat: "openai:gpt-4o-mini"
    edit: "openai:gpt-4o"
    review: "anthropic:claude-3-sonnet"
    explain: "openai:gpt-4o"
    commit: "openai:gpt-4o-mini"
```

Use specific models for commands:
```bash
# Use heavy model for complex edits
tc edit "refactor this class to use dependency injection" --files src/service.py --model "openai:gpt-4o"

# Use fast model for simple questions
tc chat "what does this function do?" --model "openai:gpt-4o-mini"
```

### Advanced Context Selection

Fine-tune context selection for better results:

```yaml
retrieval:
  # Context selection strategy
  strategy: "hybrid"  # lexical, semantic, hybrid, recent
  
  # Token budget management
  max_tokens: 16000
  reserve_tokens: 2000  # Reserve for response
  
  # File selection
  max_files: 30
  min_relevance_score: 0.3
  
  # Boost factors
  recency_boost: 1.5      # Recently modified files
  directory_boost: 2.0    # Files in same directory
  extension_boost: 1.2    # Files with same extension
  
  # Context enhancement
  include_imports: true    # Include imported modules
  include_tests: true      # Include related test files
  include_docs: false      # Include documentation files
```

### Custom Search Patterns

Create sophisticated search patterns:

```bash
# Complex regex patterns
tc search "class \w+Service" --include "**/*.py"

# Multiple search terms with operators
tc search "authentication AND (login OR signin)" --semantic

# File type combinations
tc search "TODO" --type py --type js --type ts --type go

# Exclude patterns
tc search "config" --include "**/*.yaml" --exclude "**/test_*" --exclude "**/.git/**"
```

## Advanced Editing Workflows

### Multi-File Refactoring

Perform complex refactoring across multiple files:

```bash
# Rename across entire codebase
tc refactor-rename "old_function_name" "new_function_name" --include "**/*.py" --apply

# Multi-file architectural changes
tc edit "convert all database calls to use async/await pattern" \
  --files src/models/*.py \
  --files src/services/*.py \
  --files src/controllers/*.py
```

### Conditional Edits

Use context-aware editing:

```bash
# Edit based on framework detection
tc edit "add error handling appropriate for this framework" --files src/main.py

# Edit with specific constraints
tc edit "add logging but only if logging is not already present" --files src/service.py

# Edit with style consistency
tc edit "add type hints following the existing code style" --files src/utils.py
```

### Edit Templates and Patterns

Create reusable edit patterns:

```yaml
# .term-coder/edit-templates.yaml
templates:
  add_logging:
    instruction: "add comprehensive logging with appropriate log levels"
    patterns:
      - "import logging at the top"
      - "add logger = logging.getLogger(__name__)"
      - "add log statements at function entry/exit"
      - "add error logging in exception handlers"
  
  add_tests:
    instruction: "create comprehensive unit tests"
    patterns:
      - "import pytest and necessary modules"
      - "create test class with descriptive name"
      - "add test methods for all public functions"
      - "include edge cases and error conditions"
```

Use templates:
```bash
tc edit --template add_logging --files src/service.py
tc edit --template add_tests --files src/service.py
```

## Advanced Search and Context

### Semantic Search Tuning

Optimize semantic search for your codebase:

```yaml
search:
  semantic:
    # Model selection
    model: "sentence-transformers/all-mpnet-base-v2"  # Higher quality
    
    # Embedding parameters
    batch_size: 32
    max_seq_length: 512
    
    # Search parameters
    similarity_threshold: 0.5
    max_results: 100
    
    # Caching
    cache_embeddings: true
    cache_ttl: 86400  # 24 hours
    
    # Index optimization
    index_type: "faiss"  # faiss, annoy, hnswlib
    index_params:
      nlist: 100
      nprobe: 10
```

### Hybrid Search Optimization

Balance lexical and semantic search:

```yaml
retrieval:
  hybrid_weight: 0.7  # 70% semantic, 30% lexical
  
  # Dynamic weighting based on query
  dynamic_weighting:
    enabled: true
    rules:
      - pattern: "^(class|function|method) "
        weight: 0.3  # Favor lexical for code structure
      - pattern: "(how|why|what|explain)"
        weight: 0.9  # Favor semantic for questions
      - pattern: "TODO|FIXME|BUG"
        weight: 0.1  # Favor lexical for exact matches
```

### Context Enrichment

Enhance context with related information:

```yaml
context:
  enrichment:
    # Include related files
    include_imports: true
    include_callers: true
    include_callees: true
    
    # Include documentation
    include_docstrings: true
    include_comments: true
    include_readme: true
    
    # Include git context
    include_recent_commits: true
    include_blame_info: false
    
    # Include test context
    include_test_files: true
    include_test_coverage: false
```

## Advanced Git Integration

### Intelligent Commit Messages

Configure commit message generation:

```yaml
git:
  commit_message:
    # Template selection
    auto_detect_type: true
    
    # Templates
    templates:
      feat: "feat({scope}): {description}"
      fix: "fix({scope}): {description}"
      docs: "docs: {description}"
      style: "style: {description}"
      refactor: "refactor({scope}): {description}"
      test: "test: {description}"
      chore: "chore: {description}"
    
    # Scope detection
    scope_detection:
      enabled: true
      rules:
        - pattern: "src/auth/**"
          scope: "auth"
        - pattern: "src/api/**"
          scope: "api"
        - pattern: "tests/**"
          scope: "test"
```

### Advanced Code Review

Configure AI code review:

```yaml
review:
  # Review focus areas
  focus_areas:
    - security
    - performance
    - maintainability
    - testing
    - documentation
  
  # Review depth
  depth: "thorough"  # quick, standard, thorough
  
  # Custom review prompts
  prompts:
    security: "Focus on security vulnerabilities, input validation, and authentication"
    performance: "Look for performance bottlenecks, inefficient algorithms, and resource usage"
    maintainability: "Assess code clarity, documentation, and adherence to best practices"
```

Use advanced review features:
```bash
# Focused security review
tc review --focus security --range HEAD~5..HEAD

# Performance-focused review
tc review --focus performance --files src/api/*.py

# Comprehensive review with suggestions
tc review --depth thorough --suggest-improvements
```

## Advanced Testing Integration

### Framework-Specific Testing

Configure testing for different frameworks:

```yaml
testing:
  frameworks:
    python:
      commands:
        - "python -m pytest {files} -v"
        - "python -m pytest {files} --cov={module}"
      
      patterns:
        test_files: ["test_*.py", "*_test.py"]
        test_dirs: ["tests/", "test/"]
      
      coverage:
        enabled: true
        threshold: 80
    
    javascript:
      commands:
        - "npm test {files}"
        - "jest {files} --coverage"
      
      patterns:
        test_files: ["*.test.js", "*.spec.js"]
        test_dirs: ["__tests__/", "tests/"]
    
    go:
      commands:
        - "go test {packages} -v"
        - "go test {packages} -cover"
      
      patterns:
        test_files: ["*_test.go"]
```

### Test-Driven Development

Use term-coder for TDD workflows:

```bash
# Generate tests first
tc generate test UserService --framework python

# Run tests (should fail)
tc test --files tests/test_user_service.py

# Implement code to make tests pass
tc edit "implement UserService methods to pass the tests" --files src/user_service.py

# Run tests again
tc test --files tests/test_user_service.py

# Refactor with confidence
tc edit "refactor UserService for better performance" --files src/user_service.py
tc test  # Ensure tests still pass
```

## Advanced Privacy and Security

### Custom Secret Detection

Define custom secret patterns:

```yaml
security:
  secret_detection:
    patterns:
      - name: "custom_api_key"
        pattern: "CUSTOM_API_[A-Z0-9]{32}"
        severity: "high"
        replacement: "CUSTOM_API_[REDACTED]"
      
      - name: "database_url"
        pattern: "postgresql://[^\\s]+"
        severity: "critical"
        replacement: "postgresql://[REDACTED]"
      
      - name: "jwt_secret"
        pattern: "jwt[_-]?secret[\"']?\\s*[:=]\\s*[\"']([^\"'\\s]+)"
        severity: "high"
        replacement: "jwt_secret: [REDACTED]"
    
    # File exclusions
    exclude_patterns:
      - "**/.env.example"
      - "**/README.md"
      - "**/docs/**"
```

### Advanced Audit Logging

Configure comprehensive audit logging:

```yaml
audit:
  # Detailed logging
  log_level: "detailed"
  
  # Custom log format
  format: "json"  # json, text, structured
  
  # Log rotation
  rotation:
    max_size: "10MB"
    max_files: 10
    compress: true
  
  # Event filtering
  events:
    include:
      - "llm_request"
      - "file_modification"
      - "command_execution"
      - "search_query"
    
    exclude:
      - "heartbeat"
      - "status_check"
  
  # Privacy controls
  privacy:
    redact_prompts: false
    redact_responses: false
    redact_file_contents: true
    hash_user_data: true
```

## Performance Optimization

### Caching Strategies

Configure intelligent caching:

```yaml
performance:
  caching:
    # Response caching
    llm_responses:
      enabled: true
      ttl: 3600  # 1 hour
      max_size: "100MB"
    
    # Search result caching
    search_results:
      enabled: true
      ttl: 1800  # 30 minutes
      max_size: "50MB"
    
    # Embedding caching
    embeddings:
      enabled: true
      ttl: 86400  # 24 hours
      max_size: "200MB"
    
    # File content caching
    file_contents:
      enabled: true
      ttl: 300  # 5 minutes
      max_size: "20MB"
```

### Parallel Processing

Optimize for large repositories:

```yaml
performance:
  parallel:
    # Indexing
    indexing_workers: 8
    
    # Search
    search_workers: 4
    
    # Embedding generation
    embedding_workers: 2
    
    # File processing
    file_workers: 6
  
  # Memory management
  memory:
    max_heap_size: "2GB"
    gc_threshold: 0.8
    
  # I/O optimization
  io:
    buffer_size: 65536
    async_file_ops: true
```

### Resource Monitoring

Monitor resource usage:

```bash
# Check performance metrics
tc diagnostics --performance

# Monitor resource usage
tc monitor --duration 300  # 5 minutes

# Profile specific operations
tc profile search "complex query"
tc profile edit "large refactoring" --files src/**/*.py
```

## Custom Workflows

### Workflow Automation

Create custom workflow scripts:

```yaml
# .term-coder/workflows.yaml
workflows:
  code_review:
    description: "Complete code review workflow"
    steps:
      - command: "tc review --range HEAD~1..HEAD"
        description: "Review recent changes"
      
      - command: "tc test"
        description: "Run test suite"
      
      - command: "tc scan-secrets --fix"
        description: "Check for secrets"
      
      - command: "tc audit --export review_audit.json"
        description: "Export audit log"
  
  feature_development:
    description: "Feature development workflow"
    steps:
      - command: "tc generate test {feature_name} --framework {framework}"
        description: "Generate test skeleton"
      
      - command: "tc edit 'implement {feature_name}' --files {files}"
        description: "Implement feature"
      
      - command: "tc test --files {test_files}"
        description: "Run feature tests"
      
      - command: "tc review --files {files}"
        description: "Review implementation"
```

Run workflows:
```bash
# Run predefined workflow
tc workflow run code_review

# Run with parameters
tc workflow run feature_development \
  --feature_name "user authentication" \
  --framework python \
  --files src/auth.py \
  --test_files tests/test_auth.py
```

### Integration with External Tools

#### CI/CD Integration

```bash
# In your CI pipeline
#!/bin/bash

# Install term-coder
pip install term-coder

# Initialize in CI environment
tc init --ci-mode

# Run code review on PR
tc review --range origin/main..HEAD --format json > review_results.json

# Check for secrets
tc scan-secrets --fail-on-secrets

# Generate test coverage report
tc test --coverage --format junit > test_results.xml

# Export audit log
tc audit --export ci_audit.json
```

#### IDE Integration

Create IDE-specific integrations:

```json
// VS Code tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Term-Coder: Explain Current File",
      "type": "shell",
      "command": "tc",
      "args": ["explain", "${file}"],
      "group": "build",
      "presentation": {
        "echo": true,
        "reveal": "always",
        "focus": false,
        "panel": "new"
      }
    },
    {
      "label": "Term-Coder: Review Changes",
      "type": "shell",
      "command": "tc",
      "args": ["review"],
      "group": "build"
    }
  ]
}
```

#### Git Hooks Integration

```bash
# .git/hooks/pre-commit
#!/bin/bash

# Run secret scan
tc scan-secrets --fail-on-secrets

# Run code review on staged files
tc review --staged

# Generate commit message if not provided
if [ -z "$1" ]; then
  tc commit
fi
```

## Advanced Plugin Development

### Complex Plugin Example

```python
# advanced_plugin.py
from term_coder.plugins import Plugin, command, hook
from term_coder.plugins.types import PluginContext
import asyncio
import aiohttp

class AdvancedIntegrationPlugin(Plugin):
    name = "advanced_integration"
    version = "2.0.0"
    description = "Advanced integration with external services"
    
    def initialize(self, context: PluginContext) -> None:
        super().initialize(context)
        self.session = aiohttp.ClientSession()
        self.webhook_url = self.config.get("webhook_url")
    
    @command("deploy")
    async def deploy_command(
        self,
        environment: str = typer.Argument(..., help="Deployment environment"),
        dry_run: bool = typer.Option(False, help="Dry run mode")
    ) -> CommandResult:
        """Deploy application with AI-powered checks."""
        
        # Pre-deployment checks
        await self._run_pre_deployment_checks()
        
        # Generate deployment plan
        plan = await self._generate_deployment_plan(environment)
        
        if dry_run:
            self.console.print(f"[yellow]Dry run - would deploy: {plan}[/yellow]")
            return CommandResult(success=True, data={"plan": plan})
        
        # Execute deployment
        result = await self._execute_deployment(environment, plan)
        
        # Post-deployment verification
        await self._verify_deployment(environment)
        
        # Send notification
        await self._send_notification(environment, result)
        
        return CommandResult(success=result["success"], data=result)
    
    @hook("after_edit")
    async def auto_test_hook(self, files: list[str], success: bool) -> None:
        """Automatically run tests after edits."""
        if success and self.config.get("auto_test", True):
            # Run tests asynchronously
            await self._run_tests_async(files)
    
    async def _run_tests_async(self, files: list[str]) -> None:
        """Run tests asynchronously."""
        # Implementation here
        pass
```

### Plugin Distribution and Management

```bash
# Create plugin package
tc plugin create my-advanced-plugin --template advanced

# Test plugin locally
tc plugin test my-advanced-plugin

# Package for distribution
tc plugin package my-advanced-plugin

# Publish to registry
tc plugin publish my-advanced-plugin --registry pypi

# Install from registry
tc plugin install my-advanced-plugin

# Update plugin
tc plugin update my-advanced-plugin --version 2.0.0
```

## Monitoring and Observability

### Performance Monitoring

```yaml
monitoring:
  metrics:
    enabled: true
    interval: 60  # seconds
    
    collectors:
      - system_resources
      - llm_performance
      - search_performance
      - file_operations
    
    exporters:
      - prometheus
      - statsd
      - json_file
  
  alerts:
    enabled: true
    
    rules:
      - name: "high_memory_usage"
        condition: "memory_usage > 80%"
        action: "log_warning"
      
      - name: "slow_llm_response"
        condition: "llm_response_time > 30s"
        action: "switch_model"
```

### Health Checks

```bash
# Comprehensive health check
tc health --detailed

# Specific component checks
tc health --component llm
tc health --component search
tc health --component git

# Continuous monitoring
tc monitor --interval 30 --duration 3600  # 1 hour
```

## Best Practices for Advanced Usage

### 1. Configuration Management

- Use environment-specific configs
- Version control your configuration
- Use environment variables for secrets
- Validate configuration regularly

### 2. Performance Optimization

- Monitor resource usage
- Use appropriate caching strategies
- Optimize context selection
- Profile performance bottlenecks

### 3. Security and Privacy

- Regular secret scans
- Audit log monitoring
- Privacy setting reviews
- Access control implementation

### 4. Workflow Integration

- Automate repetitive tasks
- Integrate with existing tools
- Create custom workflows
- Document processes

### 5. Monitoring and Maintenance

- Regular health checks
- Performance monitoring
- Error tracking
- Capacity planning

These advanced features enable power users to fully leverage term-coder's capabilities for complex development workflows and enterprise environments.