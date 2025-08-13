# CLI Reference

Complete reference for all term-coder commands and options.

## Global Options

These options are available for all commands:

- `--help`: Show help message and exit
- `--version`: Show version information

## Core Commands

### `tc init`

Initialize term-coder configuration in the current directory.

```bash
tc init
```

**What it does:**
- Creates `.term-coder/config.yaml` with default settings
- Sets up directory structure for sessions and cache
- Configures basic privacy and safety settings

**Example:**
```bash
cd my-project
tc init
# Creates .term-coder/config.yaml
```

---

### `tc chat`

Interactive chat with repository-aware context.

```bash
tc chat <message> [OPTIONS]
```

**Arguments:**
- `message`: Your question or instruction (required)

**Options:**
- `--files TEXT`: Specific files to include in context
- `--dir TEXT`: Directory to bias context selection toward
- `--model TEXT`: Override default model (e.g., "openai:gpt-4o")
- `--session TEXT`: Chat session name (default: "default")

**Examples:**
```bash
# Basic chat
tc chat "What does this project do?"

# Include specific files
tc chat "Explain this function" --files src/main.py src/utils.py

# Use different model
tc chat "Review this code" --model "anthropic:claude-3-sonnet"

# Named session
tc chat "Let's discuss architecture" --session architecture
```

**Session Management:**
- Sessions persist conversation history
- Stored in `.term-coder/sessions/`
- Use different sessions for different topics

---

### `tc search`

Search across your repository with multiple search modes.

```bash
tc search <query> [OPTIONS]
```

**Arguments:**
- `query`: Search terms (required)

**Options:**
- `--include TEXT`: Glob patterns to include (can be used multiple times)
- `--exclude TEXT`: Glob patterns to exclude (can be used multiple times)
- `--type TEXT`: File extensions to include (e.g., `--type py --type js`)
- `--top INTEGER`: Maximum results to return (default: 20)
- `--semantic`: Use semantic search with embeddings
- `--hybrid`: Combine lexical and semantic search
- `--both`: Show both lexical and semantic results separately

**Examples:**
```bash
# Basic lexical search
tc search "error handling"

# Semantic search
tc search "authentication logic" --semantic

# Hybrid search (recommended)
tc search "database connection" --hybrid

# Filter by file type
tc search "TODO" --type py --type js

# Include/exclude patterns
tc search "config" --include "**/*.yaml" --exclude "**/test_*"

# Show both search types
tc search "API endpoint" --both
```

**Search Types:**
- **Lexical**: Fast text matching using ripgrep
- **Semantic**: AI-powered meaning-based search
- **Hybrid**: Combines both for best results

---

### `tc index`

Build or rebuild the search index for your repository.

```bash
tc index [OPTIONS]
```

**Options:**
- `--include TEXT`: Glob patterns to include
- `--exclude TEXT`: Glob patterns to exclude

**Examples:**
```bash
# Index all files
tc index

# Index only Python files
tc index --include "**/*.py"

# Exclude test files
tc index --exclude "**/test_*" --exclude "**/*_test.py"
```

**What it does:**
- Scans repository files
- Extracts metadata and content
- Creates `.term-coder/index.tsv`
- Enables fast search and context selection

---

### `tc edit`

Generate edit proposals for files using AI.

```bash
tc edit <instruction> --files <files> [OPTIONS]
```

**Arguments:**
- `instruction`: Description of changes to make (required)

**Options:**
- `--files TEXT`: Target files to edit (required, can be used multiple times)
- `--no-llm`: Use deterministic transforms only (no AI)

**Examples:**
```bash
# Add error handling
tc edit "add try-catch blocks around file operations" --files src/file_utils.py

# Multiple files
tc edit "add type hints" --files src/main.py --files src/utils.py

# Deterministic mode
tc edit "format code" --files src/main.py --no-llm
```

**Workflow:**
1. Analyzes target files
2. Generates edit proposal
3. Shows unified diff
4. Saves proposal for review
5. Use `tc diff` and `tc apply` to complete

---

### `tc diff`

Show the currently pending edit proposal.

```bash
tc diff
```

**What it shows:**
- Unified diff of proposed changes
- Files affected
- Lines added/removed
- Safety score

**Example output:**
```diff
--- src/main.py
+++ src/main.py
@@ -10,6 +10,10 @@
 def process_file(filename):
+    try:
         with open(filename, 'r') as f:
             return f.read()
+    except FileNotFoundError:
+        print(f"File not found: {filename}")
+        return None
```

---

### `tc apply`

Apply the pending edit proposal to files.

```bash
tc apply [OPTIONS]
```

**Options:**
- `--pick TEXT`: Apply changes to specific files only
- `--unsafe`: Allow creating new files

**Examples:**
```bash
# Apply all changes
tc apply

# Apply to specific files only
tc apply --pick src/main.py

# Allow new file creation
tc apply --unsafe
```

**Safety Features:**
- Creates automatic backups
- Validates changes before applying
- Runs formatters (black, prettier, etc.)
- Can be rolled back if needed

---

### `tc run`

Execute shell commands in a sandboxed environment.

```bash
tc run <command> [OPTIONS]
```

**Arguments:**
- `command`: Shell command to execute (required)

**Options:**
- `--timeout INTEGER`: Timeout in seconds (default: 30)
- `--cpu INTEGER`: CPU seconds limit
- `--mem INTEGER`: Memory limit in MB
- `--no-network`: Disable network access

**Examples:**
```bash
# Run tests
tc run "python -m pytest tests/"

# With timeout
tc run "npm test" --timeout 60

# Resource limits
tc run "python script.py" --cpu 10 --mem 512

# No network access
tc run "python offline_script.py" --no-network
```

**Features:**
- Captures stdout/stderr
- Resource monitoring
- Execution time tracking
- Environment snapshotting

---

### `tc test`

Run tests with intelligent failure analysis.

```bash
tc test [OPTIONS]
```

**Options:**
- `--cmd TEXT`: Override test command
- `--framework TEXT`: Specify framework (pytest, jest, gotest)

**Examples:**
```bash
# Auto-detect and run tests
tc test

# Custom command
tc test --cmd "python -m pytest tests/ -v"

# Specific framework
tc test --framework pytest
```

**Features:**
- Auto-detects test frameworks
- Parses test results
- Identifies failures
- Suggests fixes

---

### `tc fix`

Analyze failures and propose fixes.

```bash
tc fix [OPTIONS]
```

**Options:**
- `--with-last-run / --no-with-last-run`: Use last command output (default: true)

**Examples:**
```bash
# Fix based on last command
tc fix

# Fix without using last run
tc fix --no-with-last-run
```

**What it does:**
- Analyzes error logs
- Identifies failure patterns
- Suggests command fixes or code edits
- Can generate edit proposals

---

### `tc explain`

Get detailed explanations of code.

```bash
tc explain <target> [OPTIONS]
```

**Arguments:**
- `target`: File path, range, or symbol (e.g., `file.py:10:20` or `file.py#ClassName`)

**Options:**
- `--model TEXT`: Override default model

**Examples:**
```bash
# Explain entire file
tc explain src/main.py

# Explain specific lines
tc explain src/main.py:10:25

# Explain a class or function
tc explain src/models.py#UserModel

# Use different model
tc explain complex_algorithm.py --model "openai:gpt-4o"
```

---

## Git Integration

### `tc review`

AI-powered code review of changes.

```bash
tc review [OPTIONS]
```

**Options:**
- `--range TEXT`: Git range to review (e.g., `HEAD~3..HEAD`)

**Examples:**
```bash
# Review staged changes
tc review

# Review specific range
tc review --range HEAD~3..HEAD

# Review branch changes
tc review --range main..feature-branch
```

---

### `tc commit`

Generate commit messages from staged changes.

```bash
tc commit [OPTIONS]
```

**Options:**
- `-m, --message TEXT`: Custom commit message

**Examples:**
```bash
# Generate commit message
tc commit

# Use custom message
tc commit -m "Fix authentication bug"
```

---

### `tc pr`

Generate pull request descriptions.

```bash
tc pr [OPTIONS]
```

**Options:**
- `--range TEXT`: Git range for PR (default: staged changes)
- `--model TEXT`: Override default model

**Examples:**
```bash
# PR for staged changes
tc pr

# PR for specific range
tc pr --range main..feature-branch
```

---

## Refactoring

### `tc refactor-rename`

Rename symbols across multiple files.

```bash
tc refactor-rename <old> <new> [OPTIONS]
```

**Arguments:**
- `old`: Current symbol name
- `new`: New symbol name

**Options:**
- `--include TEXT`: File patterns to include (default: `**/*.py`)
- `--exclude TEXT`: File patterns to exclude
- `--apply`: Apply changes immediately after preview

**Examples:**
```bash
# Preview rename
tc refactor-rename "old_function" "new_function"

# Apply immediately
tc refactor-rename "OldClass" "NewClass" --apply

# Specific file types
tc refactor-rename "oldVar" "newVar" --include "**/*.js" --include "**/*.ts"
```

---

## Code Generation

### `tc generate`

Generate code from templates.

```bash
tc generate <framework> <kind> <name> [OPTIONS]
```

**Arguments:**
- `framework`: Target framework (python, react, node)
- `kind`: Type to generate (module, component, script)
- `name`: Name for generated code

**Options:**
- `--out-dir PATH`: Output directory
- `--force`: Overwrite existing files

**Examples:**
```bash
# Generate Python module
tc generate python module UserService

# Generate React component
tc generate react component UserProfile --out-dir src/components

# Force overwrite
tc generate node script api-client --force
```

---

## Privacy and Security

### `tc privacy`

Manage privacy settings.

```bash
tc privacy [setting] [value]
```

**Arguments:**
- `setting`: Privacy setting to view/modify (optional)
- `value`: New value for the setting (optional)

**Examples:**
```bash
# Show all privacy settings
tc privacy

# Show specific setting
tc privacy offline_mode

# Update setting
tc privacy offline_mode true
tc privacy redact_secrets false
```

**Available Settings:**
- `offline_mode`: Enable/disable offline operation
- `redact_secrets`: Auto-redact sensitive information
- `audit_level`: Logging detail level
- `data_collection`: Allow data collection
- `analytics`: Send usage analytics
- `model_training`: Allow use for model training
- `error_reporting`: Send error reports

---

### `tc scan-secrets`

Scan for secrets in your codebase.

```bash
tc scan-secrets [path] [OPTIONS]
```

**Arguments:**
- `path`: Directory to scan (default: current directory)

**Options:**
- `--include TEXT`: Patterns to include
- `--exclude TEXT`: Patterns to exclude
- `--fix`: Automatically redact found secrets

**Examples:**
```bash
# Scan current directory
tc scan-secrets

# Scan specific path
tc scan-secrets src/

# Auto-fix secrets
tc scan-secrets --fix

# Include only Python files
tc scan-secrets --include "**/*.py"
```

---

### `tc audit`

View audit logs and export data.

```bash
tc audit [OPTIONS]
```

**Options:**
- `--days INTEGER`: Number of days to include (default: 7)
- `--export TEXT`: Export audit log to file

**Examples:**
```bash
# View recent audit summary
tc audit

# Last 30 days
tc audit --days 30

# Export to file
tc audit --export audit_report.json
```

---

## System Management

### `tc diagnostics`

Run comprehensive system diagnostics.

```bash
tc diagnostics
```

**What it checks:**
- System information
- Dependency availability
- Health status of components
- Error statistics
- Overall system health

**Example output:**
```
System Information:
  platform: linux
  python_version: 3.11.0
  working_directory: /home/user/project

Health Status:
  git: ✓
  ripgrep: ✓
  embeddings: ✓
  lsp_servers: ✗

Dependencies:
  git: ✓ (v2.39.0)
  python: ✓ (v3.11.0)
  ripgrep: ✓ (v13.0.0)
```

---

### `tc export-errors`

Export error reports for debugging.

```bash
tc export-errors [OPTIONS]
```

**Options:**
- `-o, --output TEXT`: Output file path (default: error_report.json)

**Examples:**
```bash
# Export to default file
tc export-errors

# Custom output file
tc export-errors -o debug_report.json
```

---

### `tc cleanup`

Clean up old logs and temporary files.

```bash
tc cleanup [OPTIONS]
```

**Options:**
- `--retention-days INTEGER`: Keep files newer than N days (default: 90)
- `--confirm`: Skip confirmation prompt

**Examples:**
```bash
# Clean with confirmation
tc cleanup

# Clean files older than 30 days
tc cleanup --retention-days 30

# Skip confirmation
tc cleanup --confirm
```

---

## Advanced Features

### `tc tui`

Launch the Text User Interface mode.

```bash
tc tui
```

**Features:**
- Interactive terminal interface
- Multiple panes for different views
- Keyboard shortcuts
- Real-time updates

**Controls:**
- `F1`: Help
- `Esc`: Exit
- `Tab`: Switch panes
- `Ctrl+C`: Cancel operation

---

### `tc lsp`

Manage Language Server Protocol integration.

```bash
tc lsp <action> [file]
```

**Arguments:**
- `action`: Action to perform (start, stop, status, diagnostics)
- `file`: File path for diagnostics (required for diagnostics action)

**Examples:**
```bash
# Check LSP status
tc lsp status

# Get diagnostics for file
tc lsp diagnostics src/main.py

# Start LSP servers
tc lsp start

# Stop LSP servers
tc lsp stop
```

---

### `tc symbols`

Extract and display symbols from files.

```bash
tc symbols <file> [OPTIONS]
```

**Arguments:**
- `file`: File to analyze

**Options:**
- `--type TEXT`: Filter by symbol type (function, class, variable)

**Examples:**
```bash
# Show all symbols
tc symbols src/main.py

# Show only functions
tc symbols src/main.py --type function

# Show only classes
tc symbols src/models.py --type class
```

---

### `tc frameworks`

Detect and display framework information.

```bash
tc frameworks
```

**What it shows:**
- Detected frameworks in the project
- Available commands for each framework
- Configuration files found
- Recommended workflows

---

## Configuration Commands

### Environment Variables

Term-coder respects these environment variables:

- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key
- `TERM_CODER_CONFIG`: Custom config file path
- `TERM_CODER_OFFLINE`: Force offline mode (set to "true")

### Exit Codes

Term-coder uses standard exit codes:

- `0`: Success
- `1`: General error
- `2`: Configuration error
- `130`: Interrupted by user (Ctrl+C)

### File Patterns

Many commands accept glob patterns:

- `**/*.py`: All Python files recursively
- `src/**/*.js`: JavaScript files in src/ and subdirectories
- `*.{py,js,ts}`: Files with multiple extensions
- `!test_*`: Exclude files starting with "test_"

Use `--include` and `--exclude` options to control which files are processed.