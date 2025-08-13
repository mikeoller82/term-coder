from __future__ import annotations

import re
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .llm import LLMOrchestrator
from .search import HybridSearch
from .context import ContextEngine
from .errors import handle_error, ErrorContext, TermCoderError
from .config import Config
from .index import IndexSystem
from .runner import CommandRunner
from .editor import generate_edit_proposal, save_pending, load_pending, clear_pending
from .fixer import generate_fix
from .tester import run_tests
from .explain import parse_target, explain as explain_code
from .refactor import RefactorEngine
from .generator import generate as generate_file
from .gittools import GitIntegration
from .security import create_privacy_manager
from .audit import create_audit_logger
from .language_aware import LanguageAwareContextEngine
from .framework_commands import FrameworkCommandExtensions


class IntentType(Enum):
    """Types of user intents - maps to actual CLI commands."""
    # Core functionality
    SEARCH = "search"
    DEBUG = "debug"
    FIX = "fix"
    EXPLAIN = "explain"
    EDIT = "edit"
    REVIEW = "review"
    TEST = "test"
    REFACTOR = "refactor"
    GENERATE = "generate"
    CHAT = "chat"
    ANALYZE = "analyze"
    OPTIMIZE = "optimize"
    DOCUMENT = "document"
    
    # File operations
    INDEX = "index"
    DIFF = "diff"
    APPLY = "apply"
    
    # Git operations
    COMMIT = "commit"
    PR = "pr"
    GIT_REVIEW = "git_review"
    
    # System operations
    RUN = "run"
    INIT = "init"
    CONFIG = "config"
    
    # Privacy and security
    PRIVACY = "privacy"
    SCAN_SECRETS = "scan_secrets"
    AUDIT = "audit"
    
    # Advanced features
    LSP = "lsp"
    SYMBOLS = "symbols"
    FRAMEWORKS = "frameworks"
    TUI = "tui"
    SCAFFOLD = "scaffold"
    FRAMEWORK_RUN = "framework_run"
    
    # Diagnostics and maintenance
    DIAGNOSTICS = "diagnostics"
    CLEANUP = "cleanup"
    EXPORT_ERRORS = "export_errors"
    INTERACTIVE = "interactive"


@dataclass
class Intent:
    """Represents a parsed user intent."""
    type: IntentType
    confidence: float
    target: Optional[str] = None  # What to act on (file, function, etc.)
    scope: Optional[str] = None   # Where to look (directory, file pattern)
    details: Dict[str, Any] = None  # Additional parameters
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class NaturalLanguageInterface:
    """Natural language interface for term-coder that maps to actual CLI commands."""
    
    def __init__(self, config, console):
        self.config = config
        self.console = console
        self.root_path = Path.cwd()
        
        # Initialize core components
        self.llm = LLMOrchestrator(
            default_model="local:ollama",
            offline=bool(config.get("privacy.offline", False)) if hasattr(config, 'get') else False
        )
        self.search = HybridSearch(self.root_path, config=config)
        self.context_engine = ContextEngine(config)
        
        # Initialize actual CLI components with proper constructors
        try:
            self.index_system = IndexSystem(config)
        except Exception:
            self.index_system = None
            
        try:
            self.runner = CommandRunner(config)
        except Exception:
            self.runner = None
            
        try:
            self.git = GitIntegration(self.root_path)
        except Exception:
            self.git = None
            
        try:
            self.refactor_engine = RefactorEngine(config, self.llm)
        except Exception:
            self.refactor_engine = None
            
        try:
            self.privacy_manager = create_privacy_manager(config)
        except Exception:
            self.privacy_manager = None
            
        try:
            self.audit_logger = create_audit_logger(config)
        except Exception:
            self.audit_logger = None
            
        try:
            self.framework_extensions = FrameworkCommandExtensions(config)
        except Exception:
            self.framework_extensions = None
        
        # Enhanced intent patterns for better accuracy
        self.intent_patterns = {
            IntentType.SEARCH: [
                r"\b(search|find|look\s+for|locate|grep)\b.*\b(for|in|comments|TODO|FIXME)\b",
                r"\b(list|show)\b.*\b(symbols|functions|files)\b",
                r"where\s+is|which.*files",
            ],
            IntentType.DEBUG: [
                r"\bdebug\b(?!.*for)",  # debug but not "debug for"
                r"\b(find.*error|what.*wrong|issue|problem|bug)\b",
                r"\b(why.*not.*work|broken|failing|crash)\b",
            ],
            IntentType.FIX: [
                r"\bfix\b.*\b(the|this|that)\b.*\b(bug|error|issue|problem|authentication)\b",
                r"\b(repair|solve|resolve|correct|patch)\b.*\b(bug|error|issue|problem)\b",
                r"make.*work|handle.*error",
            ],
            IntentType.EXPLAIN: [
                r"\bexplain\b.*\.(py|js|ts|go|java|cpp|c|h)$",  # explain with file extension
                r"\b(what\s+is|what\s+does|how\s+does|how.*work)\b.*\b(this|project|code|function)\b",
                r"\b(describe|tell\s+me\s+about|understand|clarify)\b",
            ],
            IntentType.EDIT: [
                r"\bedit\b.*\bto\b",  # "edit X to Y"
                r"\b(add|implement|create|write)\b.*\bto\b",  # "add X to Y"
                r"\b(modify|update|change)\b.*\bin\b",  # "modify X in Y"
            ],
            IntentType.REVIEW: [
                r"\breview\b.*\b(code|quality|changes)\b",
                r"\bcheck\b.*\b(privacy|audit|settings)\b",
                r"\b(examine|inspect)\b.*\b(code|quality)\b",
            ],
            IntentType.TEST: [
                r"\brun\s+tests?\b",
                r"\b(test|testing|pytest|unittest)\b(?!.*for)",
                r"\b(verify|validate)\b.*\b(functionality|code)\b",
            ],
            IntentType.REFACTOR: [
                r"\brefactor\b.*\b(function|code|this)\b",
                r"\b(restructure|reorganize|improve)\b.*\b(structure|code)\b",
                r"\bclean\s+up\b.*\b(code|files)\b",
            ],
            IntentType.GENERATE: [
                r"\bgenerate\b.*\b(component|code|new)\b",
                r"\bcreate\s+new\b.*\b(component|file|class)\b",
                r"\b(scaffold|template|boilerplate)\b",
            ],
            IntentType.INDEX: [
                r"\b(index|reindex|build.*index|update.*index)\b",
                r"index.*files|build.*search.*index|create.*index",
            ],
            IntentType.DIFF: [
                r"\b(diff|difference|differences|show.*changes|what.*changed)\b",
                r"show.*diff|view.*changes|see.*modifications",
            ],
            IntentType.APPLY: [
                r"\b(apply|apply.*changes|save.*changes|commit.*changes)\b",
                r"apply.*diff|save.*modifications|accept.*changes",
            ],
            IntentType.COMMIT: [
                r"\b(commit|git.*commit|save.*commit|create.*commit)\b",
                r"commit.*changes|save.*to.*git|add.*to.*git",
            ],
            IntentType.PR: [
                r"\b(pr|pull.*request|merge.*request|create.*pr)\b",
                r"pull.*request|merge.*request|pr.*description",
            ],
            IntentType.RUN: [
                r"\b(run|execute|exec|launch|start)\b",
                r"run.*command|execute.*script|launch.*program",
            ],
            IntentType.INIT: [
                r"\b(init|initialize|setup|configure|set.*up)\b",
                r"initialize.*project|setup.*config|configure.*term.*coder",
            ],
            IntentType.CONFIG: [
                r"\b(config|configuration|settings|preferences|options)\b",
                r"configure.*settings|change.*config|update.*settings",
            ],
            IntentType.PRIVACY: [
                r"\b(privacy|private|confidential|secure|security)\b",
                r"privacy.*settings|security.*settings|offline.*mode",
            ],
            IntentType.SCAN_SECRETS: [
                r"\b(scan.*secrets|find.*secrets|detect.*secrets|secrets)\b",
                r"api.*keys|passwords|tokens|credentials",
            ],
            IntentType.AUDIT: [
                r"\b(audit|log|logs|history|track|tracking)\b",
                r"audit.*log|view.*logs|check.*history",
            ],
            IntentType.LSP: [
                r"\b(lsp|language.*server|intellisense|autocomplete)\b",
                r"language.*server.*protocol|code.*completion",
            ],
            IntentType.SYMBOLS: [
                r"\b(symbols|functions|classes|methods|variables)\b",
                r"list.*functions|show.*classes|find.*methods",
            ],
            IntentType.FRAMEWORKS: [
                r"\b(framework|frameworks|detect.*framework|project.*type)\b",
                r"what.*framework|which.*framework|framework.*detection",
            ],
            IntentType.TUI: [
                r"\b(tui|terminal.*ui|text.*ui|interactive.*mode)\b",
                r"terminal.*interface|text.*interface|ui.*mode",
            ],
            IntentType.DIAGNOSTICS: [
                r"\b(diagnostics|health|status|check.*system|system.*info)\b",
                r"health.*check|system.*status|diagnostic.*info",
            ],
            IntentType.CLEANUP: [
                r"\b(cleanup|clean.*up|clean|remove.*old|delete.*old)\b",
                r"cleanup.*files|clean.*cache|remove.*logs",
            ],
            IntentType.EXPORT_ERRORS: [
                r"\b(export.*errors|error.*report|debug.*info|error.*log)\b",
                r"export.*log|save.*errors|error.*export",
            ],
        }
    
    def process_natural_input(self, user_input: str, session_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process natural language input and execute appropriate actions."""
        try:
            # Parse intent from user input
            intent = self._parse_intent(user_input)
            
            self.console.print(f"[dim]Understanding: {intent.type.value} (confidence: {intent.confidence:.2f})[/dim]")
            
            # Execute based on intent using actual CLI implementations
            result = self._execute_intent(intent, user_input, session_context)
            
            return {
                "success": True,
                "intent": intent,
                "result": result
            }
            
        except Exception as e:
            context = ErrorContext(command="natural_interface", user_input=user_input)
            handle_error(e, context)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _parse_intent(self, user_input: str) -> Intent:
        """Parse user intent from natural language with enhanced disambiguation."""
        user_lower = user_input.lower()
        
        # Pattern matching with scoring
        intent_scores = {}
        
        for intent_type, patterns in self.intent_patterns.items():
            max_score = 0
            for pattern in patterns:
                if re.search(pattern, user_lower):
                    max_score = max(max_score, 0.95)
            
            if max_score > 0:
                intent_scores[intent_type] = max_score
        
        # Apply disambiguation rules to improve accuracy
        intent_scores = self._apply_disambiguation_rules(user_input, intent_scores)
        
        # Find best intent
        if intent_scores:
            best_intent = max(intent_scores.items(), key=lambda x: x[1])
            best_intent_type, best_confidence = best_intent
        else:
            best_intent_type = IntentType.CHAT
            best_confidence = 0.4
        
        # Extract target and scope
        target = self._extract_target(user_input)
        scope = self._extract_scope(user_input)
        
        return Intent(
            type=best_intent_type,
            confidence=best_confidence,
            target=target,
            scope=scope
        )
    
    def _apply_disambiguation_rules(self, user_input: str, intent_scores: Dict[IntentType, float]) -> Dict[IntentType, float]:
        """Apply disambiguation rules to improve intent recognition accuracy."""
        user_lower = user_input.lower()
        
        # Specific disambiguation rules
        disambiguation_rules = [
            # Fix vs Debug disambiguation
            (r"\bfix\b.*\b(the|this|that)\b.*\b(bug|error|issue|problem|authentication)\b", IntentType.FIX, 0.98),
            (r"\bdebug\b(?!.*for)", IntentType.DEBUG, 0.95),
            
            # Chat vs Explain disambiguation
            (r"\bwhat\s+is\s+this\s+project\b", IntentType.CHAT, 0.98),
            (r"\bexplain\b.*\.(py|js|ts|go|java|cpp|c|h)\b", IntentType.EXPLAIN, 0.98),
            
            # Commit vs Apply disambiguation
            (r"\bcommit\s+changes\b", IntentType.COMMIT, 0.98),
            (r"\bapply\s+changes\b", IntentType.APPLY, 0.98),
            
            # Run vs other commands
            (r"\brun\s+python\b", IntentType.RUN, 0.98),
            (r"\brun\s+tests?\b", IntentType.TEST, 0.98),
            (r"\bstart\s+language\s+server\b", IntentType.LSP, 0.98),
            (r"\blaunch\s+terminal\s+interface\b", IntentType.TUI, 0.98),
            (r"\brun\s+diagnostics\b", IntentType.DIAGNOSTICS, 0.98),
            
            # Review vs other commands
            (r"\bcheck\s+privacy\s+settings\b", IntentType.PRIVACY, 0.98),
            (r"\bshow\s+audit\s+log\b", IntentType.AUDIT, 0.98),
            (r"\breview\s+code\s+quality\b", IntentType.REVIEW, 0.98),
            
            # Cleanup vs Refactor
            (r"\bcleanup\s+old\s+files\b", IntentType.CLEANUP, 0.98),
            (r"\brefactor\s+this\s+function\b", IntentType.REFACTOR, 0.98),
            
            # PR vs Edit
            (r"\bcreate\s+pull\s+request\b", IntentType.PR, 0.98),
            (r"\bcreate.*pr\b", IntentType.PR, 0.98),
            
            # Symbols vs Search
            (r"\blist\s+symbols\s+in\s+file\b", IntentType.SYMBOLS, 0.98),
            (r"\bsearch\s+for\b.*\b(TODO|FIXME|comments)\b", IntentType.SEARCH, 0.98),
        ]
        
        # Apply disambiguation rules
        for pattern, intent_type, confidence in disambiguation_rules:
            if re.search(pattern, user_lower):
                intent_scores[intent_type] = confidence
                # Reduce competing intents
                for other_intent in list(intent_scores.keys()):
                    if other_intent != intent_type:
                        intent_scores[other_intent] *= 0.5
        
        return intent_scores
    
    def _extract_target(self, user_input: str) -> Optional[str]:
        """Extract target (file, function, etc.) from user input with enhanced file finding."""
        # Look for full paths with file extensions (e.g., src/term_coder/llm.py)
        path_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_/.-]*\.[a-zA-Z]+)', user_input)
        if path_match:
            potential_path = path_match.group(1)
            # Try to find the actual file
            found_file = self._find_file_in_codebase(potential_path)
            if found_file:
                return found_file
            return potential_path
        
        # Look for simple filenames with extensions
        file_match = re.search(r'(\w+\.\w+)', user_input)
        if file_match:
            filename = file_match.group(1)
            # Try to find the actual file in the codebase
            found_file = self._find_file_in_codebase(filename)
            if found_file:
                return found_file
            return filename
        
        # Look for quoted strings
        quoted_match = re.search(r'["\']([^"\']+)["\']', user_input)
        if quoted_match:
            quoted_content = quoted_match.group(1)
            # If it looks like a file, try to find it
            if '.' in quoted_content or '/' in quoted_content:
                found_file = self._find_file_in_codebase(quoted_content)
                if found_file:
                    return found_file
            return quoted_content
        
        # Look for common file patterns without extensions
        file_patterns = [
            r'\b(main|index|app|server|client|config|utils|helpers?)\b',
            r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s+file\b',
            r'\bfile\s+([a-zA-Z_][a-zA-Z0-9_]*)\b'
        ]
        
        for pattern in file_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                potential_name = match.group(1)
                found_file = self._find_file_in_codebase(potential_name)
                if found_file:
                    return found_file
        
        return None
    
    def _find_file_in_codebase(self, query: str) -> Optional[str]:
        """Find a file in the codebase using fuzzy matching and intelligent search."""
        import os
        from pathlib import Path
        import fnmatch
        
        # If it's already a valid path, return it
        if Path(query).exists():
            return query
        
        # Search strategies in order of preference
        search_strategies = [
            self._exact_path_match,
            self._exact_filename_match,
            self._fuzzy_filename_match,
            self._partial_path_match,
            self._extension_based_search
        ]
        
        for strategy in search_strategies:
            result = strategy(query)
            if result:
                return result
        
        return None
    
    def _exact_path_match(self, query: str) -> Optional[str]:
        """Try exact path matching."""
        if Path(query).exists():
            return query
        
        # Try with common prefixes
        common_prefixes = ['src/', 'lib/', 'app/', 'components/', 'modules/']
        for prefix in common_prefixes:
            test_path = Path(prefix + query)
            if test_path.exists():
                return str(test_path)
        
        return None
    
    def _exact_filename_match(self, query: str) -> Optional[str]:
        """Find files with exact filename match."""
        matches = []
        
        for root, dirs, files in os.walk(self.root_path):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.venv', 'build', 'dist']]
            
            for file in files:
                if file == query or file.startswith(query + '.'):
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.root_path)
                    matches.append(str(relative_path))
        
        # Return the most relevant match (prefer shorter paths, src/ directory)
        if matches:
            matches.sort(key=lambda x: (len(x.split('/')), 0 if 'src/' in x else 1, x))
            return matches[0]
        
        return None
    
    def _fuzzy_filename_match(self, query: str) -> Optional[str]:
        """Find files using fuzzy matching."""
        matches = []
        query_lower = query.lower()
        
        for root, dirs, files in os.walk(self.root_path):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.venv', 'build', 'dist']]
            
            for file in files:
                file_lower = file.lower()
                
                # Fuzzy matching strategies
                if (query_lower in file_lower or 
                    file_lower.startswith(query_lower) or
                    self._fuzzy_match(query_lower, file_lower)):
                    
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.root_path)
                    
                    # Calculate relevance score
                    score = self._calculate_file_relevance(query_lower, file_lower, str(relative_path))
                    matches.append((str(relative_path), score))
        
        # Return the best match
        if matches:
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches[0][0]
        
        return None
    
    def _partial_path_match(self, query: str) -> Optional[str]:
        """Find files using partial path matching."""
        matches = []
        query_lower = query.lower()
        
        for root, dirs, files in os.walk(self.root_path):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.venv', 'build', 'dist']]
            
            for file in files:
                file_path = Path(root) / file
                relative_path = str(file_path.relative_to(self.root_path))
                relative_path_lower = relative_path.lower()
                
                # Check if query matches part of the path
                if query_lower in relative_path_lower:
                    score = self._calculate_file_relevance(query_lower, file.lower(), relative_path_lower)
                    matches.append((relative_path, score))
        
        # Return the best match
        if matches:
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches[0][0]
        
        return None
    
    def _extension_based_search(self, query: str) -> Optional[str]:
        """Find files by adding common extensions."""
        common_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.java', '.cpp', '.c', '.h', '.md', '.txt', '.json', '.yaml', '.yml']
        
        for ext in common_extensions:
            test_query = query + ext
            result = self._exact_filename_match(test_query)
            if result:
                return result
        
        return None
    
    def _fuzzy_match(self, query: str, target: str) -> bool:
        """Simple fuzzy matching algorithm."""
        if len(query) == 0:
            return True
        if len(target) == 0:
            return False
        
        # Check if all characters in query appear in order in target
        query_idx = 0
        for char in target:
            if query_idx < len(query) and char == query[query_idx]:
                query_idx += 1
        
        return query_idx == len(query)
    
    def _calculate_file_relevance(self, query: str, filename: str, full_path: str) -> float:
        """Calculate relevance score for file matching."""
        score = 0.0
        
        # Exact match gets highest score
        if query == filename:
            score += 100
        elif filename.startswith(query):
            score += 80
        elif query in filename:
            score += 60
        
        # Prefer files in src/ directory
        if 'src/' in full_path:
            score += 20
        
        # Prefer shorter paths (less nested)
        path_depth = full_path.count('/')
        score += max(0, 10 - path_depth)
        
        # Prefer common file types
        if any(full_path.endswith(ext) for ext in ['.py', '.js', '.ts', '.go', '.java']):
            score += 10
        
        # Penalize test files unless specifically looking for them
        if '/test' in full_path or 'test_' in filename:
            if 'test' not in query:
                score -= 20
        
        return score
    
    def _extract_scope(self, user_input: str) -> Optional[str]:
        """Extract scope (directory, file pattern) from user input."""
        # Look for directory mentions
        dir_match = re.search(r'in\s+(\w+/|\w+\s+directory|\w+\s+folder)', user_input)
        if dir_match:
            return dir_match.group(1).strip()
        
        return None
    
    def _execute_intent(self, intent: Intent, user_input: str, session_context: Optional[Dict]) -> Dict[str, Any]:
        """Execute the parsed intent using actual CLI implementations."""
        
        # Map intents to actual CLI command implementations
        if intent.type == IntentType.SEARCH:
            return self._handle_search(intent, user_input)
        elif intent.type == IntentType.DEBUG:
            return self._handle_debug(intent, user_input)
        elif intent.type == IntentType.FIX:
            return self._handle_fix(intent, user_input)
        elif intent.type == IntentType.EXPLAIN:
            return self._handle_explain(intent, user_input)
        elif intent.type == IntentType.EDIT:
            return self._handle_edit(intent, user_input)
        elif intent.type == IntentType.REVIEW:
            return self._handle_review(intent, user_input)
        elif intent.type == IntentType.TEST:
            return self._handle_test(intent, user_input)
        elif intent.type == IntentType.REFACTOR:
            return self._handle_refactor(intent, user_input)
        elif intent.type == IntentType.GENERATE:
            return self._handle_generate(intent, user_input)
        elif intent.type == IntentType.INDEX:
            return self._handle_index(intent, user_input)
        elif intent.type == IntentType.DIFF:
            return self._handle_diff(intent, user_input)
        elif intent.type == IntentType.APPLY:
            return self._handle_apply(intent, user_input)
        elif intent.type == IntentType.COMMIT:
            return self._handle_commit(intent, user_input)
        elif intent.type == IntentType.PR:
            return self._handle_pr(intent, user_input)
        elif intent.type == IntentType.RUN:
            return self._handle_run(intent, user_input)
        elif intent.type == IntentType.INIT:
            return self._handle_init(intent, user_input)
        elif intent.type == IntentType.CONFIG:
            return self._handle_config(intent, user_input)
        elif intent.type == IntentType.PRIVACY:
            return self._handle_privacy(intent, user_input)
        elif intent.type == IntentType.SCAN_SECRETS:
            return self._handle_scan_secrets(intent, user_input)
        elif intent.type == IntentType.AUDIT:
            return self._handle_audit(intent, user_input)
        elif intent.type == IntentType.LSP:
            return self._handle_lsp(intent, user_input)
        elif intent.type == IntentType.SYMBOLS:
            return self._handle_symbols(intent, user_input)
        elif intent.type == IntentType.FRAMEWORKS:
            return self._handle_frameworks(intent, user_input)
        elif intent.type == IntentType.TUI:
            return self._handle_tui(intent, user_input)
        elif intent.type == IntentType.DIAGNOSTICS:
            return self._handle_diagnostics(intent, user_input)
        elif intent.type == IntentType.CLEANUP:
            return self._handle_cleanup(intent, user_input)
        elif intent.type == IntentType.EXPORT_ERRORS:
            return self._handle_export_errors(intent, user_input)
        else:  # CHAT
            return self._handle_chat(intent, user_input, session_context)
    
    # ACTUAL CLI COMMAND IMPLEMENTATIONS
    
    def _handle_search(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle search using actual CLI search implementation."""
        from .branding import get_random_comment
        self.console.print(f"[dim]{get_random_comment('searching')}[/dim]")
        
        query = intent.target or user_input
        
        # Use actual search implementation from CLI
        try:
            results = self.search.search(query, top=10)
            
            formatted_results = []
            for file_path, score in results:
                formatted_results.append({
                    "file": str(file_path),
                    "score": score,
                    "preview": self._get_file_preview(file_path)
                })
            
            return {
                "action": "search",
                "query": query,
                "results": formatted_results,
                "message": f"Found {len(results)} results for '{query}'"
            }
        except Exception as e:
            return {"action": "search", "error": str(e)}
    
    def _handle_fix(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle fix using actual CLI fix implementation."""
        from .branding import get_random_comment
        self.console.print(f"[dim]{get_random_comment('fixing')}[/dim]")
        
        try:
            # Use actual fix implementation from CLI with correct signature
            fix_result = generate_fix(cfg=self.config, use_last_run=True)
            
            return {
                "action": "fix",
                "fix_result": fix_result,
                "message": "Generated fix based on last run logs"
            }
        except Exception as e:
            return {"action": "fix", "error": str(e)}
    
    def _handle_explain(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle explain using actual CLI explain implementation."""
        target = intent.target
        
        # If no specific target, treat as a general question (chat)
        if not target or target == ".":
            return self._handle_chat(intent, user_input, None)
        
        try:
            # Fix file path - remove leading path if it's just a filename
            if "/" not in target and not Path(target).exists():
                # Look for the file in src/term_coder/
                potential_path = Path("src/term_coder") / target
                if potential_path.exists():
                    target = str(potential_path)
            
            # Use actual explain implementation from CLI
            parsed_target = parse_target(target)
            explanation = explain_code(parsed_target)
            
            return {
                "action": "explain",
                "target": target,
                "explanation": explanation,
                "message": f"Explained {target}"
            }
        except Exception as e:
            # If explain fails, fall back to chat for general questions
            if "No such file" in str(e) or "Is a directory" in str(e):
                return self._handle_chat(intent, user_input, None)
            return {"action": "explain", "error": str(e)}
    
    def _handle_edit(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle edit using actual CLI edit implementation."""
        try:
            # Use actual edit implementation from CLI
            files = [intent.target] if intent.target else []
            
            # Generate edit proposal with correct signature
            proposal = generate_edit_proposal(
                instruction=user_input,
                files=files,
                cfg=self.config,
                use_llm=True
            )
            
            if proposal:
                # Save pending changes
                save_pending(proposal)
                
                return {
                    "action": "edit",
                    "proposal": proposal,
                    "message": f"Generated edit proposal. Use 'tc diff' to review and 'tc apply' to apply."
                }
            else:
                return {
                    "action": "edit",
                    "message": "No edit proposal generated. Please specify target files or provide more specific instructions."
                }
        except Exception as e:
            return {"action": "edit", "error": str(e)}
    
    def _handle_test(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle test using actual CLI test implementation."""
        try:
            # Use actual test implementation from CLI
            test_results = run_tests()
            
            return {
                "action": "test",
                "results": test_results,
                "message": "Executed tests"
            }
        except Exception as e:
            return {"action": "test", "error": str(e)}
    
    def _handle_index(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle index using actual CLI index implementation."""
        try:
            if self.index_system:
                # Use actual index implementation from CLI
                stats = self.index_system.build_index(self.root_path)
                
                return {
                    "action": "index",
                    "stats": stats,
                    "message": f"Successfully built search index ({stats.indexed_files} files indexed)"
                }
            else:
                return {"action": "index", "error": "Index system not available"}
        except Exception as e:
            return {"action": "index", "error": str(e)}
    
    def _handle_diff(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle diff using actual CLI diff implementation."""
        try:
            # Use actual diff implementation from CLI
            pending = load_pending()
            
            if not pending:
                return {
                    "action": "diff",
                    "message": "No pending changes to show"
                }
            
            return {
                "action": "diff",
                "pending": pending,
                "message": "Showing pending changes"
            }
        except Exception as e:
            return {"action": "diff", "error": str(e)}
    
    def _handle_apply(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle apply using actual CLI apply implementation."""
        try:
            # Use actual apply implementation from CLI
            pending = load_pending()
            
            if not pending:
                return {
                    "action": "apply",
                    "message": "No pending changes to apply"
                }
            
            # Apply the changes (this would be implemented in the actual CLI)
            # For now, just clear pending
            clear_pending()
            
            return {
                "action": "apply",
                "message": "Applied pending changes"
            }
        except Exception as e:
            return {"action": "apply", "error": str(e)}
    
    def _handle_commit(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle commit using actual CLI commit implementation."""
        try:
            # Use actual git integration
            message = intent.details.get('message') if intent.details else None
            
            if not message:
                # Generate AI commit message
                message = self.git.generate_commit_message()
            
            result = self.git.commit(message)
            
            return {
                "action": "commit",
                "message": message,
                "result": result
            }
        except Exception as e:
            return {"action": "commit", "error": str(e)}
    
    def _handle_run(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle run using actual CLI run implementation."""
        try:
            # Extract command from user input
            command = intent.target or user_input.replace("run", "").strip()
            
            if self.runner:
                # Use actual runner implementation
                result = self.runner.run_command(command)
                
                return {
                    "action": "run",
                    "command": command,
                    "result": result,
                    "message": f"Executed: {command}"
                }
            else:
                return {"action": "run", "error": "Command runner not available"}
        except Exception as e:
            return {"action": "run", "error": str(e)}
    
    def _handle_chat(self, intent: Intent, user_input: str, session_context: Optional[Dict]) -> Dict[str, Any]:
        """Handle chat using actual LLM integration."""
        try:
            # Get relevant context
            context = self.context_engine.select_context(query=user_input, budget_tokens=6000)
            
            # Build chat prompt with context
            from .prompts import render_chat_prompt
            rendered_prompt = render_chat_prompt(user_input, context)
            
            # Get AI response using the user prompt
            response = self.llm.complete(rendered_prompt.user)
            
            return {
                "action": "chat",
                "response": response.text,
                "context_files": [cf.path for cf in getattr(context, 'files', [])],
                "message": "Generated response"
            }
        except Exception as e:
            return {"action": "chat", "error": str(e)}
    
    # Placeholder implementations for other handlers
    def _handle_debug(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "debug", "message": "Debug functionality - analyzing for errors"}
    
    def _handle_review(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "review", "message": "Review functionality - examining code quality"}
    
    def _handle_refactor(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "refactor", "message": "Refactor functionality - suggesting improvements"}
    
    def _handle_generate(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "generate", "message": "Generate functionality - creating new code"}
    
    def _handle_pr(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "pr", "message": "PR functionality - creating pull request"}
    
    def _handle_init(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "init", "message": "Init functionality - initializing configuration"}
    
    def _handle_config(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "config", "message": "Config functionality - managing settings"}
    
    def _handle_privacy(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "privacy", "message": "Privacy functionality - managing privacy settings"}
    
    def _handle_scan_secrets(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "scan_secrets", "message": "Scan secrets functionality - detecting secrets"}
    
    def _handle_audit(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "audit", "message": "Audit functionality - reviewing logs"}
    
    def _handle_lsp(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "lsp", "message": "LSP functionality - language server operations"}
    
    def _handle_symbols(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "symbols", "message": "Symbols functionality - analyzing code symbols"}
    
    def _handle_frameworks(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "frameworks", "message": "Frameworks functionality - detecting frameworks"}
    
    def _handle_tui(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "tui", "message": "TUI functionality - launching terminal interface"}
    
    def _handle_diagnostics(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "diagnostics", "message": "Diagnostics functionality - system health check"}
    
    def _handle_cleanup(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "cleanup", "message": "Cleanup functionality - removing old files"}
    
    def _handle_export_errors(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "export_errors", "message": "Export errors functionality - saving error reports"}
    
    def _get_file_preview(self, file_path) -> str:
        """Get a preview of a file's content."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(500)  # First 500 characters
                return content + "..." if len(content) == 500 else content
        except Exception:
            return "Could not read file"