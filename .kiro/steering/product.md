# Product Overview

Term-coder is a terminal-based coding assistant that provides repo-aware context and safe, non-destructive file editing capabilities. It enables developers to interact with their codebase through natural language, perform code analysis, execute commands safely, and manage git workflows with AI assistance.

## Core Philosophy

- **Safety-first editing**: All modifications go through diff/patch review loops before application
- **Repo-aware context**: Intelligent context selection using hybrid search (lexical + semantic)
- **Extensible architecture**: Support for multiple LLM backends and plugin system
- **Developer-centric**: Terminal-native interface with streaming responses and session management

## Key Features

- Conversational chat interface with streaming responses
- Safe file editing through unified diffs with backup creation
- Hybrid search combining ripgrep (lexical) and embeddings (semantic)
- Sandboxed command execution with resource limits
- Git integration for reviews, commits, and PR generation
- Multi-model support (OpenAI, Anthropic, local via Ollama)
- Offline mode for privacy-conscious development
- Plugin system for extensibility

## Target Users

Developers who want AI assistance that understands their entire codebase context while maintaining full control over changes through explicit review and approval workflows.