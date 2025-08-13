# Requirements Document

## Introduction

Term-coder is a conversational coding assistant that operates directly in the terminal, providing repo-aware context and safe, non-destructive file editing capabilities. The system enables developers to interact with their codebase through natural language, perform code analysis, execute commands safely, and manage git workflows with AI assistance. The core philosophy centers on safety-first editing through diffs/patches with review loops, comprehensive repo understanding, and extensible architecture supporting multiple LLM backends.

## Requirements

### Requirement 1

**User Story:** As a developer, I want to have conversational interactions with my codebase in the terminal, so that I can get contextual help and perform coding tasks through natural language.

#### Acceptance Criteria

1. WHEN a user runs `tc chat [prompt]` THEN the system SHALL provide streaming responses with repo-aware context
2. WHEN a user continues a conversation THEN the system SHALL maintain session state and memory of recently touched files
3. WHEN a user asks questions about code THEN the system SHALL automatically select relevant context based on query, path, and recent edits
4. IF a user specifies files with `--files` flag THEN the system SHALL include those files in the active context
5. WHEN a user specifies a directory with `--dir` flag THEN the system SHALL include relevant files from that directory in context

### Requirement 2

**User Story:** As a developer, I want the system to understand my entire repository structure and content, so that I can get accurate, contextual assistance.

#### Acceptance Criteria

1. WHEN a user runs `tc index` THEN the system SHALL build a searchable index of source files, READMEs, configs, and tests
2. WHEN indexing THEN the system SHALL support configurable glob include/exclude patterns
3. WHEN a user searches with `tc search "<query>"` THEN the system SHALL provide both lexical (ripgrep) and semantic search results
4. WHEN a user searches with `--semantic` flag THEN the system SHALL prioritize embedding-based semantic search
5. IF the system is in offline mode THEN the system SHALL fall back to ripgrep-only search
6. WHEN selecting context THEN the system SHALL automatically choose relevant files based on query relevance and recent edit history

### Requirement 3

**User Story:** As a developer, I want to make safe, reviewable edits to my code, so that I can modify files without risk of breaking my codebase.

#### Acceptance Criteria

1. WHEN a user runs `tc edit "<instruction>"` THEN the system SHALL propose a unified diff without automatically applying changes
2. WHEN a diff is proposed THEN the system SHALL provide rationale explaining why each change was made
3. WHEN a user runs `tc diff` THEN the system SHALL display the pending AI-proposed diff with stats and summary
4. WHEN a user runs `tc apply` THEN the system SHALL apply the proposed patch with backup creation
5. IF a user runs `tc apply --pick hunks` THEN the system SHALL allow interactive selection of specific hunks to apply
6. WHEN applying patches THEN the system SHALL only modify tracked files unless `--unsafe` flag is used
7. WHEN a patch is applied THEN the system SHALL run configured formatter hooks (prettier, black, gofmt)

### Requirement 4

**User Story:** As a developer, I want to execute commands safely and get AI assistance with fixing issues, so that I can iterate quickly on problems.

#### Acceptance Criteria

1. WHEN a user runs `tc run "<cmd>"` THEN the system SHALL execute the command in a sandboxed environment with resource limits
2. WHEN a command is executed THEN the system SHALL capture stdout, stderr, exit code, and environment snapshot
3. WHEN a user runs `tc fix` THEN the system SHALL analyze recent run logs and propose fixes
4. IF a user specifies `--with last-run` THEN the system SHALL use the most recent command execution logs
5. WHEN a user runs `tc test` THEN the system SHALL execute configured test commands and capture results
6. IF tests fail THEN the system SHALL propose fixes based on test output and error messages

### Requirement 5

**User Story:** As a developer, I want AI assistance with code understanding and refactoring, so that I can better comprehend and improve my codebase.

#### Acceptance Criteria

1. WHEN a user runs `tc explain <path>` THEN the system SHALL provide detailed explanations of the specified file or function
2. WHEN a user specifies line numbers with `<path:line:end>` THEN the system SHALL focus explanation on that specific code section
3. WHEN a user runs refactor commands THEN the system SHALL perform multi-file refactors with safety checks
4. WHEN refactoring is complete THEN the system SHALL run post-refactor tests to verify functionality
5. WHEN a user requests code generation THEN the system SHALL scaffold modules, components, migrations, or scripts as specified

### Requirement 6

**User Story:** As a developer, I want AI assistance with git workflows and PR management, so that I can streamline my version control processes.

#### Acceptance Criteria

1. WHEN a user runs `tc review` THEN the system SHALL analyze staged changes or specified branch ranges
2. WHEN reviewing code THEN the system SHALL generate inline comments and summary feedback
3. WHEN a user runs `tc commit` THEN the system SHALL generate contextual commit messages based on staged changes
4. IF a user specifies `--message auto` THEN the system SHALL automatically use the AI-generated commit message
5. WHEN a user runs `tc pr` THEN the system SHALL draft PR descriptions with context of changes, risks, and testing notes
6. WHEN creating PRs THEN the system SHALL analyze the changeset and provide rollout recommendations

### Requirement 7

**User Story:** As a developer, I want to use different LLM backends and configure the system for my needs, so that I can optimize for cost, speed, and privacy requirements.

#### Acceptance Criteria

1. WHEN configuring models THEN the system SHALL support adapters for Anthropic, OpenAI, and local models via OpenRouter/Ollama
2. WHEN a user specifies `--model` flag THEN the system SHALL use the specified model for that command
3. WHEN configured THEN the system SHALL allow different models per command type (e.g., bigger model for refactor/review)
4. WHEN in offline mode THEN the system SHALL only use local models and disable external API calls
5. WHEN processing prompts THEN the system SHALL redact secrets and sensitive information from logs
6. WHEN a user sets privacy.offline to true THEN the system SHALL prevent all external network calls

### Requirement 8

**User Story:** As a developer, I want to extend the system with plugins and custom tools, so that I can adapt it to my specific workflow and technology stack.

#### Acceptance Criteria

1. WHEN a user runs `tc plugins list` THEN the system SHALL display all available and installed plugins
2. WHEN a user installs a plugin THEN the system SHALL register new tools and commands provided by the plugin
3. WHEN plugins are loaded THEN the system SHALL support language-aware tools (LSP, tree-sitter)
4. WHEN plugins are configured THEN the system SHALL support framework-specific commands (Django, React, Rust)
5. WHEN hooks are defined THEN the system SHALL execute pre-context, pre-prompt, post-response, and pre-apply hooks
6. WHEN custom reviewers are installed THEN the system SHALL integrate security, performance, and i18n review capabilities

### Requirement 9

**User Story:** As a developer, I want a responsive and informative user interface, so that I can efficiently interact with the system and understand its operations.

#### Acceptance Criteria

1. WHEN the system provides output THEN it SHALL use colorized streaming output with clear "tool call" blocks
2. WHEN a user enables TUI mode THEN the system SHALL provide a curses-based interface as an alternative to plain CLI
3. WHEN commands are executed THEN the system SHALL provide output capture panes and scrollback functionality
4. WHEN sessions are active THEN the system SHALL save transcripts to `.term-coder/sessions` for later reference
5. WHEN displaying diffs THEN the system SHALL show diff stats and summaries before applying changes

### Requirement 10

**User Story:** As a developer, I want comprehensive configuration options, so that I can customize the system behavior to match my development environment and preferences.

#### Acceptance Criteria

1. WHEN a user runs `tc init` THEN the system SHALL initialize configuration, allow model selection, and set index scope
2. WHEN configuration is needed THEN the system SHALL support `.term-coder/config.yaml` for all settings
3. WHEN indexing THEN the system SHALL respect `.term-coder/ignore` patterns in addition to `.gitignore`
4. WHEN a user runs `tc config get/set <key> [value]` THEN the system SHALL allow runtime configuration management
5. WHEN formatters are configured THEN the system SHALL apply language-specific formatting automatically
6. IF `git.create_branch_on_edit` is true THEN the system SHALL automatically create feature branches for edits