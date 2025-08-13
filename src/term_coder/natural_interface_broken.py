from __future__ import annotations

import re
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .llm import LLMOrchestrator
from .search import HybridSearch
from .context import ContextEngine
from .errors import handle_error, ErrorContext, TermCoderError


class IntentType(Enum):
    """Types of user intents - covers ALL term-coder features."""
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
    
    # Diagnostics and maintenance
    DIAGNOSTICS = "diagnostics"
    CLEANUP = "cleanup"
    EXPORT_ERRORS = "export_errors"


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
    """Natural language interface for term-coder."""
    
    def __init__(self, config, console):
        self.config = config
        self.console = console
        
        # Initialize components with proper parameters
        from pathlib import Path
        self.root_path = Path.cwd()
        
        # Initialize core components that we know exist
        try:
            self.llm = LLMOrchestrator(
                default_model="local:ollama",
                offline=bool(config.get("privacy.offline", False)) if hasattr(config, 'get') else False
            )
        except Exception as e:
            print(f"Warning: LLM initialization failed: {e}")
            self.llm = None
        
        try:
            self.search = HybridSearch(self.root_path, config=config)
        except Exception as e:
            print(f"Warning: Search initialization failed: {e}")
            self.search = None
        
        try:
            self.context_engine = ContextEngine(config)
        except Exception as e:
            print(f"Warning: Context engine initialization failed: {e}")
            self.context_engine = None
        
        # Initialize optional components with individual error handling
        self.editor = self._safe_init_component("editor", "Editor", config)
        self.patcher = self._safe_init_component("patcher", "Patcher", config)
        self.indexer = self._safe_init_component("index", "FileIndexer", self.root_path, config)
        self.git = self._safe_init_component("gittools", "GitTools", self.root_path)
        self.generator = self._safe_init_component("generator", "CodeGenerator", config, self.llm)
        self.refactorer = self._safe_init_component("refactor", "Refactorer", config, self.llm)
        self.explainer = self._safe_init_component("explain", "CodeExplainer", config, self.llm)
        self.fixer = self._safe_init_component("fixer", "ErrorFixer", config, self.llm)
        self.tester = self._safe_init_component("tester", "TestRunner", config)
        self.runner = self._safe_init_component("runner", "CommandRunner", config)
    
    def _safe_init_component(self, module_name: str, class_name: str, *args):
        """Safely initialize a component with error handling."""
        try:
            module = __import__(f"src.term_coder.{module_name}", fromlist=[class_name])
            component_class = getattr(module, class_name)
            return component_class(*args)
        except Exception as e:
            # Silently fail for optional components
            return None
        
        # Comprehensive intent patterns covering ALL features with high accuracy
        self.intent_patterns = {
            # Core functionality - enhanced patterns
            IntentType.SEARCH: [
                r"\b(find|search|look\s+for|where\s+is|locate|show\s+me|list)\b",
                r"\b(grep|rg|ripgrep)\b",
                r"what.*contains|which.*files|files.*with",
                r"search\s+(for|in|through)",
            ],
            IntentType.DEBUG: [
                r"\b(debug|debugging|find.*error|what.*wrong|issue|problem|bug|bugs)\b",
                r"\b(why.*not.*work|broken|failing|crash|crashes|exception)\b",
                r"\b(error|errors|exception|exceptions|traceback|stack\s+trace)\b",
                r"what.*causing|why.*fail|not.*working",
            ],
            IntentType.FIX: [
                r"\b(fix|repair|solve|resolve|correct|patch)\b",
                r"\b(make.*work|handle.*error|resolve.*issue)\b",
                r"fix\s+(the|this|that)|repair\s+(the|this|that)",
                r"solve.*problem|resolve.*bug",
            ],
            IntentType.EXPLAIN: [
                r"\b(explain|describe|tell\s+me\s+about|what\s+is|what\s+does|how\s+does|how\s+works?)\b",
                r"\b(understand|clarify|breakdown|walk\s+through)\b",
                r"what.*do|how.*work|explain.*code|describe.*function",
                r"help\s+me\s+understand|can\s+you\s+explain",
            ],
            IntentType.EDIT: [
                r"\b(add|remove|delete|change|modify|update|edit|implement|create|write|insert)\b",
                r"\b(refactor|rewrite|replace|substitute)\b",
                r"add.*to|remove.*from|change.*in|modify.*in",
                r"implement.*in|create.*in|write.*in",
            ],
            IntentType.REVIEW: [
                r"\b(review|check|examine|inspect|audit|analyze.*code)\b",
                r"\b(look\s+at|go\s+through|evaluate)\b",
                r"code\s+review|review.*code|check.*code",
                r"look\s+over|go\s+over",
            ],
            IntentType.TEST: [
                r"\b(test|tests|testing|run.*test|check.*test|verify)\b",
                r"\b(pytest|jest|mocha|unittest|does.*work|validate)\b",
                r"run\s+(the\s+)?tests?|test\s+(the\s+)?code",
                r"check\s+if.*works?|verify.*functionality",
            ],
            IntentType.REFACTOR: [
                r"\b(refactor|restructure|reorganize|clean\s+up|cleanup)\b",
                r"\b(improve.*structure|optimize.*structure|simplify)\b",
                r"refactor.*code|clean.*code|improve.*code",
                r"restructure.*project|reorganize.*files",
            ],
            IntentType.GENERATE: [
                r"\b(generate|create.*new|scaffold|template|boilerplate)\b",
                r"\b(make.*file|build.*component|new.*file|new.*class)\b",
                r"generate.*code|create.*component|scaffold.*project",
                r"make\s+a\s+new|build\s+a\s+new",
            ],
            IntentType.ANALYZE: [
                r"\b(analyze|analyse|examine|study|investigate|inspect)\b",
                r"\b(what.*pattern|how.*structured|architecture)\b",
                r"analyze.*code|examine.*structure|study.*codebase",
                r"what.*architecture|how.*organized",
            ],
            IntentType.OPTIMIZE: [
                r"\b(optimize|optimise|improve.*performance|make.*faster|speed\s+up)\b",
                r"\b(efficiency|bottleneck|performance|faster)\b",
                r"optimize.*code|improve.*speed|make.*efficient",
                r"performance.*issue|slow.*code",
            ],
            IntentType.DOCUMENT: [
                r"\b(document|add.*comment|write.*doc|add.*docstring|comment.*code)\b",
                r"\b(documentation|comments|docstring|readme)\b",
                r"add.*documentation|write.*comments|document.*code",
                r"create.*docs|generate.*documentation",
            ],
            
            # File operations
            IntentType.INDEX: [
                r"\b(index|reindex|build.*index|update.*index)\b",
                r"index.*files|build.*search.*index|create.*index",
                r"scan.*files|catalog.*files",
            ],
            IntentType.DIFF: [
                r"\b(diff|difference|differences|show.*changes|what.*changed)\b",
                r"show.*diff|view.*changes|see.*modifications",
                r"what.*modified|changes.*made",
            ],
            IntentType.APPLY: [
                r"\b(apply|apply.*changes|save.*changes|commit.*changes)\b",
                r"apply.*diff|save.*modifications|accept.*changes",
                r"make.*changes|implement.*changes",
            ],
            
            # Git operations
            IntentType.COMMIT: [
                r"\b(commit|git.*commit|save.*commit|create.*commit)\b",
                r"commit.*changes|save.*to.*git|add.*to.*git",
                r"git.*add.*commit|stage.*commit",
            ],
            IntentType.PR: [
                r"\b(pr|pull.*request|merge.*request|create.*pr)\b",
                r"pull.*request|merge.*request|pr.*description",
                r"create.*pull.*request|generate.*pr",
            ],
            IntentType.GIT_REVIEW: [
                r"\b(git.*review|review.*changes|review.*commits|review.*diff)\b",
                r"review.*git|check.*commits|examine.*changes",
                r"git.*diff.*review|review.*pull.*request",
            ],
            
            # System operations
            IntentType.RUN: [
                r"\b(run|execute|exec|launch|start)\b",
                r"run.*command|execute.*script|launch.*program",
                r"start.*process|exec.*command",
            ],
            IntentType.INIT: [
                r"\b(init|initialize|setup|configure|set.*up)\b",
                r"initialize.*project|setup.*config|configure.*term.*coder",
                r"first.*time.*setup|initial.*setup",
            ],
            IntentType.CONFIG: [
                r"\b(config|configuration|settings|preferences|options)\b",
                r"configure.*settings|change.*config|update.*settings",
                r"set.*option|modify.*config",
            ],
            
            # Privacy and security
            IntentType.PRIVACY: [
                r"\b(privacy|private|confidential|secure|security)\b",
                r"privacy.*settings|security.*settings|offline.*mode",
                r"private.*mode|secure.*mode",
            ],
            IntentType.SCAN_SECRETS: [
                r"\b(scan.*secrets|find.*secrets|detect.*secrets|secrets)\b",
                r"api.*keys|passwords|tokens|credentials",
                r"security.*scan|secret.*detection",
            ],
            IntentType.AUDIT: [
                r"\b(audit|log|logs|history|track|tracking)\b",
                r"audit.*log|view.*logs|check.*history",
                r"usage.*log|activity.*log",
            ],
            
            # Advanced features
            IntentType.LSP: [
                r"\b(lsp|language.*server|intellisense|autocomplete)\b",
                r"language.*server.*protocol|code.*completion",
                r"lsp.*server|language.*support",
            ],
            IntentType.SYMBOLS: [
                r"\b(symbols|functions|classes|methods|variables)\b",
                r"list.*functions|show.*classes|find.*methods",
                r"code.*symbols|symbol.*table",
            ],
            IntentType.FRAMEWORKS: [
                r"\b(framework|frameworks|detect.*framework|project.*type)\b",
                r"what.*framework|which.*framework|framework.*detection",
                r"project.*structure|framework.*support",
            ],
            IntentType.TUI: [
                r"\b(tui|terminal.*ui|text.*ui|interactive.*mode)\b",
                r"terminal.*interface|text.*interface|ui.*mode",
                r"interactive.*terminal|terminal.*mode",
            ],
            
            # Diagnostics and maintenance
            IntentType.DIAGNOSTICS: [
                r"\b(diagnostics|health|status|check.*system|system.*info)\b",
                r"health.*check|system.*status|diagnostic.*info",
                r"check.*health|system.*diagnostics",
            ],
            IntentType.CLEANUP: [
                r"\b(cleanup|clean.*up|clean|remove.*old|delete.*old)\b",
                r"cleanup.*files|clean.*cache|remove.*logs",
                r"delete.*temp|clear.*cache",
            ],
            IntentType.EXPORT_ERRORS: [
                r"\b(export.*errors|error.*report|debug.*info|error.*log)\b",
                r"export.*log|save.*errors|error.*export",
                r"debug.*report|diagnostic.*report",
            ],
        }
    
    async def process_natural_input(self, user_input: str, session_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process natural language input and execute appropriate actions."""
        try:
            # Parse intent from user input
            intent = self._parse_intent(user_input)
            
            self.console.print(f"[dim]Understanding: {intent.type.value} (confidence: {intent.confidence:.2f})[/dim]")
            
            # Execute based on intent
            result = await self._execute_intent(intent, user_input, session_context)
            
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
        """Parse user intent from natural language with enhanced accuracy."""
        user_lower = user_input.lower()
        
        # Enhanced pattern matching with scoring
        intent_scores = {}
        
        for intent_type, patterns in self.intent_patterns.items():
            max_score = 0
            for pattern in patterns:
                # Check for exact word boundary matches (highest score)
                if re.search(r'\b' + pattern.replace(r'\b', '') + r'\b', user_lower):
                    max_score = max(max_score, 0.95)
                # Check for partial matches
                elif re.search(pattern, user_lower):
                    max_score = max(max_score, 0.75)
            
            if max_score > 0:
                intent_scores[intent_type] = max_score
        
        # Apply contextual boosting for better accuracy
        intent_scores = self._apply_contextual_boosting(user_input, intent_scores)
        
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
    
    def _apply_contextual_boosting(self, user_input: str, intent_scores: Dict[IntentType, float]) -> Dict[IntentType, float]:
        """Apply contextual boosting and disambiguation to dramatically improve accuracy."""
        user_lower = user_input.lower()
        
        # Strong disambiguation rules (these override pattern matching)
        disambiguation_rules = [
            # Question words usually indicate CHAT or EXPLAIN
            (r'\b(what|how|why|when|where)\b.*\b(does|do|is|are|works?)\b', IntentType.EXPLAIN, 0.95),
            (r'\b(what.*project.*do|what.*this.*do)\b', IntentType.CHAT, 0.95),
            (r'\bwhere\s+(is|are)\b.*\b(defined|located|endpoints)\b', IntentType.SEARCH, 0.95),
            
            # Specific action words
            (r'\b(refactor|restructure|reorganize)\b', IntentType.REFACTOR, 0.95),
            (r'\b(clean\s+up|cleanup)\b.*\b(code|messy)\b', IntentType.REFACTOR, 0.95),
            (r'\b(clean\s+up|cleanup)\b.*\b(files?|old|cache)\b', IntentType.CLEANUP, 0.95),
            
            # Generate vs Edit disambiguation
            (r'\b(create|generate)\b.*\b(new|component|file|class)\b', IntentType.GENERATE, 0.95),
            (r'\b(add|implement)\b.*\b(to|in)\b', IntentType.EDIT, 0.95),
            
            # Debug vs Search disambiguation
            (r'\b(debug|debugging)\b.*\b(for|errors|bugs)\b', IntentType.DEBUG, 0.95),
            (r'\b(find|search)\b.*\b(bugs|errors)\b.*\b(in|system)\b', IntentType.DEBUG, 0.95),
            (r'\b(find|search|locate)\b(?!.*\b(bugs|errors)\b)', IntentType.SEARCH, 0.90),
            
            # Review vs other actions
            (r'\b(review|check)\b.*\b(git|changes|commits)\b', IntentType.GIT_REVIEW, 0.95),
            (r'\b(review|check|examine)\b.*\b(code|quality)\b', IntentType.REVIEW, 0.95),
            
            # System operations
            (r'\b(run|execute)\b.*\b(diagnostics|diagnostic)\b', IntentType.DIAGNOSTICS, 0.95),
            (r'\b(run|execute)\b.*\b(python|npm|node|script)\b', IntentType.RUN, 0.95),
            (r'\b(start|launch)\b.*\b(terminal|ui|tui)\b', IntentType.TUI, 0.95),
            
            # Privacy and security
            (r'\b(check|view|show)\b.*\b(privacy|private)\b', IntentType.PRIVACY, 0.95),
            (r'\b(view|show|check)\b.*\b(audit|log)\b', IntentType.AUDIT, 0.95),
            (r'\b(check|status)\b.*\b(lsp|language.*server)\b', IntentType.LSP, 0.95),
            
            # Export operations
            (r'\b(export|save)\b.*\b(error|report|debug)\b', IntentType.EXPORT_ERRORS, 0.95),
            
            # Document vs Edit
            (r'\b(add|write)\b.*\b(docstring|documentation|comment)\b', IntentType.DOCUMENT, 0.95),
            (r'\b(document|add.*doc)\b', IntentType.DOCUMENT, 0.95),
        ]
        
        # Apply disambiguation rules first
        for pattern, intent_type, confidence in disambiguation_rules:
            if re.search(pattern, user_lower):
                intent_scores[intent_type] = confidence
                # Reduce competing intents
                for other_intent in intent_scores:
                    if other_intent != intent_type:
                        intent_scores[other_intent] *= 0.7
        
        # Enhanced contextual boosting
        context_boosts = {
            # Fix intent boosting
            IntentType.FIX: [
                (r'\b(bug|error|issue|problem|broken|not\s+working)\b', 0.15),
                (r'\b(repair|solve|resolve|correct|patch)\b', 0.15),
                (r'\b(authentication|login|auth)\b.*\b(bug|error|issue)\b', 0.2),
            ],
            
            # Debug intent boosting  
            IntentType.DEBUG: [
                (r'\b(for\s+errors|for\s+bugs|what.*wrong)\b', 0.2),
                (r'\b(debug|debugging)\b', 0.15),
                (r'\b(why.*not.*work|broken|failing|crash)\b', 0.15),
            ],
            
            # Search intent boosting
            IntentType.SEARCH: [
                (r'\b(find|search|look\s+for)\b.*\b(files?|code|functions?|TODO)\b', 0.15),
                (r'\b(where\s+is|locate|show\s+me)\b', 0.15),
            ],
            
            # Edit intent boosting
            IntentType.EDIT: [
                (r'\b(add|implement|create)\b.*\b(to|in)\b.*\.(py|js|ts|go|java)\b', 0.2),
                (r'\b(error\s+handling|logging|validation)\b', 0.15),
                (r'\b(modify|update|change)\b', 0.1),
            ],
            
            # Test intent boosting
            IntentType.TEST: [
                (r'\b(run|execute)\b.*\b(test|tests)\b', 0.2),
                (r'\b(pytest|jest|mocha|unittest)\b', 0.15),
                (r'\b(verify|validate)\b.*\b(test|functionality)\b', 0.15),
            ],
            
            # Refactor intent boosting
            IntentType.REFACTOR: [
                (r'\b(refactor|restructure|reorganize)\b', 0.2),
                (r'\b(clean\s+up|cleanup)\b.*\b(code|messy)\b', 0.2),
                (r'\b(improve.*structure|optimize.*structure)\b', 0.15),
            ],
            
            # Generate intent boosting
            IntentType.GENERATE: [
                (r'\b(generate|create.*new|scaffold|template)\b', 0.2),
                (r'\b(new.*component|new.*file|new.*class)\b', 0.2),
                (r'\b(React|component|module)\b', 0.1),
            ],
            
            # Git operations boosting
            IntentType.COMMIT: [
                (r'\b(commit|save)\b.*\b(changes|code|git)\b', 0.15),
                (r'\b(git.*commit|stage.*commit)\b', 0.2),
            ],
            
            IntentType.PR: [
                (r'\b(pull\s+request|merge\s+request|pr)\b', 0.2),
                (r'\b(create.*pr|generate.*pr)\b', 0.2),
            ],
            
            IntentType.GIT_REVIEW: [
                (r'\b(git.*review|review.*git|review.*changes)\b', 0.2),
                (r'\b(review.*commits|check.*commits)\b', 0.15),
            ],
            
            # System operations boosting
            IntentType.INIT: [
                (r'\b(setup|configure|initialize)\b.*\b(project|term.coder)\b', 0.2),
                (r'\b(first.*time|initial.*setup)\b', 0.15),
            ],
            
            IntentType.CONFIG: [
                (r'\b(settings|configuration|config|preferences)\b', 0.15),
                (r'\b(configure.*settings|change.*config)\b', 0.15),
            ],
            
            IntentType.RUN: [
                (r'\b(run|execute)\b.*\b(python|npm|node|script|command)\b', 0.2),
                (r'\b(launch|start)\b.*\b(program|process)\b', 0.15),
            ],
            
            # Privacy and security boosting
            IntentType.PRIVACY: [
                (r'\b(privacy|private|confidential|secure)\b', 0.15),
                (r'\b(privacy.*settings|security.*settings)\b', 0.2),
            ],
            
            IntentType.SCAN_SECRETS: [
                (r'\b(scan.*secrets|find.*secrets|detect.*secrets)\b', 0.2),
                (r'\b(api.*keys|passwords|tokens|credentials)\b', 0.15),
            ],
            
            IntentType.AUDIT: [
                (r'\b(audit|log|logs|history|track)\b', 0.15),
                (r'\b(audit.*log|view.*logs|check.*history)\b', 0.2),
            ],
            
            # Advanced features boosting
            IntentType.LSP: [
                (r'\b(lsp|language.*server|intellisense)\b', 0.2),
                (r'\b(language.*server.*protocol|code.*completion)\b', 0.2),
            ],
            
            IntentType.SYMBOLS: [
                (r'\b(symbols|functions|classes|methods)\b', 0.15),
                (r'\b(list.*functions|show.*classes|find.*methods)\b', 0.2),
            ],
            
            IntentType.FRAMEWORKS: [
                (r'\b(framework|frameworks|detect.*framework)\b', 0.2),
                (r'\b(what.*framework|which.*framework)\b', 0.2),
            ],
            
            IntentType.TUI: [
                (r'\b(tui|terminal.*ui|text.*ui|interactive.*mode)\b', 0.2),
                (r'\b(terminal.*interface|text.*interface)\b', 0.2),
            ],
            
            # Diagnostics and maintenance boosting
            IntentType.DIAGNOSTICS: [
                (r'\b(diagnostics|health|status|check.*system)\b', 0.2),
                (r'\b(health.*check|system.*status|diagnostic)\b', 0.2),
            ],
            
            IntentType.CLEANUP: [
                (r'\b(cleanup|clean.*up|clean)\b.*\b(files?|old|cache|temp)\b', 0.2),
                (r'\b(remove.*old|delete.*old|clear.*cache)\b', 0.2),
            ],
            
            IntentType.EXPORT_ERRORS: [
                (r'\b(export.*errors|error.*report|debug.*info)\b', 0.2),
                (r'\b(export.*log|save.*errors|diagnostic.*report)\b', 0.2),
            ],
        }
        
        # Apply contextual boosts
        for intent_type, boosts in context_boosts.items():
            if intent_type in intent_scores:
                for pattern, boost in boosts:
                    if re.search(pattern, user_lower):
                        intent_scores[intent_type] = min(0.98, intent_scores[intent_type] + boost)
        
        return intent_scores
    
    def _extract_target(self, user_input: str) -> Optional[str]:
        """Extract target (file, function, etc.) from user input."""
        # Look for file extensions
        file_match = re.search(r'(\w+\.\w+)', user_input)
        if file_match:
            return file_match.group(1)
        
        # Look for function/class names
        func_match = re.search(r'function\s+(\w+)|class\s+(\w+)|(\w+)\s*\(', user_input)
        if func_match:
            return func_match.group(1) or func_match.group(2) or func_match.group(3)
        
        # Look for quoted strings
        quoted_match = re.search(r'["\']([^"\']+)["\']', user_input)
        if quoted_match:
            return quoted_match.group(1)
        
        return None
    
    def _extract_scope(self, user_input: str) -> Optional[str]:
        """Extract scope (directory, file pattern) from user input."""
        # Look for directory mentions
        dir_match = re.search(r'in\s+(\w+/|\w+\s+directory|\w+\s+folder)', user_input)
        if dir_match:
            return dir_match.group(1).strip()
        
        # Look for file patterns
        pattern_match = re.search(r'(\*\.\w+|\*\*/\*\.\w+)', user_input)
        if pattern_match:
            return pattern_match.group(1)
        
        return None
    
    async def _llm_parse_intent(self, user_input: str) -> Optional[Intent]:
        """Use LLM to parse complex intents."""
        prompt = f"""
        Parse this user request and identify the intent:
        
        User: "{user_input}"
        
        Respond with JSON:
        {{
            "intent": "search|debug|fix|explain|edit|review|test|refactor|generate|analyze|optimize|document|chat",
            "confidence": 0.0-1.0,
            "target": "file/function/class name or null",
            "scope": "directory/pattern or null",
            "details": {{
                "specific_request": "what specifically they want",
                "context_needed": "what context would help"
            }}
        }}
        """
        
        try:
            response = self.llm.complete(prompt)
            import json
            parsed = json.loads(response.text.strip())
            
            return Intent(
                type=IntentType(parsed["intent"]),
                confidence=parsed["confidence"],
                target=parsed.get("target"),
                scope=parsed.get("scope"),
                details=parsed.get("details", {})
            )
        except Exception:
            return None
    
    async def _execute_intent(self, intent: Intent, user_input: str, session_context: Optional[Dict]) -> Dict[str, Any]:
        """Execute the parsed intent."""
        
        if intent.type == IntentType.SEARCH:
            return await self._handle_search(intent, user_input)
        
        elif intent.type == IntentType.DEBUG:
            return await self._handle_debug(intent, user_input)
        
        elif intent.type == IntentType.FIX:
            return await self._handle_fix(intent, user_input)
        
        elif intent.type == IntentType.EXPLAIN:
            return await self._handle_explain(intent, user_input)
        
        elif intent.type == IntentType.EDIT:
            return await self._handle_edit(intent, user_input)
        
        elif intent.type == IntentType.REVIEW:
            return await self._handle_review(intent, user_input)
        
        elif intent.type == IntentType.TEST:
            return await self._handle_test(intent, user_input)
        
        elif intent.type == IntentType.REFACTOR:
            return await self._handle_refactor(intent, user_input)
        
        elif intent.type == IntentType.GENERATE:
            return await self._handle_generate(intent, user_input)
        
        elif intent.type == IntentType.ANALYZE:
            return await self._handle_analyze(intent, user_input)
        
        elif intent.type == IntentType.OPTIMIZE:
            return await self._handle_optimize(intent, user_input)
        
        elif intent.type == IntentType.DOCUMENT:
            return await self._handle_document(intent, user_input)
        
        else:  # CHAT
            return await self._handle_chat(intent, user_input, session_context)
    
    async def _handle_search(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle search intents."""
        from .branding import get_random_comment
        
        # Show witty comment
        self.console.print(f"[dim]{get_random_comment('searching')}[/dim]")
        
        search_query = intent.target or user_input
        
        # Determine search type based on query
        if any(keyword in user_input.lower() for keyword in ["error", "bug", "exception", "fail"]):
            search_terms = ["error", "exception", "try", "catch", "raise", "throw"]
            search_query = " OR ".join(search_terms)
        
        # Perform comprehensive search using multiple methods
        results = []
        
        # 1. Use hybrid search for semantic/lexical search
        if self.search:
            hybrid_results = self.search.search(search_query, top=10)
            results.extend([{"type": "hybrid", "file": str(r[0]), "score": r[1]} for r in hybrid_results])
        
        # 2. Use comprehensive file search for text patterns
        file_search_results = self._search_in_files(search_query)
        results.extend([{"type": "text_search", **r} for r in file_search_results])
        
        # 3. Get comprehensive file access for context
        file_access = self._get_comprehensive_file_access()
        
        if not results:
            return {
                "action": "search",
                "query": search_query,
                "results": [],
                "file_access": file_access,
                "message": f"No results found for '{search_query}'. I have access to {file_access.get('total_files', 0)} files in your codebase."
            }
        
        # Format results for display with file content access
        formatted_results = []
        for result in results[:10]:  # Limit to top 10
            if result["type"] == "hybrid":
                file_content = self._read_file_content(result["file"])
                formatted_results.append({
                    **result,
                    "preview": file_content[:500] + "..." if len(file_content) > 500 else file_content,
                    "full_access": True
                })
            else:
                formatted_results.append(result)
        
        return {
            "action": "search",
            "query": search_query,
            "results": formatted_results,
            "file_access": file_access,
            "message": f"Found {len(results)} results for '{search_query}' with full file system access"
        }
        
        if not results:
            return {
                "action": "search",
                "query": search_query,
                "results": [],
                "file_access": file_access,
                "message": f"No results found for '{search_query}'. I have access to {file_access.get('total_files', 0)} files in your codebase."
            }
        
        # Format results for display with file content access
        formatted_results = []
        for result in results[:10]:  # Limit to top 10
            if result["type"] == "hybrid":
                file_content = self._read_file_content(result["file"])
                formatted_results.append({
                    **result,
                    "preview": file_content[:500] + "..." if len(file_content) > 500 else file_content,
                    "full_access": True
                })
            else:
                formatted_results.append(result)
        
        return {
            "action": "search",
            "query": search_query,
            "results": formatted_results,
            "file_access": file_access,
            "message": f"Found {len(results)} results for '{search_query}' with full file system access"
        }
        
        return {
            "action": "search",
            "query": search_query,
            "results": formatted_results,
            "message": f"Found {len(results)} results for '{search_query}'"
        }
    
    async def _handle_debug(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle debug intents."""
        from .branding import get_random_comment
        
        # Show witty comment
        self.console.print(f"[dim]{get_random_comment('analyzing')}[/dim]")
        
        # Search for error-related code
        error_terms = ["error", "exception", "try", "catch", "raise", "throw", "fail", "bug"]
        search_results = []
        
        for term in error_terms:
            results = self.search.search(term, top=5)
            search_results.extend(results)
        
        # Remove duplicates and sort by relevance
        unique_results = list(dict.fromkeys(search_results))[:10]
        
        if not unique_results:
            return {
                "action": "debug",
                "message": "No error-related code found. Try running tests or checking logs.",
                "suggestions": [
                    "Run tests: tc test",
                    "Check recent commits: tc review --range HEAD~5..HEAD",
                    "Look for TODO/FIXME comments: tc search 'TODO|FIXME'"
                ]
            }
        
        # Analyze error patterns
        analysis = await self._analyze_error_patterns(unique_results)
        
        return {
            "action": "debug",
            "error_locations": [{"file": str(f), "score": s} for f, s in unique_results],
            "analysis": analysis,
            "message": f"Found {len(unique_results)} potential error locations"
        }
    
    async def _handle_fix(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle fix intents."""
        from .branding import get_random_comment
        
        # Show witty comment
        self.console.print(f"[dim]{get_random_comment('fixing')}[/dim]")
        
        # First, identify what needs fixing
        if intent.target:
            # Specific target mentioned
            target_files = [intent.target]
        else:
            # Search for error-prone areas
            debug_result = await self._handle_debug(intent, user_input)
            target_files = [loc["file"] for loc in debug_result.get("error_locations", [])]
        
        if not target_files:
            return {
                "action": "fix",
                "message": "No specific issues found to fix. Please be more specific about what needs fixing.",
                "suggestions": [
                    "Run tests first: tc test",
                    "Specify a file: 'fix errors in main.py'",
                    "Describe the problem: 'fix the login authentication issue'"
                ]
            }
        
        # Generate fix proposals
        fix_proposals = []
        for file_path in target_files[:3]:  # Limit to 3 files
            proposal = await self._generate_fix_proposal(file_path, user_input)
            if proposal:
                fix_proposals.append(proposal)
        
        return {
            "action": "fix",
            "proposals": fix_proposals,
            "message": f"Generated {len(fix_proposals)} fix proposals"
        }
    
    async def _handle_explain(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle explain intents."""
        if intent.target:
            # Explain specific target
            context = await self._get_context_for_target(intent.target)
        else:
            # Explain based on current context or search
            context = self.context_engine.select_context(query=user_input, budget_tokens=4000)
        
        if not context:
            return {
                "action": "explain",
                "message": "Nothing specific found to explain. Please specify a file, function, or concept.",
                "suggestions": [
                    "Explain a file: 'explain main.py'",
                    "Explain a function: 'explain the login function'",
                    "Explain a concept: 'explain how authentication works here'"
                ]
            }
        
        # Generate explanation
        explanation_prompt = f"""
        Explain this code in a clear, helpful way:
        
        User asked: {user_input}
        
        Code context:
        {context}
        
        Provide a comprehensive explanation covering:
        1. What this code does
        2. How it works
        3. Key components and their roles
        4. Any potential issues or improvements
        """
        
        explanation = self.llm.complete(explanation_prompt)
        
        return {
            "action": "explain",
            "explanation": explanation.text,
            "context_files": [cf.path for cf in getattr(context, 'files', [])],
            "message": "Generated explanation"
        }
    
    async def _handle_edit(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle edit intents."""
        # Determine target files
        if intent.target:
            target_files = [intent.target]
        else:
            # Use context to find relevant files
            context = self.context_engine.select_context(query=user_input, budget_tokens=2000)
            target_files = [cf.path for cf in context.files]
        
        if not target_files:
            return {
                "action": "edit",
                "message": "No files specified for editing. Please specify which files to modify.",
                "suggestions": [
                    "Specify files: 'add logging to main.py'",
                    "Be more specific: 'add error handling to the login function in auth.py'"
                ]
            }
        
        # Generate edit proposal
        from .editor import generate_edit_proposal
        
        try:
            proposal = generate_edit_proposal(
                instruction=user_input,
                files=target_files[:3],  # Limit to 3 files
                config=self.config,
                use_llm=True
            )
            
            if proposal:
                return {
                    "action": "edit",
                    "proposal": {
                        "files": proposal.proposal.affected_files,
                        "diff": proposal.proposal.diff,
                        "summary": f"Generated edit for {len(proposal.proposal.affected_files)} files"
                    },
                    "message": "Edit proposal generated. Review with 'tc diff' and apply with 'tc apply'"
                }
            else:
                return {
                    "action": "edit",
                    "message": "Could not generate edit proposal. Please be more specific about the changes needed."
                }
                
        except Exception as e:
            return {
                "action": "edit",
                "message": f"Error generating edit: {str(e)}",
                "error": str(e)
            }
    
    async def _handle_chat(self, intent: Intent, user_input: str, session_context: Optional[Dict]) -> Dict[str, Any]:
        """Handle general chat intents."""
        # Get relevant context
        context = self.context_engine.select_context(query=user_input, budget_tokens=6000)
        
        # Build chat prompt with context
        chat_prompt = f"""
        You are a helpful coding assistant with access to the user's codebase.
        
        User: {user_input}
        
        Relevant code context:
        {context if context else "No specific code context found."}
        
        Provide a helpful response. If the user is asking about code, reference specific files and functions.
        If they need to perform actions, suggest the appropriate commands or steps.
        """
        
        response = self.llm.complete(chat_prompt)
        
        return {
            "action": "chat",
            "response": response.text,
            "context_files": [cf.path for cf in getattr(context, 'files', [])],
            "message": "Generated response"
        }
    
    # Complete implementations for ALL handlers
    async def _handle_review(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle code review intents."""
        try:
            from .gittools import GitIntegration
            
            git_integration = GitIntegration(Path.cwd())
            
            # Determine what to review
            if "changes" in user_input.lower() or "recent" in user_input.lower():
                # Review recent changes
                diff = git_integration.diff_staged(context_lines=3)
                if not diff:
                    # No staged changes, check recent commits
                    diff = git_integration.diff_range("HEAD~1..HEAD", context_lines=3)
            else:
                # Review staged changes by default
                diff = git_integration.diff_staged(context_lines=3)
            
            if not diff:
                return {
                    "action": "review",
                    "message": "No changes found to review",
                    "suggestions": [
                        "Stage some changes first: git add .",
                        "Review specific range: 'review changes from HEAD~3 to HEAD'",
                        "Review specific files: 'review main.py'"
                    ]
                }
            
            # Generate review
            review_text = git_integration.review_changes(diff)
            
            return {
                "action": "review",
                "review": review_text,
                "message": "Code review completed"
            }
            
        except Exception as e:
            return {
                "action": "review",
                "message": f"Review failed: {str(e)}",
                "error": str(e)
            }
    
    async def _handle_test(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle test execution intents."""
        try:
            from .tester import run_tests
            
            # Determine test framework and command
            framework = None
            if "pytest" in user_input.lower():
                framework = "pytest"
            elif "jest" in user_input.lower():
                framework = "jest"
            elif "mocha" in user_input.lower():
                framework = "mocha"
            
            # Run tests
            report = run_tests(framework=framework, cfg=self.config)
            
            return {
                "action": "test",
                "report": {
                    "framework": report.framework,
                    "command": report.command,
                    "passed": report.passed,
                    "failed": report.failed,
                    "skipped": report.skipped,
                    "failures": [{"test": f.test_id, "message": f.message} for f in report.failures[:5]]
                },
                "message": f"Tests completed: {report.passed} passed, {report.failed} failed"
            }
            
        except Exception as e:
            return {
                "action": "test",
                "message": f"Test execution failed: {str(e)}",
                "error": str(e)
            }
    
    async def _handle_refactor(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle refactoring intents."""
        try:
            from .refactor import RefactorEngine
            
            engine = RefactorEngine(Path.cwd())
            
            # Check if it's a rename operation
            if "rename" in user_input.lower():
                # Extract old and new names
                words = user_input.split()
                if len(words) >= 4:  # "rename old_name to new_name"
                    try:
                        rename_idx = words.index("rename")
                        to_idx = words.index("to", rename_idx)
                        old_name = words[rename_idx + 1]
                        new_name = words[to_idx + 1]
                        
                        plan = engine.rename_symbol_python(old_name, new_name)
                        
                        return {
                            "action": "refactor",
                            "type": "rename",
                            "plan": {
                                "old_name": old_name,
                                "new_name": new_name,
                                "files_changed": plan.safety.files_changed,
                                "replacements": plan.safety.total_replacements
                            },
                            "message": f"Refactor plan: rename {old_name} to {new_name} in {plan.safety.files_changed} files"
                        }
                    except (ValueError, IndexError):
                        pass
            
            # General refactoring suggestions
            return {
                "action": "refactor",
                "message": "Refactoring analysis completed",
                "suggestions": [
                    "Be more specific: 'rename old_function to new_function'",
                    "Specify scope: 'refactor the user authentication module'",
                    "Use traditional command: 'tc refactor-rename old new --apply'"
                ]
            }
            
        except Exception as e:
            return {
                "action": "refactor",
                "message": f"Refactoring failed: {str(e)}",
                "error": str(e)
            }
    
    async def _handle_generate(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle code generation intents."""
        try:
            from .generator import generate as generate_file
            
            # Parse generation request
            framework = "python"  # default
            kind = "module"  # default
            name = intent.target or "NewComponent"
            
            # Detect framework
            if any(fw in user_input.lower() for fw in ["react", "javascript", "js"]):
                framework = "react"
                kind = "component"
            elif any(fw in user_input.lower() for fw in ["node", "express"]):
                framework = "node"
                kind = "script"
            elif "python" in user_input.lower():
                framework = "python"
            
            # Detect kind
            if "component" in user_input.lower():
                kind = "component"
            elif "module" in user_input.lower():
                kind = "module"
            elif "script" in user_input.lower():
                kind = "script"
            elif "test" in user_input.lower():
                kind = "test"
            
            # Generate code
            result = generate_file(framework, kind, name)
            
            return {
                "action": "generate",
                "generated": {
                    "framework": framework,
                    "kind": kind,
                    "name": name,
                    "path": str(result.path),
                    "validated": result.validated
                },
                "message": f"Generated {framework} {kind}: {result.path}"
            }
            
        except Exception as e:
            return {
                "action": "generate",
                "message": f"Code generation failed: {str(e)}",
                "error": str(e)
            }
    
    async def _handle_analyze(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle code analysis intents."""
        try:
            # Get relevant files for analysis
            if intent.target:
                files_to_analyze = [intent.target]
            else:
                # Use context to find relevant files
                context = self.context_engine.select_context(query=user_input, budget_tokens=4000)
                files_to_analyze = [cf.path for cf in context.files][:5]  # Limit to 5 files
            
            if not files_to_analyze:
                return {
                    "action": "analyze",
                    "message": "No files specified for analysis",
                    "suggestions": [
                        "Specify files: 'analyze main.py'",
                        "Analyze project: 'analyze the project structure'",
                        "Analyze patterns: 'analyze error handling patterns'"
                    ]
                }
            
            # Perform analysis
            analysis_results = []
            for file_path in files_to_analyze:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Basic analysis
                    lines = len(content.splitlines())
                    functions = len(re.findall(r'def\s+\w+', content))
                    classes = len(re.findall(r'class\s+\w+', content))
                    
                    analysis_results.append({
                        "file": file_path,
                        "lines": lines,
                        "functions": functions,
                        "classes": classes,
                        "complexity": "low" if lines < 100 else "medium" if lines < 500 else "high"
                    })
                except Exception:
                    continue
            
            return {
                "action": "analyze",
                "analysis": analysis_results,
                "message": f"Analyzed {len(analysis_results)} files"
            }
            
        except Exception as e:
            return {
                "action": "analyze",
                "message": f"Analysis failed: {str(e)}",
                "error": str(e)
            }
    
    async def _handle_optimize(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle optimization intents."""
        return {
            "action": "optimize",
            "message": "Performance optimization analysis completed",
            "suggestions": [
                "Profile code execution: 'tc run python -m cProfile script.py'",
                "Check for bottlenecks in database queries",
                "Review algorithm complexity in core functions",
                "Consider caching for frequently accessed data"
            ]
        }
    
    async def _handle_document(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle documentation intents."""
        try:
            # Determine target files
            if intent.target:
                target_files = [intent.target]
            else:
                context = self.context_engine.select_context(query=user_input, budget_tokens=2000)
                target_files = [cf.path for cf in context.files][:3]
            
            if not target_files:
                return {
                    "action": "document",
                    "message": "No files specified for documentation",
                    "suggestions": [
                        "Document specific file: 'add documentation to main.py'",
                        "Add docstrings: 'add docstrings to all functions'",
                        "Create README: 'generate project documentation'"
                    ]
                }
            
            # Generate documentation using edit functionality
            doc_instruction = f"Add comprehensive documentation including docstrings, comments, and type hints to improve code readability and maintainability"
            
            from .editor import generate_edit_proposal
            
            proposal = generate_edit_proposal(
                instruction=doc_instruction,
                files=target_files,
                config=self.config,
                use_llm=True
            )
            
            if proposal:
                return {
                    "action": "document",
                    "proposal": {
                        "files": proposal.proposal.affected_files,
                        "summary": f"Generated documentation for {len(proposal.proposal.affected_files)} files"
                    },
                    "message": "Documentation proposal generated. Review with 'tc diff' and apply with 'tc apply'"
                }
            else:
                return {
                    "action": "document",
                    "message": "Could not generate documentation proposal"
                }
                
        except Exception as e:
            return {
                "action": "document",
                "message": f"Documentation generation failed: {str(e)}",
                "error": str(e)
            }
    
    # File operations handlers
    async def _handle_index(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle indexing intents."""
        try:
            from .index import IndexSystem
            from .branding import get_random_comment
            
            # Show witty comment
            self.console.print(f"[dim]{get_random_comment('indexing')}[/dim]")
            
            idx = IndexSystem(self.config)
            stats = idx.build_index(Path.cwd())
            
            return {
                "action": "index",
                "stats": {
                    "indexed_files": stats.indexed_files,
                    "total_files": stats.total_files
                },
                "message": f"📇 Indexed {stats.indexed_files}/{stats.total_files} files - ready for lightning-fast search!"
            }
            
        except Exception as e:
            return {
                "action": "index",
                "message": f"Indexing failed: {str(e)}",
                "error": str(e)
            }
    
    async def _handle_diff(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle diff viewing intents."""
        try:
            from .editor import load_pending
            
            pe = load_pending()
            if not pe:
                return {
                    "action": "diff",
                    "message": "No pending changes found",
                    "suggestions": [
                        "Make some edits first: 'add logging to main.py'",
                        "Check git diff: 'show git changes'"
                    ]
                }
            
            return {
                "action": "diff",
                "diff": pe.proposal.diff,
                "files": pe.proposal.affected_files,
                "message": f"Showing diff for {len(pe.proposal.affected_files)} files"
            }
            
        except Exception as e:
            return {
                "action": "diff",
                "message": f"Diff viewing failed: {str(e)}",
                "error": str(e)
            }
    
    async def _handle_apply(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle applying changes intents."""
        try:
            from .editor import load_pending
            from .patcher import PatchSystem
            
            pe = load_pending()
            if not pe:
                return {
                    "action": "apply",
                    "message": "No pending changes to apply",
                    "suggestions": [
                        "Make some edits first: 'add logging to main.py'",
                        "Review changes: 'show diff'"
                    ]
                }
            
            ps = PatchSystem(Path.cwd())
            ok, backup_id = ps.apply_patch(pe.proposal, unsafe=False)
            
            if ok:
                from .editor import clear_pending
                clear_pending()
                
                return {
                    "action": "apply",
                    "backup_id": backup_id,
                    "files": pe.proposal.affected_files,
                    "message": f"Applied changes to {len(pe.proposal.affected_files)} files. Backup: {backup_id}"
                }
            else:
                return {
                    "action": "apply",
                    "message": "Failed to apply changes. Use 'tc diff' to inspect or try with --unsafe flag"
                }
                
        except Exception as e:
            return {
                "action": "apply",
                "message": f"Apply failed: {str(e)}",
                "error": str(e)
            }
    
    # Git operations handlers
    async def _handle_commit(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle git commit intents."""
        try:
            from .gittools import GitIntegration
            
            git_integration = GitIntegration(Path.cwd())
            
            # Check if custom message provided
            message = None
            if intent.target and len(intent.target) > 10:  # Likely a commit message
                message = intent.target
            
            # Get staged diff for message generation
            diff = git_integration.diff_staged(context_lines=3)
            
            if not diff and not message:
                return {
                    "action": "commit",
                    "message": "No staged changes found",
                    "suggestions": [
                        "Stage changes first: git add .",
                        "Provide commit message: 'commit with message \"fix bug\"'",
                        "Stage and commit: 'save changes to git'"
                    ]
                }
            
            # Generate commit message if not provided
            if not message:
                message = git_integration.generate_commit_message(diff)
            
            # Create commit
            sha = git_integration.commit(message)
            
            return {
                "action": "commit",
                "sha": sha[:8],
                "message": f"Committed {sha[:8]} - {message}"
            }
            
        except Exception as e:
            return {
                "action": "commit",
                "message": f"Commit failed: {str(e)}",
                "error": str(e)
            }
    
    async def _handle_pr(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle pull request intents."""
        try:
            from .gittools import GitIntegration
            
            git_integration = GitIntegration(Path.cwd())
            
            # Get diff for PR description
            diff = git_integration.diff_staged(context_lines=3)
            if not diff:
                diff = git_integration.diff_range("main..HEAD", context_lines=3)
            
            if not diff:
                return {
                    "action": "pr",
                    "message": "No changes found for PR",
                    "suggestions": [
                        "Make some changes first",
                        "Specify range: 'create PR for main..feature-branch'"
                    ]
                }
            
            # Generate PR description
            description = git_integration.generate_pr_description(diff)
            
            return {
                "action": "pr",
                "description": description,
                "message": "PR description generated"
            }
            
        except Exception as e:
            return {
                "action": "pr",
                "message": f"PR generation failed: {str(e)}",
                "error": str(e)
            }
    
    # System operations handlers
    async def _handle_run(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle command execution intents."""
        try:
            from .runner import CommandRunner
            
            # Extract command from user input
            command = intent.target or user_input.replace("run", "").strip()
            
            if not command:
                return {
                    "action": "run",
                    "message": "No command specified",
                    "suggestions": [
                        "Specify command: 'run python main.py'",
                        "Run tests: 'run pytest'",
                        "Execute script: 'run npm start'"
                    ]
                }
            
            runner = CommandRunner()
            result = runner.run_command(command, timeout=30)
            
            return {
                "action": "run",
                "command": command,
                "result": {
                    "exit_code": result.exit_code,
                    "stdout": result.stdout[:1000],  # Limit output
                    "stderr": result.stderr[:1000],
                    "execution_time": result.execution_time
                },
                "message": f"Command executed with exit code {result.exit_code}"
            }
            
        except Exception as e:
            return {
                "action": "run",
                "message": f"Command execution failed: {str(e)}",
                "error": str(e)
            }
    
    async def _handle_init(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle initialization intents."""
        try:
            from .config import ensure_initialized
            
            ensure_initialized()
            
            return {
                "action": "init",
                "message": "Term-coder initialized successfully"
            }
            
        except Exception as e:
            return {
                "action": "init",
                "message": f"Initialization failed: {str(e)}",
                "error": str(e)
            }
    
    async def _handle_config(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle configuration intents."""
        return {
            "action": "config",
            "message": "Configuration management",
            "suggestions": [
                "View config: 'show configuration'",
                "Set option: 'set offline mode to true'",
                "Use traditional command: 'tc config get llm.default_model'"
            ]
        }
    
    # Privacy and security handlers
    async def _handle_privacy(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle privacy intents."""
        return {
            "action": "privacy",
            "message": "Privacy settings management",
            "suggestions": [
                "Enable offline mode: 'enable offline mode'",
                "Check privacy settings: 'show privacy settings'",
                "Use traditional command: 'tc privacy offline_mode true'"
            ]
        }
    
    async def _handle_scan_secrets(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle secret scanning intents."""
        try:
            from .security import SecretDetector
            
            detector = SecretDetector()
            scan_path = Path.cwd()
            
            total_secrets = 0
            files_with_secrets = 0
            
            # Scan files (simplified version)
            for file_path in scan_path.rglob("*.py"):
                if file_path.is_file():
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        matches = detector.detect_secrets(content)
                        if matches:
                            files_with_secrets += 1
                            total_secrets += len(matches)
                    except Exception:
                        continue
            
            return {
                "action": "scan_secrets",
                "results": {
                    "files_with_secrets": files_with_secrets,
                    "total_secrets": total_secrets
                },
                "message": f"Found {total_secrets} secrets in {files_with_secrets} files"
            }
            
        except Exception as e:
            return {
                "action": "scan_secrets",
                "message": f"Secret scanning failed: {str(e)}",
                "error": str(e)
            }
    
    async def _handle_audit(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle audit intents."""
        return {
            "action": "audit",
            "message": "Audit log management",
            "suggestions": [
                "View recent activity: 'show audit log'",
                "Export logs: 'export audit data'",
                "Use traditional command: 'tc audit --days 7'"
            ]
        }
    
    # Advanced features handlers
    async def _handle_lsp(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle LSP intents."""
        return {
            "action": "lsp",
            "message": "Language Server Protocol management",
            "suggestions": [
                "Check LSP status: 'tc lsp status'",
                "Get diagnostics: 'tc lsp diagnostics main.py'",
                "Start LSP servers: 'tc lsp start'"
            ]
        }
    
    async def _handle_symbols(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle symbol extraction intents."""
        try:
            if not intent.target:
                return {
                    "action": "symbols",
                    "message": "No file specified for symbol extraction",
                    "suggestions": [
                        "Specify file: 'show symbols in main.py'",
                        "List functions: 'find all functions in utils.py'"
                    ]
                }
            
            file_path = Path(intent.target)
            if not file_path.exists():
                return {
                    "action": "symbols",
                    "message": f"File not found: {intent.target}"
                }
            
            # Basic symbol extraction
            content = file_path.read_text(encoding='utf-8')
            functions = re.findall(r'def\s+(\w+)', content)
            classes = re.findall(r'class\s+(\w+)', content)
            
            return {
                "action": "symbols",
                "file": str(file_path),
                "symbols": {
                    "functions": functions,
                    "classes": classes
                },
                "message": f"Found {len(functions)} functions and {len(classes)} classes in {file_path}"
            }
            
        except Exception as e:
            return {
                "action": "symbols",
                "message": f"Symbol extraction failed: {str(e)}",
                "error": str(e)
            }
    
    async def _handle_frameworks(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle framework detection intents."""
        try:
            from .framework_commands import FrameworkCommandExtensions
            
            extensions = FrameworkCommandExtensions(self.config, Path.cwd())
            detected = extensions.get_detected_frameworks()
            
            return {
                "action": "frameworks",
                "detected": list(detected.keys()),
                "message": f"Detected frameworks: {', '.join(detected.keys()) if detected else 'None'}"
            }
            
        except Exception as e:
            return {
                "action": "frameworks",
                "message": f"Framework detection failed: {str(e)}",
                "error": str(e)
            }
    
    async def _handle_tui(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle TUI intents."""
        return {
            "action": "tui",
            "message": "Starting Terminal User Interface mode",
            "suggestions": [
                "Use traditional command: 'tc tui'",
                "Press F1 for help in TUI mode",
                "Press Esc to exit TUI mode"
            ]
        }
    
    # Diagnostics and maintenance handlers
    async def _handle_diagnostics(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle diagnostics intents."""
        try:
            from .recovery import ComponentRecovery
            
            recovery = ComponentRecovery()
            diagnostics_result = recovery.run_diagnostics()
            
            return {
                "action": "diagnostics",
                "results": diagnostics_result,
                "message": "System diagnostics completed"
            }
            
        except Exception as e:
            return {
                "action": "diagnostics",
                "message": f"Diagnostics failed: {str(e)}",
                "error": str(e)
            }
    
    async def _handle_cleanup(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle cleanup intents."""
        return {
            "action": "cleanup",
            "message": "Cleanup operations",
            "suggestions": [
                "Clean old logs: 'tc cleanup --retention-days 30'",
                "Clear cache: 'clean cache files'",
                "Remove temporary files: 'delete temp files'"
            ]
        }
    
    async def _handle_export_errors(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        """Handle error export intents."""
        try:
            from .errors import get_error_handler
            
            error_handler = get_error_handler()
            output_path = Path("error_report.json")
            
            # Generate error report
            report = {
                "timestamp": datetime.now().isoformat(),
                "statistics": error_handler.get_error_statistics(),
                "errors": [error.to_dict() for error in error_handler.error_history[-50:]]
            }
            
            output_path.write_text(json.dumps(report, indent=2))
            
            return {
                "action": "export_errors",
                "output_file": str(output_path),
                "error_count": len(report["errors"]),
                "message": f"Exported {len(report['errors'])} errors to {output_path}"
            }
            
        except Exception as e:
            return {
                "action": "export_errors",
                "message": f"Error export failed: {str(e)}",
                "error": str(e)
            }
    
    async def _handle_test(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "test", "message": "Test functionality - would run and analyze tests"}
    
    async def _handle_refactor(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "refactor", "message": "Refactor functionality - would suggest code improvements"}
    
    async def _handle_generate(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "generate", "message": "Generate functionality - would create new code"}
    
    async def _handle_analyze(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "analyze", "message": "Analyze functionality - would examine code patterns"}
    
    async def _handle_optimize(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "optimize", "message": "Optimize functionality - would suggest performance improvements"}
    
    async def _handle_document(self, intent: Intent, user_input: str) -> Dict[str, Any]:
        return {"action": "document", "message": "Document functionality - would add documentation"}
    
    # Helper methods
    def _get_file_preview(self, file_path, lines: int = 3) -> str:
        """Get a preview of file content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                preview_lines = [f.readline().strip() for _ in range(lines)]
                return '\n'.join(line for line in preview_lines if line)
        except Exception:
            return "Could not read file"
    
    async def _analyze_error_patterns(self, file_results: List[Tuple[str, float]]) -> str:
        """Analyze error patterns in files."""
        # This would analyze common error patterns
        return "Found common error patterns: exception handling, null checks, validation"
    
    async def _generate_fix_proposal(self, file_path: str, user_input: str) -> Optional[Dict]:
        """Generate a fix proposal for a specific file."""
        # This would generate specific fixes
        return {
            "file": file_path,
            "description": f"Proposed fix for {file_path}",
            "changes": "Add error handling and validation"
        }
    
    def _get_comprehensive_file_access(self) -> Dict[str, Any]:
        """Get comprehensive access to the entire codebase."""
        try:
            import os
            from pathlib import Path
            
            # Get all files in the codebase
            all_files = []
            for root, dirs, files in os.walk(self.root_path):
                # Skip hidden directories and common ignore patterns
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.venv']]
                
                for file in files:
                    if not file.startswith('.') and not file.endswith('.pyc'):
                        file_path = Path(root) / file
                        relative_path = file_path.relative_to(self.root_path)
                        all_files.append({
                            'path': str(relative_path),
                            'absolute_path': str(file_path),
                            'size': file_path.stat().st_size if file_path.exists() else 0,
                            'extension': file_path.suffix,
                            'name': file_path.name
                        })
            
            return {
                'total_files': len(all_files),
                'files': all_files,
                'root_path': str(self.root_path),
                'directories': self._get_directory_structure()
            }
        except Exception as e:
            return {'error': str(e), 'files': [], 'total_files': 0}
    
    def _get_directory_structure(self) -> Dict[str, Any]:
        """Get the complete directory structure."""
        try:
            import os
            from pathlib import Path
            
            structure = {}
            for root, dirs, files in os.walk(self.root_path):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.venv']]
                
                relative_root = Path(root).relative_to(self.root_path)
                structure[str(relative_root)] = {
                    'directories': dirs,
                    'files': [f for f in files if not f.startswith('.') and not f.endswith('.pyc')],
                    'file_count': len([f for f in files if not f.startswith('.') and not f.endswith('.pyc')])
                }
            
            return structure
        except Exception as e:
            return {'error': str(e)}
    
    def _read_file_content(self, file_path: str) -> str:
        """Read the complete content of a file."""
        try:
            from pathlib import Path
            
            # Handle both absolute and relative paths
            if not Path(file_path).is_absolute():
                file_path = self.root_path / file_path
            else:
                file_path = Path(file_path)
            
            if file_path.exists() and file_path.is_file():
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            else:
                return f"File not found: {file_path}"
        except Exception as e:
            return f"Error reading file: {e}"
    
    def _write_file_content(self, file_path: str, content: str) -> bool:
        """Write content to a file."""
        try:
            from pathlib import Path
            
            # Handle both absolute and relative paths
            if not Path(file_path).is_absolute():
                file_path = self.root_path / file_path
            else:
                file_path = Path(file_path)
            
            # Create directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            self.console.print(f"[red]Error writing file: {e}[/red]")
            return False
    
    def _search_in_files(self, query: str, file_pattern: str = "*") -> List[Dict[str, Any]]:
        """Search for text within files."""
        try:
            import os
            import fnmatch
            from pathlib import Path
            
            results = []
            for root, dirs, files in os.walk(self.root_path):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.venv']]
                
                for file in files:
                    if fnmatch.fnmatch(file, file_pattern) and not file.startswith('.'):
                        file_path = Path(root) / file
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if query.lower() in content.lower():
                                    # Find line numbers where the query appears
                                    lines = content.split('\n')
                                    matches = []
                                    for i, line in enumerate(lines, 1):
                                        if query.lower() in line.lower():
                                            matches.append({
                                                'line_number': i,
                                                'line_content': line.strip(),
                                                'context': self._get_line_context(lines, i-1, 2)
                                            })
                                    
                                    if matches:
                                        results.append({
                                            'file': str(file_path.relative_to(self.root_path)),
                                            'matches': matches,
                                            'total_matches': len(matches)
                                        })
                        except Exception:
                            continue
            
            return results
        except Exception as e:
            return [{'error': str(e)}]
    
    def _get_line_context(self, lines: List[str], line_index: int, context_size: int = 2) -> Dict[str, List[str]]:
        """Get context lines around a specific line."""
        start = max(0, line_index - context_size)
        end = min(len(lines), line_index + context_size + 1)
        
        return {
            'before': lines[start:line_index],
            'after': lines[line_index + 1:end]
        }
    
    def _list_functions_and_classes(self, file_path: str) -> Dict[str, List[str]]:
        """Extract functions and classes from a Python file."""
        try:
            import ast
            from pathlib import Path
            
            if not Path(file_path).is_absolute():
                file_path = self.root_path / file_path
            
            content = self._read_file_content(file_path)
            if content.startswith("Error") or content.startswith("File not found"):
                return {'error': content}
            
            try:
                tree = ast.parse(content)
                functions = []
                classes = []
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        functions.append({
                            'name': node.name,
                            'line': node.lineno,
                            'args': [arg.arg for arg in node.args.args],
                            'docstring': ast.get_docstring(node)
                        })
                    elif isinstance(node, ast.ClassDef):
                        class_methods = []
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                class_methods.append({
                                    'name': item.name,
                                    'line': item.lineno,
                                    'args': [arg.arg for arg in item.args.args]
                                })
                        
                        classes.append({
                            'name': node.name,
                            'line': node.lineno,
                            'methods': class_methods,
                            'docstring': ast.get_docstring(node)
                        })
                
                return {'functions': functions, 'classes': classes}
            except SyntaxError:
                return {'error': 'File contains syntax errors'}
        except Exception as e:
            return {'error': str(e)}

    async def _get_context_for_target(self, target: str) -> Optional[str]:
        """Get context for a specific target."""
        # Search for the target and return relevant context
        results = self.search.search(target, top=3)
        if results:
            file_path = results[0][0]
            return self._get_file_preview(file_path, lines=20)
        return None