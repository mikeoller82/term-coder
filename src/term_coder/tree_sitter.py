from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import logging

try:
    import tree_sitter
    from tree_sitter import Language, Parser, Node, Tree
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    # Create dummy classes for type hints
    class Language: pass
    class Parser: pass
    class Node: pass
    class Tree: pass

from .config import Config


@dataclass
class SyntaxNode:
    """Represents a syntax node with metadata."""
    type: str
    text: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    children: List['SyntaxNode'] = field(default_factory=list)
    parent: Optional['SyntaxNode'] = None
    
    @property
    def range(self) -> Tuple[int, int, int, int]:
        """Get the range as (start_line, start_col, end_line, end_col)."""
        return (self.start_line, self.start_column, self.end_line, self.end_column)
    
    def contains_position(self, line: int, column: int) -> bool:
        """Check if this node contains the given position."""
        if line < self.start_line or line > self.end_line:
            return False
        if line == self.start_line and column < self.start_column:
            return False
        if line == self.end_line and column > self.end_column:
            return False
        return True
    
    def find_child_at_position(self, line: int, column: int) -> Optional['SyntaxNode']:
        """Find the deepest child node at the given position."""
        if not self.contains_position(line, column):
            return None
        
        # Check children first (deepest first)
        for child in self.children:
            result = child.find_child_at_position(line, column)
            if result:
                return result
        
        # If no child contains the position, return this node
        return self
    
    def find_nodes_by_type(self, node_type: str) -> List['SyntaxNode']:
        """Find all nodes of a specific type in this subtree."""
        result = []
        if self.type == node_type:
            result.append(self)
        
        for child in self.children:
            result.extend(child.find_nodes_by_type(node_type))
        
        return result
    
    def get_ancestors(self) -> List['SyntaxNode']:
        """Get all ancestor nodes."""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors
    
    def get_scope(self) -> Optional['SyntaxNode']:
        """Get the containing scope (function, class, etc.)."""
        scope_types = {
            'function_definition', 'method_definition', 'class_definition',
            'function_declaration', 'method_declaration', 'class_declaration',
            'function', 'method', 'class', 'struct', 'impl', 'trait'
        }
        
        for ancestor in self.get_ancestors():
            if ancestor.type in scope_types:
                return ancestor
        
        return None


@dataclass
class SymbolInfo:
    """Information about a symbol in the code."""
    name: str
    type: str  # function, class, variable, etc.
    definition_node: SyntaxNode
    references: List[SyntaxNode] = field(default_factory=list)
    scope: Optional[SyntaxNode] = None
    docstring: Optional[str] = None
    
    @property
    def definition_range(self) -> Tuple[int, int, int, int]:
        """Get the definition range."""
        return self.definition_node.range


class TreeSitterParser:
    """Tree-sitter based syntax parser."""
    
    def __init__(self, config: Config):
        self.config = config
        self.parsers: Dict[str, Parser] = {}
        self.languages: Dict[str, Language] = {}
        self.logger = logging.getLogger("tree_sitter")
        
        if not TREE_SITTER_AVAILABLE:
            self.logger.warning("Tree-sitter not available. Install with: pip install tree-sitter")
            return
        
        self._load_languages()
    
    def _load_languages(self) -> None:
        """Load tree-sitter languages."""
        if not TREE_SITTER_AVAILABLE:
            return
        
        # Language configurations
        language_configs = {
            "python": {
                "extensions": [".py"],
                "library_name": "python"
            },
            "javascript": {
                "extensions": [".js", ".jsx"],
                "library_name": "javascript"
            },
            "typescript": {
                "extensions": [".ts", ".tsx"],
                "library_name": "typescript"
            },
            "rust": {
                "extensions": [".rs"],
                "library_name": "rust"
            },
            "go": {
                "extensions": [".go"],
                "library_name": "go"
            },
            "java": {
                "extensions": [".java"],
                "library_name": "java"
            },
            "cpp": {
                "extensions": [".cpp", ".cxx", ".cc", ".c", ".h", ".hpp"],
                "library_name": "cpp"
            },
            "c": {
                "extensions": [".c", ".h"],
                "library_name": "c"
            }
        }
        
        # Try to load each language
        for lang_name, config in language_configs.items():
            try:
                # This would normally load from compiled language libraries
                # For now, we'll create a mock implementation
                self.languages[lang_name] = self._create_mock_language(lang_name)
                parser = Parser()
                parser.set_language(self.languages[lang_name])
                self.parsers[lang_name] = parser
                
            except Exception as e:
                self.logger.debug(f"Could not load tree-sitter language {lang_name}: {e}")
    
    def _create_mock_language(self, lang_name: str) -> Language:
        """Create a mock language for testing when tree-sitter libraries aren't available."""
        # This is a placeholder - in a real implementation, you would load
        # the compiled tree-sitter language libraries
        return Language(None, lang_name)
    
    def get_language_for_file(self, file_path: Path) -> Optional[str]:
        """Get the language for a file based on its extension."""
        extension = file_path.suffix.lower()
        
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript", 
            ".ts": "typescript",
            ".tsx": "typescript",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".cpp": "cpp",
            ".cxx": "cpp",
            ".cc": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp"
        }
        
        return language_map.get(extension)
    
    def parse_file(self, file_path: Path) -> Optional[SyntaxNode]:
        """Parse a file and return the syntax tree."""
        if not TREE_SITTER_AVAILABLE:
            return self._fallback_parse(file_path)
        
        language = self.get_language_for_file(file_path)
        if not language or language not in self.parsers:
            return self._fallback_parse(file_path)
        
        try:
            content = file_path.read_text(encoding='utf-8')
            return self.parse_content(content, language)
        except Exception as e:
            self.logger.error(f"Error parsing file {file_path}: {e}")
            return self._fallback_parse(file_path)
    
    def parse_content(self, content: str, language: str) -> Optional[SyntaxNode]:
        """Parse content string and return the syntax tree."""
        if not TREE_SITTER_AVAILABLE or language not in self.parsers:
            return self._fallback_parse_content(content, language)
        
        try:
            parser = self.parsers[language]
            tree = parser.parse(bytes(content, 'utf-8'))
            return self._convert_tree_sitter_node(tree.root_node, content)
        except Exception as e:
            self.logger.error(f"Error parsing content: {e}")
            return self._fallback_parse_content(content, language)
    
    def _convert_tree_sitter_node(self, ts_node: Node, content: str) -> SyntaxNode:
        """Convert a tree-sitter node to our SyntaxNode format."""
        lines = content.split('\n')
        
        # Get node text
        start_byte = ts_node.start_byte
        end_byte = ts_node.end_byte
        node_text = content[start_byte:end_byte]
        
        # Create our syntax node
        syntax_node = SyntaxNode(
            type=ts_node.type,
            text=node_text,
            start_line=ts_node.start_point[0],
            start_column=ts_node.start_point[1],
            end_line=ts_node.end_point[0],
            end_column=ts_node.end_point[1]
        )
        
        # Convert children
        for child in ts_node.children:
            child_node = self._convert_tree_sitter_node(child, content)
            child_node.parent = syntax_node
            syntax_node.children.append(child_node)
        
        return syntax_node
    
    def _fallback_parse(self, file_path: Path) -> Optional[SyntaxNode]:
        """Fallback parsing when tree-sitter is not available."""
        try:
            content = file_path.read_text(encoding='utf-8')
            language = self.get_language_for_file(file_path)
            return self._fallback_parse_content(content, language or "text")
        except Exception as e:
            self.logger.error(f"Error in fallback parsing: {e}")
            return None
    
    def _fallback_parse_content(self, content: str, language: str) -> SyntaxNode:
        """Simple regex-based fallback parsing."""
        lines = content.split('\n')
        
        # Create root node
        root = SyntaxNode(
            type="module",
            text=content,
            start_line=0,
            start_column=0,
            end_line=len(lines) - 1,
            end_column=len(lines[-1]) if lines else 0
        )
        
        # Language-specific simple parsing
        if language == "python":
            self._parse_python_fallback(content, root)
        elif language in ["javascript", "typescript"]:
            self._parse_javascript_fallback(content, root)
        elif language == "rust":
            self._parse_rust_fallback(content, root)
        elif language == "go":
            self._parse_go_fallback(content, root)
        elif language == "java":
            self._parse_java_fallback(content, root)
        elif language in ["cpp", "c"]:
            self._parse_cpp_fallback(content, root)
        
        return root
    
    def _parse_python_fallback(self, content: str, root: SyntaxNode) -> None:
        """Simple Python parsing using regex."""
        lines = content.split('\n')
        
        # Find classes
        class_pattern = re.compile(r'^(\s*)class\s+(\w+).*?:', re.MULTILINE)
        for match in class_pattern.finditer(content):
            start_line = content[:match.start()].count('\n')
            indent = len(match.group(1))
            class_name = match.group(2)
            
            # Find end of class (next class/function at same or lower indent level)
            end_line = self._find_block_end(lines, start_line, indent)
            
            class_node = SyntaxNode(
                type="class_definition",
                text='\n'.join(lines[start_line:end_line + 1]),
                start_line=start_line,
                start_column=indent,
                end_line=end_line,
                end_column=len(lines[end_line]) if end_line < len(lines) else 0,
                parent=root
            )
            root.children.append(class_node)
        
        # Find functions
        func_pattern = re.compile(r'^(\s*)def\s+(\w+).*?:', re.MULTILINE)
        for match in func_pattern.finditer(content):
            start_line = content[:match.start()].count('\n')
            indent = len(match.group(1))
            func_name = match.group(2)
            
            # Find end of function
            end_line = self._find_block_end(lines, start_line, indent)
            
            func_node = SyntaxNode(
                type="function_definition",
                text='\n'.join(lines[start_line:end_line + 1]),
                start_line=start_line,
                start_column=indent,
                end_line=end_line,
                end_column=len(lines[end_line]) if end_line < len(lines) else 0,
                parent=root
            )
            root.children.append(func_node)
    
    def _parse_javascript_fallback(self, content: str, root: SyntaxNode) -> None:
        """Simple JavaScript/TypeScript parsing using regex."""
        lines = content.split('\n')
        
        # Find functions
        func_patterns = [
            re.compile(r'function\s+(\w+)\s*\(.*?\)\s*\{', re.MULTILINE),
            re.compile(r'(\w+)\s*:\s*function\s*\(.*?\)\s*\{', re.MULTILINE),
            re.compile(r'(\w+)\s*=\s*\(.*?\)\s*=>\s*\{', re.MULTILINE),
            re.compile(r'const\s+(\w+)\s*=\s*\(.*?\)\s*=>\s*\{', re.MULTILINE)
        ]
        
        for pattern in func_patterns:
            for match in pattern.finditer(content):
                start_line = content[:match.start()].count('\n')
                func_name = match.group(1)
                
                # Find matching closing brace
                end_line = self._find_brace_end(lines, start_line)
                
                func_node = SyntaxNode(
                    type="function_declaration",
                    text='\n'.join(lines[start_line:end_line + 1]),
                    start_line=start_line,
                    start_column=0,
                    end_line=end_line,
                    end_column=len(lines[end_line]) if end_line < len(lines) else 0,
                    parent=root
                )
                root.children.append(func_node)
        
        # Find classes
        class_pattern = re.compile(r'class\s+(\w+).*?\{', re.MULTILINE)
        for match in class_pattern.finditer(content):
            start_line = content[:match.start()].count('\n')
            class_name = match.group(1)
            
            end_line = self._find_brace_end(lines, start_line)
            
            class_node = SyntaxNode(
                type="class_declaration",
                text='\n'.join(lines[start_line:end_line + 1]),
                start_line=start_line,
                start_column=0,
                end_line=end_line,
                end_column=len(lines[end_line]) if end_line < len(lines) else 0,
                parent=root
            )
            root.children.append(class_node)
    
    def _parse_rust_fallback(self, content: str, root: SyntaxNode) -> None:
        """Simple Rust parsing using regex."""
        lines = content.split('\n')
        
        # Find functions
        func_pattern = re.compile(r'fn\s+(\w+)\s*\(.*?\)\s*.*?\{', re.MULTILINE)
        for match in func_pattern.finditer(content):
            start_line = content[:match.start()].count('\n')
            func_name = match.group(1)
            
            end_line = self._find_brace_end(lines, start_line)
            
            func_node = SyntaxNode(
                type="function_item",
                text='\n'.join(lines[start_line:end_line + 1]),
                start_line=start_line,
                start_column=0,
                end_line=end_line,
                end_column=len(lines[end_line]) if end_line < len(lines) else 0,
                parent=root
            )
            root.children.append(func_node)
        
        # Find structs
        struct_pattern = re.compile(r'struct\s+(\w+).*?\{', re.MULTILINE)
        for match in struct_pattern.finditer(content):
            start_line = content[:match.start()].count('\n')
            struct_name = match.group(1)
            
            end_line = self._find_brace_end(lines, start_line)
            
            struct_node = SyntaxNode(
                type="struct_item",
                text='\n'.join(lines[start_line:end_line + 1]),
                start_line=start_line,
                start_column=0,
                end_line=end_line,
                end_column=len(lines[end_line]) if end_line < len(lines) else 0,
                parent=root
            )
            root.children.append(struct_node)
    
    def _parse_go_fallback(self, content: str, root: SyntaxNode) -> None:
        """Simple Go parsing using regex."""
        lines = content.split('\n')
        
        # Find functions
        func_pattern = re.compile(r'func\s+(\w+)\s*\(.*?\).*?\{', re.MULTILINE)
        for match in func_pattern.finditer(content):
            start_line = content[:match.start()].count('\n')
            func_name = match.group(1)
            
            end_line = self._find_brace_end(lines, start_line)
            
            func_node = SyntaxNode(
                type="function_declaration",
                text='\n'.join(lines[start_line:end_line + 1]),
                start_line=start_line,
                start_column=0,
                end_line=end_line,
                end_column=len(lines[end_line]) if end_line < len(lines) else 0,
                parent=root
            )
            root.children.append(func_node)
        
        # Find structs
        struct_pattern = re.compile(r'type\s+(\w+)\s+struct\s*\{', re.MULTILINE)
        for match in struct_pattern.finditer(content):
            start_line = content[:match.start()].count('\n')
            struct_name = match.group(1)
            
            end_line = self._find_brace_end(lines, start_line)
            
            struct_node = SyntaxNode(
                type="type_declaration",
                text='\n'.join(lines[start_line:end_line + 1]),
                start_line=start_line,
                start_column=0,
                end_line=end_line,
                end_column=len(lines[end_line]) if end_line < len(lines) else 0,
                parent=root
            )
            root.children.append(struct_node)
    
    def _parse_java_fallback(self, content: str, root: SyntaxNode) -> None:
        """Simple Java parsing using regex."""
        lines = content.split('\n')
        
        # Find classes
        class_pattern = re.compile(r'class\s+(\w+).*?\{', re.MULTILINE)
        for match in class_pattern.finditer(content):
            start_line = content[:match.start()].count('\n')
            class_name = match.group(1)
            
            end_line = self._find_brace_end(lines, start_line)
            
            class_node = SyntaxNode(
                type="class_declaration",
                text='\n'.join(lines[start_line:end_line + 1]),
                start_line=start_line,
                start_column=0,
                end_line=end_line,
                end_column=len(lines[end_line]) if end_line < len(lines) else 0,
                parent=root
            )
            root.children.append(class_node)
        
        # Find methods
        method_pattern = re.compile(r'(public|private|protected)?\s*(static)?\s*\w+\s+(\w+)\s*\(.*?\)\s*\{', re.MULTILINE)
        for match in method_pattern.finditer(content):
            start_line = content[:match.start()].count('\n')
            method_name = match.group(3)
            
            end_line = self._find_brace_end(lines, start_line)
            
            method_node = SyntaxNode(
                type="method_declaration",
                text='\n'.join(lines[start_line:end_line + 1]),
                start_line=start_line,
                start_column=0,
                end_line=end_line,
                end_column=len(lines[end_line]) if end_line < len(lines) else 0,
                parent=root
            )
            root.children.append(method_node)
    
    def _parse_cpp_fallback(self, content: str, root: SyntaxNode) -> None:
        """Simple C/C++ parsing using regex."""
        lines = content.split('\n')
        
        # Find functions
        func_pattern = re.compile(r'\w+\s+(\w+)\s*\(.*?\)\s*\{', re.MULTILINE)
        for match in func_pattern.finditer(content):
            start_line = content[:match.start()].count('\n')
            func_name = match.group(1)
            
            # Skip if it looks like a control structure
            if func_name in ['if', 'for', 'while', 'switch']:
                continue
            
            end_line = self._find_brace_end(lines, start_line)
            
            func_node = SyntaxNode(
                type="function_definition",
                text='\n'.join(lines[start_line:end_line + 1]),
                start_line=start_line,
                start_column=0,
                end_line=end_line,
                end_column=len(lines[end_line]) if end_line < len(lines) else 0,
                parent=root
            )
            root.children.append(func_node)
        
        # Find classes/structs
        class_pattern = re.compile(r'(class|struct)\s+(\w+).*?\{', re.MULTILINE)
        for match in class_pattern.finditer(content):
            start_line = content[:match.start()].count('\n')
            class_name = match.group(2)
            
            end_line = self._find_brace_end(lines, start_line)
            
            class_node = SyntaxNode(
                type=f"{match.group(1)}_specifier",
                text='\n'.join(lines[start_line:end_line + 1]),
                start_line=start_line,
                start_column=0,
                end_line=end_line,
                end_column=len(lines[end_line]) if end_line < len(lines) else 0,
                parent=root
            )
            root.children.append(class_node)
    
    def _find_block_end(self, lines: List[str], start_line: int, base_indent: int) -> int:
        """Find the end of a Python block based on indentation."""
        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            if line.strip() == "":
                continue
            
            # Calculate indentation
            indent = len(line) - len(line.lstrip())
            
            # If we find a line with same or less indentation, we've found the end
            if indent <= base_indent:
                return i - 1
        
        return len(lines) - 1
    
    def _find_brace_end(self, lines: List[str], start_line: int) -> int:
        """Find the matching closing brace."""
        brace_count = 0
        found_opening = False
        
        for i in range(start_line, len(lines)):
            line = lines[i]
            for char in line:
                if char == '{':
                    brace_count += 1
                    found_opening = True
                elif char == '}':
                    brace_count -= 1
                    if found_opening and brace_count == 0:
                        return i
        
        return len(lines) - 1
    
    def extract_symbols(self, syntax_tree: SyntaxNode) -> List[SymbolInfo]:
        """Extract symbol information from a syntax tree."""
        symbols = []
        
        # Define symbol types for different node types
        symbol_types = {
            'function_definition': 'function',
            'function_declaration': 'function',
            'function_item': 'function',
            'method_definition': 'method',
            'method_declaration': 'method',
            'class_definition': 'class',
            'class_declaration': 'class',
            'struct_item': 'struct',
            'struct_specifier': 'struct',
            'type_declaration': 'type',
            'variable_declaration': 'variable',
            'identifier': 'variable'
        }
        
        def extract_from_node(node: SyntaxNode) -> None:
            if node.type in symbol_types:
                # Extract symbol name from the node text
                name = self._extract_symbol_name(node)
                if name:
                    symbol = SymbolInfo(
                        name=name,
                        type=symbol_types[node.type],
                        definition_node=node,
                        scope=node.get_scope()
                    )
                    symbols.append(symbol)
            
            # Recursively process children
            for child in node.children:
                extract_from_node(child)
        
        extract_from_node(syntax_tree)
        return symbols
    
    def _extract_symbol_name(self, node: SyntaxNode) -> Optional[str]:
        """Extract the symbol name from a node."""
        text = node.text.strip()
        
        # Simple regex patterns for different languages
        patterns = [
            r'def\s+(\w+)',  # Python function
            r'class\s+(\w+)',  # Python/Java/C++ class
            r'function\s+(\w+)',  # JavaScript function
            r'fn\s+(\w+)',  # Rust function
            r'func\s+(\w+)',  # Go function
            r'struct\s+(\w+)',  # C/C++/Rust struct
            r'type\s+(\w+)',  # Go type
            r'\w+\s+(\w+)\s*\(',  # Generic function pattern
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def find_node_at_position(self, syntax_tree: SyntaxNode, line: int, column: int) -> Optional[SyntaxNode]:
        """Find the syntax node at a specific position."""
        return syntax_tree.find_child_at_position(line, column)
    
    def get_context_for_position(self, syntax_tree: SyntaxNode, line: int, column: int) -> Dict[str, Any]:
        """Get contextual information for a position in the code."""
        node = self.find_node_at_position(syntax_tree, line, column)
        if not node:
            return {}
        
        context = {
            'node_type': node.type,
            'node_text': node.text[:100] + '...' if len(node.text) > 100 else node.text,
            'scope': None,
            'ancestors': []
        }
        
        # Get scope information
        scope = node.get_scope()
        if scope:
            context['scope'] = {
                'type': scope.type,
                'name': self._extract_symbol_name(scope),
                'range': scope.range
            }
        
        # Get ancestor information
        ancestors = node.get_ancestors()
        context['ancestors'] = [
            {
                'type': ancestor.type,
                'name': self._extract_symbol_name(ancestor),
                'range': ancestor.range
            }
            for ancestor in ancestors[:5]  # Limit to 5 ancestors
        ]
        
        return context