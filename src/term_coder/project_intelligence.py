"""
Project Intelligence - Smart context awareness and project understanding.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.text import Text

from .utils import iter_source_files
from .config import Config


@dataclass
class ProjectMetrics:
    """Project metrics and statistics."""
    total_files: int = 0
    source_files: int = 0
    total_lines: int = 0
    source_lines: int = 0
    languages: Dict[str, int] = None
    file_types: Dict[str, int] = None
    test_files: int = 0
    documentation_files: int = 0
    configuration_files: int = 0
    complexity_score: float = 0.0
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.languages is None:
            self.languages = {}
        if self.file_types is None:
            self.file_types = {}
        if self.last_updated is None:
            self.last_updated = datetime.now()


@dataclass
class FileAnalysis:
    """Analysis of a single file."""
    path: str
    language: str
    lines: int
    functions: List[str]
    classes: List[str]
    imports: List[str]
    exports: List[str]
    dependencies: List[str]
    complexity: float
    last_modified: datetime
    is_test: bool = False
    is_config: bool = False
    is_documentation: bool = False


@dataclass
class ProjectStructure:
    """Project structure analysis."""
    root_path: Path
    main_directories: List[str]
    entry_points: List[str]
    test_directories: List[str]
    documentation_directories: List[str]
    configuration_files: List[str]
    build_files: List[str]
    dependency_files: List[str]
    framework_indicators: Dict[str, List[str]]
    architecture_pattern: str = "unknown"


class ProjectIntelligence:
    """Smart project context awareness and analysis."""
    
    def __init__(self, root: Path, config: Config):
        self.root = root
        self.config = config
        self.console = Console()
        
        # Cache for analysis results
        self.cache_dir = root / ".term-coder" / "intelligence"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.metrics_file = self.cache_dir / "metrics.json"
        self.structure_file = self.cache_dir / "structure.json"
        self.files_file = self.cache_dir / "files.json"
        
        # Cached data
        self._metrics: Optional[ProjectMetrics] = None
        self._structure: Optional[ProjectStructure] = None
        self._file_analyses: Dict[str, FileAnalysis] = {}
        
        # Language patterns
        self.language_patterns = {
            'python': {
                'extensions': ['.py', '.pyx', '.pyi'],
                'function_pattern': r'def\s+(\w+)\s*\(',
                'class_pattern': r'class\s+(\w+)\s*[:\(]',
                'import_pattern': r'(?:from\s+(\S+)\s+)?import\s+([^#\n]+)',
            },
            'javascript': {
                'extensions': ['.js', '.jsx', '.mjs'],
                'function_pattern': r'(?:function\s+(\w+)|(\w+)\s*[:=]\s*(?:function|\([^)]*\)\s*=>))',
                'class_pattern': r'class\s+(\w+)\s*[{]',
                'import_pattern': r'import\s+(?:[^from]*from\s+)?["\']([^"\']+)["\']',
            },
            'typescript': {
                'extensions': ['.ts', '.tsx'],
                'function_pattern': r'(?:function\s+(\w+)|(\w+)\s*[:=]\s*(?:function|\([^)]*\)\s*=>))',
                'class_pattern': r'(?:class|interface)\s+(\w+)\s*[{<]',
                'import_pattern': r'import\s+(?:[^from]*from\s+)?["\']([^"\']+)["\']',
            },
            'java': {
                'extensions': ['.java'],
                'function_pattern': r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(',
                'class_pattern': r'(?:public|private)?\s*class\s+(\w+)\s*[{]',
                'import_pattern': r'import\s+([^;]+);',
            },
            'cpp': {
                'extensions': ['.cpp', '.cxx', '.cc', '.c++', '.hpp', '.hxx', '.h++'],
                'function_pattern': r'\w+\s+(\w+)\s*\([^)]*\)\s*[{;]',
                'class_pattern': r'class\s+(\w+)\s*[{:]',
                'import_pattern': r'#include\s*[<"]([^>"]+)[>"]',
            },
            'go': {
                'extensions': ['.go'],
                'function_pattern': r'func\s+(?:\([^)]*\)\s+)?(\w+)\s*\(',
                'class_pattern': r'type\s+(\w+)\s+struct\s*{',
                'import_pattern': r'import\s+(?:[^"]*"([^"]+)"|\(([^)]+)\))',
            },
            'rust': {
                'extensions': ['.rs'],
                'function_pattern': r'fn\s+(\w+)\s*[(<]',
                'class_pattern': r'(?:struct|enum|trait)\s+(\w+)\s*[{<]',
                'import_pattern': r'use\s+([^;]+);',
            }
        }
        
        # Framework detection patterns
        self.framework_patterns = {
            'react': ['react', 'jsx', 'tsx', 'package.json with react'],
            'vue': ['vue', '.vue files', 'package.json with vue'],
            'angular': ['angular', '@angular', 'angular.json'],
            'django': ['django', 'manage.py', 'settings.py'],
            'flask': ['flask', 'app.py', 'from flask'],
            'fastapi': ['fastapi', 'from fastapi'],
            'express': ['express', 'package.json with express'],
            'spring': ['springframework', '@SpringBootApplication'],
            'rails': ['rails', 'Gemfile', 'app/controllers'],
            'laravel': ['laravel', 'artisan', 'composer.json with laravel'],
        }
    
    def analyze_project(self, force_refresh: bool = False) -> ProjectMetrics:
        """Analyze the entire project and return metrics."""
        if not force_refresh and self._metrics and self._is_cache_valid():
            return self._metrics
        
        self.console.print("[dim]Analyzing project structure and metrics...[/dim]")
        
        # Initialize metrics
        metrics = ProjectMetrics()
        file_analyses = {}
        
        # Analyze all files
        for file_path in self.root.rglob('*'):
            if file_path.is_file() and not self._should_ignore_file(file_path):
                try:
                    analysis = self._analyze_file(file_path)
                    if analysis:
                        file_analyses[str(file_path.relative_to(self.root))] = analysis
                        self._update_metrics(metrics, analysis)
                except Exception as e:
                    continue  # Skip files that can't be analyzed
        
        # Calculate complexity score
        metrics.complexity_score = self._calculate_project_complexity(file_analyses)
        metrics.last_updated = datetime.now()
        
        # Cache results
        self._metrics = metrics
        self._file_analyses = file_analyses
        self._save_analysis_cache()
        
        return metrics
    
    def analyze_project_structure(self) -> ProjectStructure:
        """Analyze and return project structure."""
        if self._structure and self._is_cache_valid():
            return self._structure
        
        structure = ProjectStructure(root_path=self.root)
        
        # Analyze directory structure
        structure.main_directories = self._find_main_directories()
        structure.entry_points = self._find_entry_points()
        structure.test_directories = self._find_test_directories()
        structure.documentation_directories = self._find_documentation_directories()
        structure.configuration_files = self._find_configuration_files()
        structure.build_files = self._find_build_files()
        structure.dependency_files = self._find_dependency_files()
        
        # Detect frameworks
        structure.framework_indicators = self._detect_frameworks()
        
        # Determine architecture pattern
        structure.architecture_pattern = self._determine_architecture_pattern(structure)
        
        # Cache results
        self._structure = structure
        self._save_structure_cache()
        
        return structure
    
    def get_file_context(self, file_path: str) -> Dict[str, Any]:
        """Get intelligent context for a specific file."""
        rel_path = str(Path(file_path).relative_to(self.root))
        
        if rel_path in self._file_analyses:
            analysis = self._file_analyses[rel_path]
        else:
            analysis = self._analyze_file(Path(file_path))
        
        if not analysis:
            return {}
        
        # Find related files
        related_files = self._find_related_files(analysis)
        
        # Get usage patterns
        usage_patterns = self._analyze_usage_patterns(analysis)
        
        return {
            'analysis': asdict(analysis),
            'related_files': related_files,
            'usage_patterns': usage_patterns,
            'suggestions': self._get_file_suggestions(analysis)
        }
    
    def suggest_next_actions(self) -> List[str]:
        """Suggest intelligent next actions based on project state."""
        suggestions = []
        
        if not self._metrics:
            self.analyze_project()
        
        # Analyze patterns and suggest improvements
        if self._metrics.test_files < self._metrics.source_files * 0.3:
            suggestions.append("Consider adding more test coverage - current ratio is low")
        
        if self._metrics.documentation_files < 3:
            suggestions.append("Add more documentation files (README, CONTRIBUTING, etc.)")
        
        if self._metrics.complexity_score > 7.0:
            suggestions.append("High complexity detected - consider refactoring complex functions")
        
        # Check for common issues
        suggestions.extend(self._detect_common_issues())
        
        # Framework-specific suggestions
        suggestions.extend(self._get_framework_suggestions())
        
        return suggestions[:10]  # Limit to top 10 suggestions
    
    def find_similar_files(self, file_path: str, limit: int = 5) -> List[Tuple[str, float]]:
        """Find files similar to the given file."""
        target_analysis = self._analyze_file(Path(file_path))
        if not target_analysis:
            return []
        
        similar_files = []
        
        for rel_path, analysis in self._file_analyses.items():
            if rel_path == str(Path(file_path).relative_to(self.root)):
                continue
            
            similarity = self._calculate_file_similarity(target_analysis, analysis)
            if similarity > 0.3:  # Threshold for similarity
                similar_files.append((rel_path, similarity))
        
        return sorted(similar_files, key=lambda x: x[1], reverse=True)[:limit]
    
    def _analyze_file(self, file_path: Path) -> Optional[FileAnalysis]:
        """Analyze a single file."""
        try:
            if not file_path.exists() or file_path.stat().st_size > 1024 * 1024:  # 1MB limit
                return None
            
            # Determine language
            language = self._detect_language(file_path)
            if not language:
                return None
            
            # Read file content
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
            except UnicodeDecodeError:
                content = file_path.read_text(encoding='latin-1', errors='ignore')
            
            lines = content.splitlines()
            
            # Extract code elements
            functions = self._extract_functions(content, language)
            classes = self._extract_classes(content, language)
            imports = self._extract_imports(content, language)
            
            # Calculate complexity
            complexity = self._calculate_file_complexity(content, language)
            
            # Determine file type
            is_test = self._is_test_file(file_path)
            is_config = self._is_config_file(file_path)
            is_doc = self._is_documentation_file(file_path)
            
            return FileAnalysis(
                path=str(file_path.relative_to(self.root)),
                language=language,
                lines=len(lines),
                functions=functions,
                classes=classes,
                imports=imports,
                exports=[],  # Could be implemented for specific languages
                dependencies=self._extract_dependencies(imports, language),
                complexity=complexity,
                last_modified=datetime.fromtimestamp(file_path.stat().st_mtime),
                is_test=is_test,
                is_config=is_config,
                is_documentation=is_doc
            )
            
        except Exception as e:
            return None
    
    def _detect_language(self, file_path: Path) -> Optional[str]:
        """Detect the programming language of a file."""
        suffix = file_path.suffix.lower()
        
        for language, config in self.language_patterns.items():
            if suffix in config['extensions']:
                return language
        
        # Special cases
        if file_path.name.lower() in ['makefile', 'dockerfile']:
            return file_path.name.lower()
        
        return None
    
    def _extract_functions(self, content: str, language: str) -> List[str]:
        """Extract function names from content."""
        if language not in self.language_patterns:
            return []
        
        pattern = self.language_patterns[language]['function_pattern']
        matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
        
        # Handle multiple capture groups
        functions = []
        for match in matches:
            if isinstance(match, tuple):
                for group in match:
                    if group and group.strip():
                        functions.append(group.strip())
                        break
            else:
                functions.append(match.strip())
        
        return list(set(functions))  # Remove duplicates
    
    def _extract_classes(self, content: str, language: str) -> List[str]:
        """Extract class names from content."""
        if language not in self.language_patterns:
            return []
        
        pattern = self.language_patterns[language]['class_pattern']
        matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
        
        return [match.strip() if isinstance(match, str) else match[0].strip() 
                for match in matches]
    
    def _extract_imports(self, content: str, language: str) -> List[str]:
        """Extract import statements from content."""
        if language not in self.language_patterns:
            return []
        
        pattern = self.language_patterns[language]['import_pattern']
        matches = re.findall(pattern, content, re.MULTILINE)
        
        imports = []
        for match in matches:
            if isinstance(match, tuple):
                for group in match:
                    if group and group.strip():
                        imports.append(group.strip())
            else:
                imports.append(match.strip())
        
        return list(set(imports))  # Remove duplicates
    
    def _extract_dependencies(self, imports: List[str], language: str) -> List[str]:
        """Extract external dependencies from imports."""
        dependencies = []
        
        for imp in imports:
            # Clean up import string
            clean_imp = imp.split('.')[0].split('/')[0].strip('\'"')
            
            # Filter out relative imports and stdlib
            if language == 'python':
                if not clean_imp.startswith('.') and clean_imp not in self._get_python_stdlib():
                    dependencies.append(clean_imp)
            elif language in ['javascript', 'typescript']:
                if not clean_imp.startswith('.') and not clean_imp.startswith('/'):
                    dependencies.append(clean_imp)
            else:
                dependencies.append(clean_imp)
        
        return list(set(dependencies))
    
    def _calculate_file_complexity(self, content: str, language: str) -> float:
        """Calculate complexity score for a file."""
        lines = content.splitlines()
        
        # Basic metrics
        code_lines = len([line for line in lines if line.strip() and not line.strip().startswith(('#', '//', '/*'))])
        
        if code_lines == 0:
            return 0.0
        
        # Count complexity indicators
        complexity_indicators = {
            'if_statements': len(re.findall(r'\bif\s+', content)),
            'loops': len(re.findall(r'\b(for|while)\s+', content)),
            'functions': len(self._extract_functions(content, language)),
            'classes': len(self._extract_classes(content, language)),
            'nested_blocks': content.count('{') + content.count('def ') + content.count('class '),
            'long_functions': len([f for f in content.split('def ') if len(f.splitlines()) > 20])
        }
        
        # Calculate weighted complexity
        weights = {
            'if_statements': 0.5,
            'loops': 1.0,
            'functions': 0.3,
            'classes': 0.2,
            'nested_blocks': 0.4,
            'long_functions': 2.0
        }
        
        total_complexity = sum(count * weights.get(metric, 0.5) 
                              for metric, count in complexity_indicators.items())
        
        # Normalize by code lines
        return min(total_complexity / max(code_lines / 10, 1), 10.0)  # Cap at 10.0
    
    def _calculate_project_complexity(self, file_analyses: Dict[str, FileAnalysis]) -> float:
        """Calculate overall project complexity."""
        if not file_analyses:
            return 0.0
        
        complexities = [analysis.complexity for analysis in file_analyses.values()]
        
        # Weighted average with emphasis on high complexity files
        sorted_complexities = sorted(complexities, reverse=True)
        total_files = len(complexities)
        
        if total_files == 0:
            return 0.0
        
        # Weight higher complexity files more heavily
        weighted_sum = 0.0
        weight_sum = 0.0
        
        for i, complexity in enumerate(sorted_complexities):
            weight = 1.0 / (i + 1)  # Decreasing weight
            weighted_sum += complexity * weight
            weight_sum += weight
        
        return weighted_sum / weight_sum if weight_sum > 0 else 0.0
    
    def _should_ignore_file(self, file_path: Path) -> bool:
        """Check if file should be ignored during analysis."""
        # Ignore patterns
        ignore_patterns = [
            r'\.git/',
            r'__pycache__/',
            r'node_modules/',
            r'\.env',
            r'\.venv/',
            r'venv/',
            r'build/',
            r'dist/',
            r'target/',
            r'\.DS_Store',
            r'\.pyc$',
            r'\.pyo$',
            r'\.class$',
            r'\.o$',
            r'\.so$',
            r'\.exe$',
            r'\.dll$',
        ]
        
        path_str = str(file_path.relative_to(self.root))
        
        return any(re.search(pattern, path_str) for pattern in ignore_patterns)
    
    def _is_test_file(self, file_path: Path) -> bool:
        """Check if file is a test file."""
        path_str = str(file_path).lower()
        name = file_path.name.lower()
        
        test_indicators = [
            'test_', '_test', 'tests/', '/test/', 'spec_', '_spec',
            'tests.py', 'test.py', 'spec.js', '.spec.', '.test.'
        ]
        
        return any(indicator in path_str or indicator in name 
                  for indicator in test_indicators)
    
    def _is_config_file(self, file_path: Path) -> bool:
        """Check if file is a configuration file."""
        config_files = {
            'package.json', 'pyproject.toml', 'setup.py', 'requirements.txt',
            'cargo.toml', 'go.mod', 'pom.xml', 'build.gradle',
            'webpack.config.js', 'vite.config.js', 'tsconfig.json',
            '.gitignore', '.eslintrc', '.prettierrc', 'docker-compose.yml',
            'dockerfile', 'makefile'
        }
        
        config_extensions = {'.toml', '.yaml', '.yml', '.ini', '.cfg', '.conf'}
        
        name = file_path.name.lower()
        suffix = file_path.suffix.lower()
        
        return name in config_files or suffix in config_extensions
    
    def _is_documentation_file(self, file_path: Path) -> bool:
        """Check if file is documentation."""
        doc_extensions = {'.md', '.rst', '.txt'}
        doc_names = {'readme', 'license', 'changelog', 'contributing', 'authors'}
        
        name = file_path.stem.lower()
        suffix = file_path.suffix.lower()
        
        return suffix in doc_extensions or name in doc_names
    
    def _find_main_directories(self) -> List[str]:
        """Find main project directories."""
        main_dirs = []
        
        for item in self.root.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Check if directory contains source code
                source_files = list(iter_source_files(item))
                if source_files:
                    main_dirs.append(item.name)
        
        return sorted(main_dirs)
    
    def _find_entry_points(self) -> List[str]:
        """Find likely entry points for the application."""
        entry_point_names = [
            'main.py', 'app.py', 'server.py', 'index.js', 'main.js',
            'App.js', 'index.html', 'main.go', 'main.rs', 'Main.java'
        ]
        
        entry_points = []
        
        for file_pattern in entry_point_names:
            matches = list(self.root.rglob(file_pattern))
            entry_points.extend(str(match.relative_to(self.root)) for match in matches)
        
        return entry_points
    
    def _detect_frameworks(self) -> Dict[str, List[str]]:
        """Detect frameworks used in the project."""
        detected = {}
        
        for framework, indicators in self.framework_patterns.items():
            evidence = []
            
            for indicator in indicators:
                if 'package.json' in indicator:
                    package_json = self.root / 'package.json'
                    if package_json.exists():
                        try:
                            content = package_json.read_text()
                            if framework in content.lower():
                                evidence.append(f"Found in {package_json.name}")
                        except:
                            pass
                
                elif indicator.endswith(' files'):
                    extension = indicator.split()[0]
                    if list(self.root.rglob(f'*{extension}')):
                        evidence.append(f"Found {extension} files")
                
                elif indicator.startswith('from ') or indicator.startswith('import '):
                    # Check Python imports
                    for py_file in self.root.rglob('*.py'):
                        try:
                            content = py_file.read_text(errors='ignore')
                            if indicator in content:
                                evidence.append(f"Import found in {py_file.name}")
                                break
                        except:
                            pass
                
                else:
                    # Generic file/content search
                    if list(self.root.rglob(f'*{indicator}*')):
                        evidence.append(f"Found {indicator}")
            
            if evidence:
                detected[framework] = evidence
        
        return detected
    
    def _get_python_stdlib(self) -> Set[str]:
        """Get Python standard library modules (subset)."""
        return {
            'os', 'sys', 'json', 'datetime', 're', 'pathlib', 'typing',
            'collections', 'itertools', 'functools', 'asyncio', 'threading',
            'multiprocessing', 'subprocess', 'unittest', 'logging', 'argparse',
            'configparser', 'urllib', 'http', 'socket', 'email', 'html',
            'xml', 'sqlite3', 'csv', 'hashlib', 'base64', 'uuid', 'random',
            'math', 'statistics', 'decimal', 'fractions', 'time', 'calendar'
        }
    
    def _update_metrics(self, metrics: ProjectMetrics, analysis: FileAnalysis) -> None:
        """Update project metrics with file analysis."""
        metrics.total_files += 1
        
        if analysis.language in self.language_patterns:
            metrics.source_files += 1
            metrics.source_lines += analysis.lines
            
            # Update language counts
            metrics.languages[analysis.language] = metrics.languages.get(analysis.language, 0) + 1
        
        metrics.total_lines += analysis.lines
        
        # Update file type counts
        extension = Path(analysis.path).suffix.lower()
        metrics.file_types[extension] = metrics.file_types.get(extension, 0) + 1
        
        if analysis.is_test:
            metrics.test_files += 1
        
        if analysis.is_documentation:
            metrics.documentation_files += 1
        
        if analysis.is_config:
            metrics.configuration_files += 1
    
    def _is_cache_valid(self) -> bool:
        """Check if cached analysis is still valid."""
        if not self.metrics_file.exists():
            return False
        
        # Cache is valid for 1 hour
        cache_age = time.time() - self.metrics_file.stat().st_mtime
        return cache_age < 3600  # 1 hour
    
    def _save_analysis_cache(self) -> None:
        """Save analysis results to cache."""
        try:
            if self._metrics:
                with open(self.metrics_file, 'w') as f:
                    json.dump(asdict(self._metrics), f, indent=2, default=str)
            
            if self._file_analyses:
                with open(self.files_file, 'w') as f:
                    file_data = {path: asdict(analysis) 
                                for path, analysis in self._file_analyses.items()}
                    json.dump(file_data, f, indent=2, default=str)
                    
        except Exception as e:
            pass  # Ignore cache save errors
    
    def _save_structure_cache(self) -> None:
        """Save structure analysis to cache."""
        try:
            if self._structure:
                with open(self.structure_file, 'w') as f:
                    json.dump(asdict(self._structure), f, indent=2, default=str)
        except Exception as e:
            pass  # Ignore cache save errors
    
    def show_project_insights(self) -> None:
        """Display comprehensive project insights."""
        metrics = self.analyze_project()
        structure = self.analyze_project_structure()
        
        self.console.print("[bold cyan]📊 Project Intelligence Report[/bold cyan]\n")
        
        # Metrics table
        metrics_table = Table(title="Project Metrics", show_header=False)
        metrics_table.add_column("Metric", style="cyan", width=25)
        metrics_table.add_column("Value", style="white", width=15)
        
        metrics_table.add_row("Total Files", str(metrics.total_files))
        metrics_table.add_row("Source Files", str(metrics.source_files))
        metrics_table.add_row("Lines of Code", f"{metrics.total_lines:,}")
        metrics_table.add_row("Test Files", str(metrics.test_files))
        metrics_table.add_row("Documentation", str(metrics.documentation_files))
        metrics_table.add_row("Complexity Score", f"{metrics.complexity_score:.1f}/10")
        
        self.console.print(metrics_table)
        
        # Languages table
        if metrics.languages:
            lang_table = Table(title="Languages", show_header=True)
            lang_table.add_column("Language", style="cyan")
            lang_table.add_column("Files", style="white")
            lang_table.add_column("Percentage", style="yellow")
            
            total_source = sum(metrics.languages.values())
            for lang, count in sorted(metrics.languages.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_source) * 100 if total_source > 0 else 0
                lang_table.add_row(lang.title(), str(count), f"{percentage:.1f}%")
            
            self.console.print(lang_table)
        
        # Framework detection
        if structure.framework_indicators:
            frameworks_panel = Panel(
                "\n".join([f"• [bold]{fw}[/bold]: {', '.join(evidence[:2])}" 
                          for fw, evidence in structure.framework_indicators.items()]),
                title="🚀 Detected Frameworks",
                border_style="green"
            )
            self.console.print(frameworks_panel)
        
        # Suggestions
        suggestions = self.suggest_next_actions()
        if suggestions:
            suggestions_text = "\n".join([f"• {suggestion}" for suggestion in suggestions])
            suggestions_panel = Panel(
                suggestions_text,
                title="💡 Suggested Improvements",
                border_style="yellow"
            )
            self.console.print(suggestions_panel)


# Additional helper methods would go here for completeness
# (file similarity calculation, usage pattern analysis, etc.)