from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import pytest

from term_coder.config import Config
from term_coder.tree_sitter import TreeSitterParser, SyntaxNode, SymbolInfo
from term_coder.lsp import LSPManager, LSPClient, LSPDiagnostic, LSPPosition, LSPRange
from term_coder.language_aware import LanguageAwareContextEngine, LanguageContext, FrameworkInfo
from term_coder.framework_commands import FrameworkCommandRegistry, FrameworkCommandExtensions


class TestTreeSitterParser:
    """Test tree-sitter parser functionality."""
    
    def test_parser_initialization(self):
        """Test parser initialization."""
        config = Config()
        parser = TreeSitterParser(config)
        
        assert parser.config == config
        assert isinstance(parser.parsers, dict)
        assert isinstance(parser.languages, dict)
    
    def test_get_language_for_file(self):
        """Test language detection for files."""
        config = Config()
        parser = TreeSitterParser(config)
        
        # Test Python files
        assert parser.get_language_for_file(Path("test.py")) == "python"
        assert parser.get_language_for_file(Path("script.py")) == "python"
        
        # Test JavaScript files
        assert parser.get_language_for_file(Path("app.js")) == "javascript"
        assert parser.get_language_for_file(Path("component.jsx")) == "javascript"
        
        # Test TypeScript files
        assert parser.get_language_for_file(Path("app.ts")) == "typescript"
        assert parser.get_language_for_file(Path("component.tsx")) == "typescript"
        
        # Test other languages
        assert parser.get_language_for_file(Path("main.rs")) == "rust"
        assert parser.get_language_for_file(Path("main.go")) == "go"
        assert parser.get_language_for_file(Path("Main.java")) == "java"
        
        # Test unknown extension
        assert parser.get_language_for_file(Path("unknown.xyz")) is None
    
    def test_fallback_python_parsing(self):
        """Test fallback Python parsing."""
        config = Config()
        parser = TreeSitterParser(config)
        
        python_code = '''
class TestClass:
    def __init__(self):
        self.value = 42
    
    def test_method(self):
        return self.value

def standalone_function():
    return "hello"
'''
        
        syntax_tree = parser._fallback_parse_content(python_code, "python")
        
        assert syntax_tree is not None
        assert syntax_tree.type == "module"
        assert len(syntax_tree.children) >= 2  # Should find class and function
        
        # Check for class definition
        class_nodes = [child for child in syntax_tree.children if child.type == "class_definition"]
        assert len(class_nodes) >= 1
        
        # Check for function definition
        func_nodes = [child for child in syntax_tree.children if child.type == "function_definition"]
        assert len(func_nodes) >= 1 
   
    def test_fallback_javascript_parsing(self):
        """Test fallback JavaScript parsing."""
        config = Config()
        parser = TreeSitterParser(config)
        
        js_code = '''
function testFunction() {
    return "hello";
}

class TestClass {
    constructor() {
        this.value = 42;
    }
    
    testMethod() {
        return this.value;
    }
}

const arrowFunction = () => {
    return "arrow";
};
'''
        
        syntax_tree = parser._fallback_parse_content(js_code, "javascript")
        
        assert syntax_tree is not None
        assert syntax_tree.type == "module"
        assert len(syntax_tree.children) >= 2  # Should find functions and class
    
    def test_symbol_extraction(self):
        """Test symbol extraction from syntax tree."""
        config = Config()
        parser = TreeSitterParser(config)
        
        # Create a simple syntax tree
        root = SyntaxNode(
            type="module",
            text="test content",
            start_line=0,
            start_column=0,
            end_line=10,
            end_column=0
        )
        
        func_node = SyntaxNode(
            type="function_definition",
            text="def test_func():\n    pass",
            start_line=1,
            start_column=0,
            end_line=2,
            end_column=8,
            parent=root
        )
        root.children.append(func_node)
        
        symbols = parser.extract_symbols(root)
        
        assert len(symbols) >= 1
        assert any(symbol.type == "function" for symbol in symbols)
    
    def test_find_node_at_position(self):
        """Test finding node at specific position."""
        config = Config()
        parser = TreeSitterParser(config)
        
        # Create nested syntax tree
        root = SyntaxNode(
            type="module",
            text="test content",
            start_line=0,
            start_column=0,
            end_line=10,
            end_column=0
        )
        
        child = SyntaxNode(
            type="function_definition",
            text="def test():\n    pass",
            start_line=2,
            start_column=0,
            end_line=3,
            end_column=8,
            parent=root
        )
        root.children.append(child)
        
        # Test finding node at position
        found_node = parser.find_node_at_position(root, 2, 5)
        assert found_node == child
        
        # Test position outside any node
        found_node = parser.find_node_at_position(root, 20, 0)
        assert found_node is None


class TestSyntaxNode:
    """Test SyntaxNode functionality."""
    
    def test_syntax_node_creation(self):
        """Test syntax node creation."""
        node = SyntaxNode(
            type="function_definition",
            text="def test(): pass",
            start_line=1,
            start_column=0,
            end_line=1,
            end_column=16
        )
        
        assert node.type == "function_definition"
        assert node.text == "def test(): pass"
        assert node.range == (1, 0, 1, 16)
    
    def test_contains_position(self):
        """Test position containment check."""
        node = SyntaxNode(
            type="function_definition",
            text="def test(): pass",
            start_line=1,
            start_column=0,
            end_line=3,
            end_column=10
        )
        
        # Test positions inside
        assert node.contains_position(1, 5)
        assert node.contains_position(2, 0)
        assert node.contains_position(3, 5)
        
        # Test positions outside
        assert not node.contains_position(0, 5)
        assert not node.contains_position(4, 0)
        assert not node.contains_position(1, -1)
        assert not node.contains_position(3, 15)
    
    def test_find_child_at_position(self):
        """Test finding child at position."""
        parent = SyntaxNode(
            type="class_definition",
            text="class Test:\n    def method(self): pass",
            start_line=0,
            start_column=0,
            end_line=1,
            end_column=26
        )
        
        child = SyntaxNode(
            type="function_definition",
            text="def method(self): pass",
            start_line=1,
            start_column=4,
            end_line=1,
            end_column=26,
            parent=parent
        )
        parent.children.append(child)
        
        # Should find the child
        found = parent.find_child_at_position(1, 10)
        assert found == child
        
        # Should find parent if no child matches
        found = parent.find_child_at_position(0, 5)
        assert found == parent
    
    def test_find_nodes_by_type(self):
        """Test finding nodes by type."""
        root = SyntaxNode(
            type="module",
            text="module content",
            start_line=0,
            start_column=0,
            end_line=10,
            end_column=0
        )
        
        func1 = SyntaxNode(
            type="function_definition",
            text="def func1(): pass",
            start_line=1,
            start_column=0,
            end_line=1,
            end_column=17,
            parent=root
        )
        
        func2 = SyntaxNode(
            type="function_definition",
            text="def func2(): pass",
            start_line=3,
            start_column=0,
            end_line=3,
            end_column=17,
            parent=root
        )
        
        class_node = SyntaxNode(
            type="class_definition",
            text="class Test: pass",
            start_line=5,
            start_column=0,
            end_line=5,
            end_column=16,
            parent=root
        )
        
        root.children.extend([func1, func2, class_node])
        
        # Find all function definitions
        functions = root.find_nodes_by_type("function_definition")
        assert len(functions) == 2
        assert func1 in functions
        assert func2 in functions
        
        # Find class definitions
        classes = root.find_nodes_by_type("class_definition")
        assert len(classes) == 1
        assert class_node in classes


class TestLSPIntegration:
    """Test LSP integration functionality."""
    
    @pytest.mark.asyncio
    async def test_lsp_manager_initialization(self):
        """Test LSP manager initialization."""
        config = Config()
        root_path = Path("/tmp/test")
        
        manager = LSPManager(config, root_path)
        
        assert manager.config == config
        assert manager.root_path == root_path
        assert isinstance(manager.clients, dict)
        assert isinstance(manager.server_configs, dict)
    
    def test_get_language_for_file(self):
        """Test language detection for LSP."""
        config = Config()
        root_path = Path("/tmp/test")
        manager = LSPManager(config, root_path)
        
        assert manager.get_language_for_file(Path("test.py")) == "python"
        assert manager.get_language_for_file(Path("app.js")) == "javascript"
        assert manager.get_language_for_file(Path("main.rs")) == "rust"
        assert manager.get_language_for_file(Path("unknown.xyz")) is None
    
    def test_is_supported(self):
        """Test file support checking."""
        config = Config()
        root_path = Path("/tmp/test")
        manager = LSPManager(config, root_path)
        
        assert manager.is_supported(Path("test.py"))
        assert manager.is_supported(Path("app.js"))
        assert not manager.is_supported(Path("unknown.xyz"))


class TestLanguageAwareContextEngine:
    """Test language-aware context engine."""
    
    def test_initialization(self):
        """Test context engine initialization."""
        config = Config()
        root_path = Path("/tmp/test")
        
        engine = LanguageAwareContextEngine(config, root_path)
        
        assert engine.config == config
        assert engine.root_path == root_path
        assert isinstance(engine.detected_frameworks, dict)
        assert isinstance(engine.language_configs, dict)
    
    def test_language_configs_loading(self):
        """Test language configuration loading."""
        config = Config()
        root_path = Path("/tmp/test")
        
        engine = LanguageAwareContextEngine(config, root_path)
        
        # Check that default configs are loaded
        assert "python" in engine.language_configs
        assert "javascript" in engine.language_configs
        assert "typescript" in engine.language_configs
        
        # Check Python config structure
        python_config = engine.language_configs["python"]
        assert "import_patterns" in python_config
        assert "test_patterns" in python_config
        assert "framework_indicators" in python_config
    
    @pytest.mark.asyncio
    async def test_analyze_file_nonexistent(self):
        """Test analyzing non-existent file."""
        config = Config()
        root_path = Path("/tmp/test")
        
        engine = LanguageAwareContextEngine(config, root_path)
        
        result = await engine.analyze_file(Path("/nonexistent/file.py"))
        assert result is None
    
    def test_extract_imports_python(self):
        """Test Python import extraction."""
        config = Config()
        root_path = Path("/tmp/test")
        
        engine = LanguageAwareContextEngine(config, root_path)
        
        python_code = '''
import os
import sys
from pathlib import Path
from typing import List, Dict
'''
        
        imports = engine._extract_imports(python_code, "python")
        
        # Should find some imports (exact matching depends on regex patterns)
        assert len(imports) >= 2
        assert any("os" in imp for imp in imports)
        assert any("pathlib" in imp for imp in imports)
    
    def test_extract_imports_javascript(self):
        """Test JavaScript import extraction."""
        config = Config()
        root_path = Path("/tmp/test")
        
        engine = LanguageAwareContextEngine(config, root_path)
        
        js_code = '''
import React from 'react';
import { useState } from 'react';
const fs = require('fs');
'''
        
        imports = engine._extract_imports(js_code, "javascript")
        
        # Should find imports
        assert len(imports) >= 1
        assert any("react" in imp for imp in imports)


class TestFrameworkDetection:
    """Test framework detection functionality."""
    
    def test_django_detection(self, tmp_path):
        """Test Django framework detection."""
        config = Config()
        
        # Create Django project structure
        manage_py = tmp_path / "manage.py"
        manage_py.write_text("#!/usr/bin/env python\n# Django manage.py")
        
        settings_dir = tmp_path / "myproject"
        settings_dir.mkdir()
        settings_py = settings_dir / "settings.py"
        settings_py.write_text("# Django settings")
        
        engine = LanguageAwareContextEngine(config, tmp_path)
        
        # Should detect Django
        assert "django" in engine.detected_frameworks
        django_info = engine.detected_frameworks["django"]
        assert django_info.name == "django"
        assert manage_py in django_info.config_files
    
    def test_react_detection(self, tmp_path):
        """Test React framework detection."""
        config = Config()
        
        # Create React project structure
        package_json = tmp_path / "package.json"
        package_json.write_text('''
{
  "name": "my-react-app",
  "dependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  }
}
''')
        
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        index_js = src_dir / "index.js"
        index_js.write_text("import React from 'react';")
        
        engine = LanguageAwareContextEngine(config, tmp_path)
        
        # Should detect React
        assert "react" in engine.detected_frameworks
        react_info = engine.detected_frameworks["react"]
        assert react_info.name == "react"
        assert react_info.version == "^18.0.0"
    
    def test_no_framework_detection(self, tmp_path):
        """Test when no frameworks are detected."""
        config = Config()
        
        # Create empty directory
        engine = LanguageAwareContextEngine(config, tmp_path)
        
        # Should not detect any frameworks
        assert len(engine.detected_frameworks) == 0


class TestFrameworkCommands:
    """Test framework command functionality."""
    
    def test_command_registry_initialization(self):
        """Test command registry initialization."""
        config = Config()
        root_path = Path("/tmp/test")
        
        engine = LanguageAwareContextEngine(config, root_path)
        registry = FrameworkCommandRegistry(config, engine)
        
        assert isinstance(registry.commands, dict)
        assert "django" in registry.commands
        assert "react" in registry.commands
        assert "rust_web" in registry.commands
    
    def test_get_django_commands(self):
        """Test getting Django commands."""
        config = Config()
        root_path = Path("/tmp/test")
        
        engine = LanguageAwareContextEngine(config, root_path)
        registry = FrameworkCommandRegistry(config, engine)
        
        django_commands = registry.get_available_commands("django")
        
        assert "runserver" in django_commands
        assert "migrate" in django_commands
        assert "test" in django_commands
        
        runserver_cmd = django_commands["runserver"]
        assert runserver_cmd.name == "runserver"
        assert "manage.py" in runserver_cmd.requires_files
    
    def test_can_execute_command(self, tmp_path):
        """Test command execution validation."""
        config = Config()
        
        engine = LanguageAwareContextEngine(config, tmp_path)
        registry = FrameworkCommandRegistry(config, engine)
        
        # Should not be able to execute Django commands without manage.py
        assert not registry.can_execute_command("django", "runserver", tmp_path)
        
        # Create manage.py
        manage_py = tmp_path / "manage.py"
        manage_py.write_text("#!/usr/bin/env python")
        
        # Now should be able to execute
        assert registry.can_execute_command("django", "runserver", tmp_path)
    
    def test_framework_extensions_initialization(self):
        """Test framework extensions initialization."""
        config = Config()
        root_path = Path("/tmp/test")
        
        extensions = FrameworkCommandExtensions(config, root_path)
        
        assert extensions.config == config
        assert extensions.root_path == root_path
        assert isinstance(extensions.language_engine, LanguageAwareContextEngine)
        assert isinstance(extensions.command_registry, FrameworkCommandRegistry)
    
    def test_suggest_commands_for_context(self, tmp_path):
        """Test command suggestions based on context."""
        config = Config()
        
        # Create Django project
        manage_py = tmp_path / "manage.py"
        manage_py.write_text("#!/usr/bin/env python")
        
        extensions = FrameworkCommandExtensions(config, tmp_path)
        
        suggestions = extensions.suggest_commands_for_context()
        
        # Should suggest Django commands
        django_suggestions = [s for s in suggestions if s[0] == "django"]
        assert len(django_suggestions) > 0
        
        # Check that runserver is suggested
        runserver_suggestions = [s for s in django_suggestions if s[1] == "runserver"]
        assert len(runserver_suggestions) == 1


class TestCodeGeneration:
    """Test framework-specific code generation."""
    
    def test_django_model_generation(self):
        """Test Django model code generation."""
        config = Config()
        root_path = Path("/tmp/test")
        
        extensions = FrameworkCommandExtensions(config, root_path)
        
        code = extensions.generate_framework_specific_code("django", "model", "User")
        
        assert code is not None
        assert "class User(models.Model)" in code
        assert "created_at" in code
        assert "updated_at" in code
    
    def test_react_component_generation(self):
        """Test React component code generation."""
        config = Config()
        root_path = Path("/tmp/test")
        
        extensions = FrameworkCommandExtensions(config, root_path)
        
        code = extensions.generate_framework_specific_code("react", "component", "UserProfile")
        
        assert code is not None
        assert "const UserProfile" in code
        assert "React.FC" in code
        assert "export default UserProfile" in code
    
    def test_fastapi_router_generation(self):
        """Test FastAPI router code generation."""
        config = Config()
        root_path = Path("/tmp/test")
        
        extensions = FrameworkCommandExtensions(config, root_path)
        
        code = extensions.generate_framework_specific_code("fastapi", "router", "User")
        
        assert code is not None
        assert "APIRouter" in code
        assert "UserCreate" in code
        assert "UserResponse" in code
    
    def test_unknown_framework_generation(self):
        """Test code generation for unknown framework."""
        config = Config()
        root_path = Path("/tmp/test")
        
        extensions = FrameworkCommandExtensions(config, root_path)
        
        code = extensions.generate_framework_specific_code("unknown", "component", "Test")
        
        assert code is None


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_python_analysis(self, tmp_path):
        """Test full analysis of a Python file."""
        config = Config()
        
        # Create a Python file
        python_file = tmp_path / "test_module.py"
        python_file.write_text('''
import os
from pathlib import Path

class TestClass:
    """A test class."""
    
    def __init__(self, name: str):
        self.name = name
    
    def get_name(self) -> str:
        return self.name

def utility_function(value: int) -> int:
    """A utility function."""
    return value * 2

if __name__ == "__main__":
    test = TestClass("example")
    print(test.get_name())
''')
        
        engine = LanguageAwareContextEngine(config, tmp_path)
        
        # Analyze the file
        context = await engine.analyze_file(python_file)
        
        assert context is not None
        assert context.language == "python"
        assert context.file_path == python_file
        assert len(context.content) > 0
        
        # Should have extracted imports
        assert len(context.imports) >= 1
        assert any("os" in imp for imp in context.imports)
        
        # Should have parsed syntax tree
        assert context.syntax_tree is not None
        assert context.syntax_tree.type == "module"
        
        # Should have extracted symbols
        assert len(context.symbols) >= 2  # Class and function
        symbol_types = [s.type for s in context.symbols]
        assert "class" in symbol_types
        assert "function" in symbol_types
    
    def test_framework_context_integration(self, tmp_path):
        """Test framework context integration."""
        config = Config()
        
        # Create Django project structure
        manage_py = tmp_path / "manage.py"
        manage_py.write_text("#!/usr/bin/env python")
        
        app_dir = tmp_path / "myapp"
        app_dir.mkdir()
        
        models_py = app_dir / "models.py"
        models_py.write_text('''
from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
''')
        
        extensions = FrameworkCommandExtensions(config, tmp_path)
        
        # Get framework-specific context
        context = extensions.get_framework_specific_context(models_py)
        
        assert context["framework"] == "django"
        assert context["pattern_type"] == "models"
        assert len(context["available_commands"]) > 0
        assert "runserver" in context["available_commands"]
    
    @pytest.mark.asyncio
    async def test_related_files_detection(self, tmp_path):
        """Test detection of related files."""
        config = Config()
        
        # Create Python module with imports
        main_py = tmp_path / "main.py"
        main_py.write_text('''
from utils import helper_function
from models import User

def main():
    user = User("test")
    result = helper_function(user.name)
    print(result)
''')
        
        utils_py = tmp_path / "utils.py"
        utils_py.write_text('''
def helper_function(name: str) -> str:
    return f"Hello, {name}!"
''')
        
        models_py = tmp_path / "models.py"
        models_py.write_text('''
class User:
    def __init__(self, name: str):
        self.name = name
''')
        
        engine = LanguageAwareContextEngine(config, tmp_path)
        
        # Get related files
        related = engine.get_related_files(main_py)
        
        # Should find the imported modules
        related_paths = [str(f) for f in related]
        assert any("utils.py" in path for path in related_paths)
        assert any("models.py" in path for path in related_paths)