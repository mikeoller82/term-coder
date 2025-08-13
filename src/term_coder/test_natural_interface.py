from __future__ import annotations

import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from term_coder.natural_interface import NaturalLanguageInterface, IntentType, Intent
from term_coder.config import Config


class TestNaturalLanguageInterface:
    """Test the natural language interface."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        config = Mock(spec=Config)
        config.get.return_value = "openai:gpt-4o-mini"
        return config
    
    @pytest.fixture
    def mock_console(self):
        """Mock console."""
        console = Mock()
        console.print = Mock()
        return console
    
    @pytest.fixture
    def natural_interface(self, mock_config, mock_console):
        """Create natural language interface with mocked dependencies."""
        with patch('term_coder.natural_interface.LLMOrchestrator'), \
             patch('term_coder.natural_interface.HybridSearch'), \
             patch('term_coder.natural_interface.ContextEngine'):
            
            interface = NaturalLanguageInterface(mock_config, mock_console)
            return interface
    
    def test_intent_pattern_matching(self, natural_interface):
        """Test intent pattern matching."""
        # Test debug intent
        intent = natural_interface._parse_intent("debug for errors")
        assert intent.type == IntentType.DEBUG
        assert intent.confidence > 0.6
        
        # Test search intent
        intent = natural_interface._parse_intent("find all TODO comments")
        assert intent.type == IntentType.SEARCH
        assert intent.confidence > 0.6
        
        # Test fix intent
        intent = natural_interface._parse_intent("fix the authentication bug")
        assert intent.type == IntentType.FIX
        assert intent.confidence > 0.6
        
        # Test explain intent
        intent = natural_interface._parse_intent("explain how the login works")
        assert intent.type == IntentType.EXPLAIN
        assert intent.confidence > 0.6
        
        # Test edit intent
        intent = natural_interface._parse_intent("add error handling to main.py")
        assert intent.type == IntentType.EDIT
        assert intent.confidence > 0.6
    
    @pytest.mark.parametrize("user_input, intent_type, search_return, expected_target, expected_search_query", [
        # Case 1: Good semantic match found
        ("fix the authentication logic", IntentType.FIX, [('src/auth.py', 0.8)], 'src/auth.py', 'the authentication logic'),
        
        # Case 2: Semantic match score is too low
        ("fix something unrelated", IntentType.FIX, [('src/some_other_file.py', 0.2)], None, 'something unrelated'),
        
        # Case 3: No semantic match found
        ("fix another thing", IntentType.FIX, [], None, 'another thing'),
        
        # Case 4: Quoted query is used for search
        ('edit "the user model"', IntentType.EDIT, [('src/models/user.py', 0.9)], 'src/models/user.py', 'the user model'),
        
        # Case 5: Intent is not for file search, so no search is performed
        ("what is your name?", IntentType.CHAT, [('src/main.py', 0.9)], None, None),
    ])
    def test_target_extraction_with_hybrid_search(self, natural_interface, user_input, intent_type, search_return, expected_target, expected_search_query):
        """Test target extraction using hybrid search for natural language queries."""
        natural_interface.search.search.return_value = search_return
        
        target = natural_interface._extract_target(user_input, intent_type)
        
        if expected_search_query:
            natural_interface.search.search.assert_called_with(expected_search_query, top=1)
        else:
            natural_interface.search.search.assert_not_called()

        assert target == expected_target

    def test_target_extraction_explicit_file_overrides_hybrid(self, natural_interface):
        """Test that an explicit file path in the query overrides hybrid search."""
        natural_interface.search.search.side_effect = Exception("Should not have been called.")
        
        with patch.object(natural_interface, '_find_file_in_codebase', return_value='src/main.py') as mock_find_file:
            target = natural_interface._extract_target("fix bug in main.py", IntentType.FIX)
            assert target == 'src/main.py'
            mock_find_file.assert_called_with('main.py')
    
    def test_scope_extraction(self, natural_interface):
        """Test scope extraction from user input."""
        # Test directory extraction
        scope = natural_interface._extract_scope("find errors in src directory")
        assert "src" in scope
        
        # Test pattern extraction
        scope = natural_interface._extract_scope("search in *.py files")
        assert "*.py" in scope
    
    @pytest.mark.asyncio
    async def test_search_intent_handling(self, natural_interface):
        """Test search intent handling."""
        intent = Intent(type=IntentType.SEARCH, confidence=0.8, target="error")
        
        # Mock search results
        natural_interface.search.search_async = AsyncMock(return_value=[
            (Path("main.py"), 0.9),
            (Path("utils.py"), 0.7)
        ])
        
        result = await natural_interface._handle_search(intent, "search for errors")
        
        assert result["action"] == "search"
        assert len(result["results"]) == 2
        assert result["results"][0]["file"] == "main.py"
    
    @pytest.mark.asyncio
    async def test_debug_intent_handling(self, natural_interface):
        """Test debug intent handling."""
        intent = Intent(type=IntentType.DEBUG, confidence=0.8)
        
        # Mock search results for error terms
        natural_interface.search.search_async = AsyncMock(return_value=[
            (Path("auth.py"), 0.8),
            (Path("main.py"), 0.6)
        ])
        
        result = await natural_interface._handle_debug(intent, "debug for errors")
        
        assert result["action"] == "debug"
        assert len(result["error_locations"]) == 2
        assert "analysis" in result
    
    @pytest.mark.asyncio
    async def test_explain_intent_handling(self, natural_interface):
        """Test explain intent handling."""
        intent = Intent(type=IntentType.EXPLAIN, confidence=0.8, target="main.py")
        
        # Mock context and LLM response
        natural_interface._get_context_for_target = AsyncMock(return_value="def main(): pass")
        natural_interface.llm.generate_async = AsyncMock(return_value="This is the main function...")
        
        result = await natural_interface._handle_explain(intent, "explain main.py")
        
        assert result["action"] == "explain"
        assert "explanation" in result
        assert result["explanation"] == "This is the main function..."
    
    @pytest.mark.asyncio
    async def test_chat_intent_handling(self, natural_interface):
        """Test chat intent handling."""
        intent = Intent(type=IntentType.CHAT, confidence=0.8)
        
        # Mock context engine and LLM
        natural_interface.context_engine.select_context = AsyncMock(return_value="some context")
        natural_interface.llm.generate_async = AsyncMock(return_value="Here's my response...")
        
        result = await natural_interface._handle_chat(intent, "hello", {})
        
        assert result["action"] == "chat"
        assert result["response"] == "Here's my response..."
    
    @pytest.mark.asyncio
    async def test_process_natural_input_success(self, natural_interface):
        """Test successful natural input processing."""
        # Mock the parse and execute methods
        mock_intent = Intent(type=IntentType.SEARCH, confidence=0.8)
        natural_interface._parse_intent = AsyncMock(return_value=mock_intent)
        natural_interface._execute_intent = AsyncMock(return_value={
            "action": "search",
            "message": "Search completed"
        })
        
        result = await natural_interface.process_natural_input("find errors")
        
        assert result["success"] == True
        assert result["intent"] == mock_intent
        assert result["result"]["action"] == "search"
    
    @pytest.mark.asyncio
    async def test_process_natural_input_error(self, natural_interface):
        """Test error handling in natural input processing."""
        # Mock an exception
        natural_interface._parse_intent = AsyncMock(side_effect=Exception("Test error"))
        
        result = await natural_interface.process_natural_input("test input")
        
        assert result["success"] == False
        assert "error" in result
    
    def test_intent_confidence_scoring(self, natural_interface):
        """Test intent confidence scoring."""
        # High confidence cases
        high_confidence_inputs = [
            "debug for errors",
            "fix the authentication bug", 
            "search for TODO comments",
            "explain the main function"
        ]
        
        for input_text in high_confidence_inputs:
            intent = natural_interface._parse_intent(input_text)
            assert intent.confidence > 0.6, f"Low confidence for: {input_text}"
        
        # Lower confidence case (ambiguous)
        ambiguous_intent = natural_interface._parse_intent("hello there")
        assert ambiguous_intent.confidence <= 0.7


class TestIntentTypes:
    """Test intent type definitions and behavior."""
    
    def test_intent_creation(self):
        """Test intent creation with different parameters."""
        intent = Intent(
            type=IntentType.DEBUG,
            confidence=0.8,
            target="main.py",
            scope="src/",
            details={"specific": "error handling"}
        )
        
        assert intent.type == IntentType.DEBUG
        assert intent.confidence == 0.8
        assert intent.target == "main.py"
        assert intent.scope == "src/"
        assert intent.details["specific"] == "error handling"
    
    def test_intent_default_details(self):
        """Test intent with default details."""
        intent = Intent(type=IntentType.SEARCH, confidence=0.7)
        
        assert intent.details == {}
        assert intent.target is None
        assert intent.scope is None


class TestNaturalLanguageExamples:
    """Test with realistic natural language examples."""
    
    @pytest.fixture
    def interface(self):
        """Create interface for testing."""
        config = Mock(spec=Config)
        console = Mock()
        
        with patch('term_coder.natural_interface.LLMOrchestrator'), \
             patch('term_coder.natural_interface.HybridSearch'), \
             patch('term_coder.natural_interface.ContextEngine'):
            
            return NaturalLanguageInterface(config, console)
    
    @pytest.mark.parametrize("user_input,expected_intent", [
        ("debug for errors", IntentType.DEBUG),
        ("find bugs in the code", IntentType.DEBUG),
        ("what's wrong with the authentication", IntentType.DEBUG),
        ("fix the login issue", IntentType.FIX),
        ("repair the broken function", IntentType.FIX),
        ("solve the database connection problem", IntentType.FIX),
        ("explain how authentication works", IntentType.EXPLAIN),
        ("what does the main function do", IntentType.EXPLAIN),
        ("describe the user registration flow", IntentType.EXPLAIN),
        ("add error handling to main.py", IntentType.EDIT),
        ("implement logging in the service", IntentType.EDIT),
        ("create a new user model", IntentType.EDIT),
        ("search for TODO comments", IntentType.SEARCH),
        ("find all database queries", IntentType.SEARCH),
        ("locate the authentication code", IntentType.SEARCH),
        ("review my recent changes", IntentType.REVIEW),
        ("check the code quality", IntentType.REVIEW),
        ("run the tests", IntentType.TEST),
        ("verify the functionality", IntentType.TEST),
        ("refactor the user service", IntentType.REFACTOR),
        ("clean up the database code", IntentType.REFACTOR),
        ("generate a new component", IntentType.GENERATE),
        ("create tests for the user model", IntentType.GENERATE),
    ])
    def test_realistic_intent_recognition(self, interface, user_input, expected_intent):
        """Test intent recognition with realistic user inputs."""
        intent = interface._parse_intent(user_input)
        assert intent.type == expected_intent, f"Expected {expected_intent} for '{user_input}', got {intent.type}"
        assert intent.confidence > 0.5, f"Low confidence ({intent.confidence}) for '{user_input}'"


if __name__ == "__main__":
    pytest.main([__file__])
