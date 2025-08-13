#!/usr/bin/env python3
"""Test script to verify real LLM integration."""

from src.term_coder.natural_interface import NaturalLanguageInterface
from unittest.mock import Mock

def test_real_llm():
    """Test that the natural language interface uses real LLM."""
    print("🔧 Testing Natural Language Interface with Real LLM")
    print("=" * 60)
    
    # Create mock config and console
    config = Mock()
    config.get = Mock(return_value=False)
    console = Mock()
    console.print = Mock()
    
    try:
        # Initialize interface
        interface = NaturalLanguageInterface(config, console)
        
        print(f"✅ Interface initialized")
        print(f"   Default model: {interface.llm.default_model}")
        
        # Test LLM directly
        print("\n🧪 Testing LLM Integration:")
        test_prompt = "What is 2+2? Answer in one sentence."
        print(f"   Prompt: '{test_prompt}'")
        
        response = interface.llm.complete(test_prompt)
        print(f"   Model: {response.model}")
        print(f"   Response: {response.text}")
        
        # Check if it's real or mock
        if "[MOCK:" in response.text:
            print("❌ ERROR: Still getting mock data!")
            return False
        else:
            print("✅ SUCCESS: Getting real LLM responses!")
            
        # Test intent parsing
        print("\n🧪 Testing Intent Recognition:")
        test_cases = [
            "explain main.py",
            "debug for errors", 
            "search for TODO comments"
        ]
        
        for test_input in test_cases:
            intent = interface._parse_intent(test_input)
            print(f"   '{test_input}' → {intent.type.value} ({intent.confidence:.2f})")
            if intent.target:
                print(f"      Target: {intent.target}")
        
        print("\n🎉 SUCCESS! Natural Language Interface is using real LLM!")
        print("\n🚀 Real AI Features Now Available:")
        print("   • 🤖 Genuine natural language understanding")
        print("   • 🧠 Real AI-powered explanations and analysis")
        print("   • 💡 Intelligent code suggestions and debugging")
        print("   • 🔍 Smart context-aware assistance")
        print("   • ✨ Authentic AI conversations")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_real_llm()
    exit(0 if success else 1)