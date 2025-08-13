from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import logging

from .config import Config
from .lsp import LSPManager, LSPDiagnostic, LSPSymbol, LSPLocation
from .tree_sitter import TreeSitterParser, SyntaxNode, SymbolInfo
from .context import ContextFile


@dataclass
class LanguageContext:
    """Enhanced context information for a file with language awareness."""
    file_path: Path
    language: str
    content: str
    syntax_tree: Optional[SyntaxNode] = None
    symbols: List[SymbolInfo] = field(default_factory=list)
    diagnostics: List[LSPDiagnostic] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    dependencies: List[Path] = field(default_factory=list)
    framework_info: Optional[Dict[str, Any]] = None
    
    @property
    def has_errors(self) -> bool:
        """Check if the file has any error diagnostics."""
        return any(diag.severity == 1 for diag in self.diagnostics)
    
    @property
    def has_warnings(self) -> bool:
        """Check if the file has any warning diagnostics."""
        return any(diag.severity == 2 for diag in self.diagnostics)
    
    def get_symbols_by_type(self, symbol_type: str) -> List[SymbolInfo]:
        """Get symbols of a specific type."""
        return [sym for sym in self.symbols if sym.type == symbol_type]
    
    def get_symbol_at_position(self, line: int, column: int) -> Optional[SymbolInfo]:
        """Get the symbol at a specific position."""
        for symbol in self.symbols:
            if symbol.definition_node.contains_position(line, column):
                return symbol
        return None


@dataclass
class FrameworkInfo:
    """Information about detected frameworks in the project."""
    name: str
    version: Optional[str] = None
    config_files: List[Path] = field(default_factory=list)
    entry_points: List[Path] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    patterns: Dict[str, List[str]] = field(default_factory=dict)


class LanguageAwareContextEngine:
    """Enhanced context engine with language awareness."""
    
    def __init__(self, config: Config, root_path: Path):
        self.config = config
        self.root_path = root_path
        self.lsp_manager = LSPManager(config, root_path)
        self.tree_sitter = TreeSitterParser(config)
        self.logger = logging.getLogger("language_aware")
        
        # Framework detection
        self.detected_frameworks: Dict[str, FrameworkInfo] = {}
        self._detect_frameworks()
        
        # Language-specific configurations
        self.language_configs = self._load_language_configs()
    
    def _load_language_configs(self) -> Dict[str, Dict]:
        """Load language-specific configurations."""
        default_configs = {
            "python": {
                "import_patterns": [r"^import\s+(\w+)", r"^from\s+(\w+)\s+import"],
                "test_patterns": ["test_*.py", "*_test.py"],
                "config_files": ["setup.py", "pyproject.toml", "requirements.txt", "Pipfile"],
                "framework_indicators": {
                    "django": ["manage.py", "settings.py", "urls.py"],
                    "flask": ["app.py", "application.py"],
                    "fastapi": ["main.py", "app.py"],
                    "pytest": ["conftest.py", "pytest.ini"]
                }
            },
            "javascript": {
                "import_patterns": [r"^import\s+.*\s+from\s+['\"](.+)['\"]", r"^const\s+.*\s+=\s+require\(['\"](.+)['\"]\)"],
                "test_patterns": ["*.test.js", "*.spec.js", "__tests__/**/*.js"],
                "config_files": ["package.json", "webpack.config.js", "babel.config.js"],
                "framework_indicators": {
                    "react": ["src/App.js", "src/index.js", "public/index.html"],
                    "vue": ["src/App.vue", "src/main.js"],
                    "angular": ["src/app/app.module.ts", "angular.json"],
                    "express": ["server.js", "app.js"],
                    "next": ["next.config.js", "pages/index.js"]
                }
            },
            "typescript": {
                "import_patterns": [r"^import\s+.*\s+from\s+['\"](.+)['\"]"],
                "test_patterns": ["*.test.ts", "*.spec.ts", "__tests__/**/*.ts"],
                "config_files": ["tsconfig.json", "package.json"],
                "framework_indicators": {
                    "react": ["src/App.tsx", "src/index.tsx"],
                    "angular": ["src/app/app.module.ts", "angular.json"],
                    "nest": ["src/main.ts", "nest-cli.json"]
                }
            },
            "rust": {
                "import_patterns": [r"^use\s+(.+);"],
                "test_patterns": ["tests/**/*.rs", "src/**/*test*.rs"],
                "config_files": ["Cargo.toml", "Cargo.lock"],
                "framework_indicators": {
                    "actix": ["src/main.rs"],
                    "rocket": ["src/main.rs"],
                    "warp": ["src/main.rs"]
                }
            },
            "go": {
                "import_patterns": [r"^import\s+[\"'](.+)[\"']"],
                "test_patterns": ["*_test.go"],
                "config_files": ["go.mod", "go.sum"],
                "framework_indicators": {
                    "gin": ["main.go"],
                    "echo": ["main.go"],
                    "fiber": ["main.go"]
                }
            },
            "java": {
                "import_patterns": [r"^import\s+(.+);"],
                "test_patterns": ["*Test.java", "*Tests.java"],
                "config_files": ["pom.xml", "build.gradle", "build.xml"],
                "framework_indicators": {
                    "spring": ["src/main/java/**/*Application.java", "application.properties"],
                    "maven": ["pom.xml"],
                    "gradle": ["build.gradle"]
                }
            }
        }
        
        # Override with user config
        user_configs = self.config.get("language_aware.languages", {})
        for lang, user_config in user_configs.items():
            if lang in default_configs:
                default_configs[lang].update(user_config)
            else:
                default_configs[lang] = user_config
        
        return default_configs
    
    def _detect_frameworks(self) -> None:
        """Detect frameworks used in the project."""
        # Check for common framework indicators
        framework_detectors = {
            "django": self._detect_django,
            "flask": self._detect_flask,
            "fastapi": self._detect_fastapi,
            "react": self._detect_react,
            "vue": self._detect_vue,
            "angular": self._detect_angular,
            "spring": self._detect_spring,
            "rust_web": self._detect_rust_web,
            "go_web": self._detect_go_web
        }
        
        for framework_name, detector in framework_detectors.items():
            try:
                framework_info = detector()
                if framework_info:
                    self.detected_frameworks[framework_name] = framework_info
            except Exception as e:
                self.logger.debug(f"Error detecting {framework_name}: {e}")
    
    def _detect_django(self) -> Optional[FrameworkInfo]:
        """Detect Django framework."""
        manage_py = self.root_path / "manage.py"
        if not manage_py.exists():
            return None
        
        # Look for Django-specific files
        config_files = []
        for pattern in ["**/settings.py", "**/urls.py", "**/wsgi.py"]:
            config_files.extend(self.root_path.glob(pattern))
        
        if config_files:
            return FrameworkInfo(
                name="django",
                config_files=[manage_py] + config_files,
                entry_points=[manage_py],
                patterns={
                    "models": ["**/models.py"],
                    "views": ["**/views.py"],
                    "urls": ["**/urls.py"],
                    "templates": ["**/templates/**/*.html"],
                    "static": ["**/static/**/*"]
                }
            )
        return None
    
    def _detect_flask(self) -> Optional[FrameworkInfo]:
        """Detect Flask framework."""
        app_files = list(self.root_path.glob("**/app.py")) + list(self.root_path.glob("**/application.py"))
        if not app_files:
            return None
        
        # Check if any app file imports Flask
        for app_file in app_files:
            try:
                content = app_file.read_text()
                if "from flask import" in content or "import flask" in content:
                    return FrameworkInfo(
                        name="flask",
                        config_files=app_files,
                        entry_points=app_files,
                        patterns={
                            "routes": ["**/routes.py", "**/views.py"],
                            "models": ["**/models.py"],
                            "templates": ["**/templates/**/*.html"],
                            "static": ["**/static/**/*"]
                        }
                    )
            except Exception:
                continue
        
        return None
    
    def _detect_fastapi(self) -> Optional[FrameworkInfo]:
        """Detect FastAPI framework."""
        main_files = list(self.root_path.glob("**/main.py")) + list(self.root_path.glob("**/app.py"))
        if not main_files:
            return None
        
        for main_file in main_files:
            try:
                content = main_file.read_text()
                if "from fastapi import" in content or "import fastapi" in content:
                    return FrameworkInfo(
                        name="fastapi",
                        config_files=main_files,
                        entry_points=main_files,
                        patterns={
                            "routers": ["**/routers/**/*.py"],
                            "models": ["**/models.py", "**/schemas.py"],
                            "dependencies": ["**/dependencies.py"]
                        }
                    )
            except Exception:
                continue
        
        return None
    
    def _detect_react(self) -> Optional[FrameworkInfo]:
        """Detect React framework."""
        package_json = self.root_path / "package.json"
        if not package_json.exists():
            return None
        
        try:
            import json
            with open(package_json) as f:
                package_data = json.load(f)
            
            dependencies = {**package_data.get("dependencies", {}), **package_data.get("devDependencies", {})}
            if "react" in dependencies:
                return FrameworkInfo(
                    name="react",
                    version=dependencies.get("react"),
                    config_files=[package_json],
                    entry_points=list(self.root_path.glob("src/index.js")) + list(self.root_path.glob("src/index.tsx")),
                    dependencies=list(dependencies.keys()),
                    patterns={
                        "components": ["src/components/**/*.js", "src/components/**/*.jsx", "src/components/**/*.ts", "src/components/**/*.tsx"],
                        "pages": ["src/pages/**/*.js", "src/pages/**/*.jsx", "src/pages/**/*.ts", "src/pages/**/*.tsx"],
                        "hooks": ["src/hooks/**/*.js", "src/hooks/**/*.ts"],
                        "utils": ["src/utils/**/*.js", "src/utils/**/*.ts"]
                    }
                )
        except Exception:
            pass
        
        return None
    
    def _detect_vue(self) -> Optional[FrameworkInfo]:
        """Detect Vue.js framework."""
        package_json = self.root_path / "package.json"
        if not package_json.exists():
            return None
        
        try:
            import json
            with open(package_json) as f:
                package_data = json.load(f)
            
            dependencies = {**package_data.get("dependencies", {}), **package_data.get("devDependencies", {})}
            if "vue" in dependencies:
                return FrameworkInfo(
                    name="vue",
                    version=dependencies.get("vue"),
                    config_files=[package_json],
                    entry_points=list(self.root_path.glob("src/main.js")) + list(self.root_path.glob("src/main.ts")),
                    dependencies=list(dependencies.keys()),
                    patterns={
                        "components": ["src/components/**/*.vue"],
                        "views": ["src/views/**/*.vue"],
                        "router": ["src/router/**/*.js", "src/router/**/*.ts"],
                        "store": ["src/store/**/*.js", "src/store/**/*.ts"]
                    }
                )
        except Exception:
            pass
        
        return None
    
    def _detect_angular(self) -> Optional[FrameworkInfo]:
        """Detect Angular framework."""
        angular_json = self.root_path / "angular.json"
        if not angular_json.exists():
            return None
        
        package_json = self.root_path / "package.json"
        version = None
        if package_json.exists():
            try:
                import json
                with open(package_json) as f:
                    package_data = json.load(f)
                dependencies = {**package_data.get("dependencies", {}), **package_data.get("devDependencies", {})}
                version = dependencies.get("@angular/core")
            except Exception:
                pass
        
        return FrameworkInfo(
            name="angular",
            version=version,
            config_files=[angular_json],
            entry_points=list(self.root_path.glob("src/main.ts")),
            patterns={
                "components": ["src/app/**/*.component.ts"],
                "services": ["src/app/**/*.service.ts"],
                "modules": ["src/app/**/*.module.ts"],
                "guards": ["src/app/**/*.guard.ts"],
                "pipes": ["src/app/**/*.pipe.ts"]
            }
        )
    
    def _detect_spring(self) -> Optional[FrameworkInfo]:
        """Detect Spring framework."""
        pom_xml = self.root_path / "pom.xml"
        build_gradle = self.root_path / "build.gradle"
        
        config_files = []
        if pom_xml.exists():
            config_files.append(pom_xml)
        if build_gradle.exists():
            config_files.append(build_gradle)
        
        if not config_files:
            return None
        
        # Look for Spring Boot application class
        app_files = list(self.root_path.glob("**/src/main/java/**/*Application.java"))
        if app_files:
            return FrameworkInfo(
                name="spring",
                config_files=config_files,
                entry_points=app_files,
                patterns={
                    "controllers": ["**/src/main/java/**/*Controller.java"],
                    "services": ["**/src/main/java/**/*Service.java"],
                    "repositories": ["**/src/main/java/**/*Repository.java"],
                    "entities": ["**/src/main/java/**/*Entity.java"],
                    "config": ["**/src/main/java/**/*Config.java"]
                }
            )
        
        return None
    
    def _detect_rust_web(self) -> Optional[FrameworkInfo]:
        """Detect Rust web frameworks."""
        cargo_toml = self.root_path / "Cargo.toml"
        if not cargo_toml.exists():
            return None
        
        try:
            content = cargo_toml.read_text()
            if any(framework in content for framework in ["actix-web", "rocket", "warp", "axum"]):
                return FrameworkInfo(
                    name="rust_web",
                    config_files=[cargo_toml],
                    entry_points=list(self.root_path.glob("src/main.rs")),
                    patterns={
                        "handlers": ["src/handlers/**/*.rs"],
                        "models": ["src/models/**/*.rs"],
                        "routes": ["src/routes/**/*.rs"],
                        "middleware": ["src/middleware/**/*.rs"]
                    }
                )
        except Exception:
            pass
        
        return None
    
    def _detect_go_web(self) -> Optional[FrameworkInfo]:
        """Detect Go web frameworks."""
        go_mod = self.root_path / "go.mod"
        if not go_mod.exists():
            return None
        
        try:
            content = go_mod.read_text()
            if any(framework in content for framework in ["gin-gonic/gin", "labstack/echo", "gofiber/fiber"]):
                return FrameworkInfo(
                    name="go_web",
                    config_files=[go_mod],
                    entry_points=list(self.root_path.glob("main.go")) + list(self.root_path.glob("cmd/**/main.go")),
                    patterns={
                        "handlers": ["handlers/**/*.go"],
                        "models": ["models/**/*.go"],
                        "routes": ["routes/**/*.go"],
                        "middleware": ["middleware/**/*.go"]
                    }
                )
        except Exception:
            pass
        
        return None
    
    async def analyze_file(self, file_path: Path) -> Optional[LanguageContext]:
        """Analyze a file with language awareness."""
        if not file_path.exists():
            return None
        
        try:
            content = file_path.read_text(encoding='utf-8')
            language = self.tree_sitter.get_language_for_file(file_path)
            
            if not language:
                return None
            
            # Parse syntax tree
            syntax_tree = self.tree_sitter.parse_content(content, language)
            
            # Extract symbols
            symbols = []
            if syntax_tree:
                symbols = self.tree_sitter.extract_symbols(syntax_tree)
            
            # Get LSP diagnostics
            diagnostics = await self.lsp_manager.get_diagnostics(file_path)
            
            # Extract imports
            imports = self._extract_imports(content, language)
            
            # Find dependencies
            dependencies = self._find_dependencies(file_path, imports, language)
            
            # Get framework info
            framework_info = self._get_framework_info_for_file(file_path)
            
            return LanguageContext(
                file_path=file_path,
                language=language,
                content=content,
                syntax_tree=syntax_tree,
                symbols=symbols,
                diagnostics=diagnostics,
                imports=imports,
                dependencies=dependencies,
                framework_info=framework_info
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing file {file_path}: {e}")
            return None
    
    def _extract_imports(self, content: str, language: str) -> List[str]:
        """Extract import statements from code."""
        imports = []
        
        if language not in self.language_configs:
            return imports
        
        import_patterns = self.language_configs[language].get("import_patterns", [])
        
        for pattern in import_patterns:
            import re
            matches = re.findall(pattern, content, re.MULTILINE)
            imports.extend(matches)
        
        return imports
    
    def _find_dependencies(self, file_path: Path, imports: List[str], language: str) -> List[Path]:
        """Find dependency files based on imports."""
        dependencies = []
        
        for import_name in imports:
            # Try to resolve import to actual file
            resolved_path = self._resolve_import(file_path, import_name, language)
            if resolved_path and resolved_path.exists():
                dependencies.append(resolved_path)
        
        return dependencies
    
    def _resolve_import(self, file_path: Path, import_name: str, language: str) -> Optional[Path]:
        """Resolve an import to a file path."""
        base_dir = file_path.parent
        
        if language == "python":
            # Handle Python imports
            if "." in import_name:
                # Package import
                parts = import_name.split(".")
                potential_path = base_dir
                for part in parts:
                    potential_path = potential_path / part
                
                # Try .py file
                py_file = potential_path.with_suffix(".py")
                if py_file.exists():
                    return py_file
                
                # Try __init__.py in directory
                init_file = potential_path / "__init__.py"
                if init_file.exists():
                    return init_file
            else:
                # Simple import
                py_file = base_dir / f"{import_name}.py"
                if py_file.exists():
                    return py_file
        
        elif language in ["javascript", "typescript"]:
            # Handle JS/TS imports
            if import_name.startswith("."):
                # Relative import
                import_path = base_dir / import_name.lstrip("./")
                
                # Try various extensions
                for ext in [".js", ".ts", ".jsx", ".tsx"]:
                    file_with_ext = import_path.with_suffix(ext)
                    if file_with_ext.exists():
                        return file_with_ext
                
                # Try index files
                for ext in [".js", ".ts", ".jsx", ".tsx"]:
                    index_file = import_path / f"index{ext}"
                    if index_file.exists():
                        return index_file
        
        return None
    
    def _get_framework_info_for_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Get framework-specific information for a file."""
        for framework_name, framework_info in self.detected_frameworks.items():
            # Check if file matches any framework patterns
            for pattern_type, patterns in framework_info.patterns.items():
                for pattern in patterns:
                    if file_path.match(pattern):
                        return {
                            "framework": framework_name,
                            "pattern_type": pattern_type,
                            "version": framework_info.version,
                            "entry_points": [str(ep) for ep in framework_info.entry_points]
                        }
        
        return None
    
    async def get_enhanced_context(self, files: List[Path], query: Optional[str] = None) -> List[LanguageContext]:
        """Get enhanced context for multiple files."""
        contexts = []
        
        for file_path in files:
            context = await self.analyze_file(file_path)
            if context:
                contexts.append(context)
        
        # Sort by relevance if query provided
        if query and contexts:
            contexts = self._rank_contexts_by_relevance(contexts, query)
        
        return contexts
    
    def _rank_contexts_by_relevance(self, contexts: List[LanguageContext], query: str) -> List[LanguageContext]:
        """Rank contexts by relevance to the query."""
        scored_contexts = []
        
        for context in contexts:
            score = 0
            
            # Score based on content match
            if query.lower() in context.content.lower():
                score += 10
            
            # Score based on symbol names
            for symbol in context.symbols:
                if query.lower() in symbol.name.lower():
                    score += 5
            
            # Score based on file name
            if query.lower() in context.file_path.name.lower():
                score += 3
            
            # Boost score for files with errors (might be relevant for debugging)
            if context.has_errors:
                score += 2
            
            # Boost score for framework-specific files
            if context.framework_info:
                score += 1
            
            scored_contexts.append((score, context))
        
        # Sort by score (descending)
        scored_contexts.sort(key=lambda x: x[0], reverse=True)
        
        return [context for _, context in scored_contexts]
    
    async def get_symbol_references(self, file_path: Path, line: int, column: int) -> List[LSPLocation]:
        """Get references to a symbol at a specific position."""
        return await self.lsp_manager.get_references(file_path, line, column)
    
    async def get_symbol_definition(self, file_path: Path, line: int, column: int) -> List[LSPLocation]:
        """Get definition of a symbol at a specific position."""
        return await self.lsp_manager.get_definition(file_path, line, column)
    
    async def get_completion_suggestions(self, file_path: Path, line: int, column: int) -> List[str]:
        """Get completion suggestions at a specific position."""
        completions = await self.lsp_manager.get_completion(file_path, line, column)
        return [comp.label for comp in completions]
    
    def get_test_files_for(self, file_path: Path) -> List[Path]:
        """Get test files related to a source file."""
        language = self.tree_sitter.get_language_for_file(file_path)
        if not language or language not in self.language_configs:
            return []
        
        test_patterns = self.language_configs[language].get("test_patterns", [])
        test_files = []
        
        # Look for test files with similar names
        file_stem = file_path.stem
        file_dir = file_path.parent
        
        for pattern in test_patterns:
            if "*" in pattern:
                # Handle glob patterns
                pattern_with_name = pattern.replace("*", file_stem)
                test_candidates = list(self.root_path.glob(pattern_with_name))
                test_files.extend(test_candidates)
            else:
                # Handle specific patterns
                test_file = file_dir / pattern
                if test_file.exists():
                    test_files.append(test_file)
        
        return test_files
    
    def get_related_files(self, file_path: Path) -> List[Path]:
        """Get files related to the given file."""
        related = []
        
        # Add dependency files
        context = asyncio.run(self.analyze_file(file_path))
        if context:
            related.extend(context.dependencies)
        
        # Add test files
        related.extend(self.get_test_files_for(file_path))
        
        # Add framework-specific related files
        framework_info = self._get_framework_info_for_file(file_path)
        if framework_info:
            related.extend(self._get_framework_related_files(file_path, framework_info))
        
        return list(set(related))  # Remove duplicates
    
    def _get_framework_related_files(self, file_path: Path, framework_info: Dict[str, Any]) -> List[Path]:
        """Get framework-specific related files."""
        related = []
        framework_name = framework_info.get("framework")
        
        if framework_name == "django":
            # For Django, relate models, views, and URLs
            if "models.py" in str(file_path):
                # Find related views and admin files
                app_dir = file_path.parent
                related.extend(app_dir.glob("views.py"))
                related.extend(app_dir.glob("admin.py"))
                related.extend(app_dir.glob("urls.py"))
            elif "views.py" in str(file_path):
                # Find related models and URLs
                app_dir = file_path.parent
                related.extend(app_dir.glob("models.py"))
                related.extend(app_dir.glob("urls.py"))
        
        elif framework_name == "react":
            # For React, relate components and their tests
            if file_path.suffix in [".jsx", ".tsx"]:
                # Find test files
                test_file = file_path.with_suffix(".test" + file_path.suffix)
                if test_file.exists():
                    related.append(test_file)
                
                # Find style files
                style_file = file_path.with_suffix(".css")
                if style_file.exists():
                    related.append(style_file)
        
        return related
    
    async def shutdown(self) -> None:
        """Shutdown the language-aware context engine."""
        await self.lsp_manager.shutdown_all()