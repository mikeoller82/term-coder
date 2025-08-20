#!/usr/bin/env python3
"""
Test script for model switching functionality in term-coder interactive terminal.
"""

import sys
import asyncio
from pathlib import Path

# Add the src directory to Python path so we can import term_coder modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from term_coder.config import Config, DEFAULT_CONFIG
from term_coder.interactive_terminal import InteractiveTerminal
from term_coder.llm import LLMOrchestrator


async def test_model_switching():
    """Test the model switching functionality."""
    print("🧪 Testing Model Switching Functionality")
    print("=" * 50)
    
    # Create a test config
    config = Config()
    config.data = DEFAULT_CONFIG.copy()
    
    # Test 1: Verify default model configuration
    print("\n1. Testing default model configuration...")
    default_model = config.get("model.default", "mock-llm")
    print(f"   Default model: {default_model}")
    assert default_model in ["gpt-5-mini", "mock-llm"], f"Unexpected default model: {default_model}"
    
    # Test 2: Verify LLMOrchestrator has all expected models
    print("\n2. Testing LLMOrchestrator model availability...")
    orchestrator = LLMOrchestrator()
    available_models = list(orchestrator.adapters.keys())
    expected_models = ["mock-llm", "openai:gpt", "anthropic:claude", "local:ollama", "openrouter"]
    
    print(f"   Available models: {available_models}")
    for model in expected_models:
        assert model in available_models, f"Expected model {model} not found"
    print("   ✅ All expected models are available")
    
    # Test 3: Test model switching
    print("\n3. Testing model configuration changes...")
    
    # Switch to mock-llm
    old_model = config.get("model.default", "mock-llm")
    config.set("model.default", "mock-llm")
    new_model = config.get("model.default")
    print(f"   Changed model from {old_model} to {new_model}")
    assert new_model == "mock-llm", f"Model switch failed: expected mock-llm, got {new_model}"
    
    # Switch to openai:gpt
    config.set("model.default", "openai:gpt")
    new_model = config.get("model.default")
    print(f"   Changed model to {new_model}")
    assert new_model == "openai:gpt", f"Model switch failed: expected openai:gpt, got {new_model}"
    
    # Switch back to mock-llm
    config.set("model.default", "mock-llm")
    new_model = config.get("model.default")
    print(f"   Changed model back to {new_model}")
    assert new_model == "mock-llm", f"Model switch failed: expected mock-llm, got {new_model}"
    
    print("   ✅ Model switching works correctly")
    
    # Test 4: Test invalid model handling
    print("\n4. Testing invalid model handling...")
    try:
        # This should not crash, just stay with the current valid model
        invalid_model = "invalid-model-name"
        orchestrator = LLMOrchestrator(default_model=invalid_model)
        # The orchestrator should fall back to a valid model
        actual_model = orchestrator.default_model
        print(f"   Invalid model '{invalid_model}' -> fallback to '{actual_model}'")
        assert actual_model in available_models, f"Fallback model {actual_model} not in available models"
        print("   ✅ Invalid model handling works")
    except Exception as e:
        print(f"   ❌ Invalid model handling failed: {e}")
        return False
    
    # Test 5: Test InteractiveTerminal integration
    print("\n5. Testing InteractiveTerminal integration...")
    terminal = InteractiveTerminal(config)
    
    # Check that the terminal has access to the config and natural interface
    assert terminal.config == config, "Terminal config not set correctly"
    assert terminal.natural_interface is not None, "Natural interface not initialized"
    assert terminal.natural_interface.config == config, "Natural interface config not set correctly"
    
    print("   ✅ InteractiveTerminal integration works")
    
    print("\n🎉 All tests passed! Model switching functionality is working correctly.")
    return True


async def demo_interactive_usage():
    """Demo the interactive usage of model switching."""
    print("\n" + "=" * 50)
    print("📖 DEMO: How to use model switching in interactive mode")
    print("=" * 50)
    
    print("\nWhen you run 'tc' and enter interactive mode, you can use these commands:")
    print()
    print("  model                    # Show current model and available options")
    print("  model openai:gpt         # Switch to OpenAI GPT-4o-mini")
    print("  model anthropic:claude   # Switch to Anthropic Claude Haiku") 
    print("  model local:ollama       # Switch to local Ollama model")
    print("  model openrouter         # Switch to OpenRouter API")
    print("  model mock-llm           # Switch to mock model (for testing)")
    print()
    print("  status                   # Check current session status (shows current model)")
    print("  help                     # See all available commands")
    print()
    print("The same commands work in 'tc advanced' mode as well!")
    print()
    print("💡 Tips:")
    print("  • Model changes are saved to .term-coder/config.yaml")
    print("  • You need appropriate API keys for non-mock models")
    print("  • Use 'model' without arguments to see all available options")


if __name__ == "__main__":
    print("🚀 Term-Coder Model Switching Test Suite")
    
    try:
        # Run the tests
        success = asyncio.run(test_model_switching())
        
        if success:
            # Show the demo
            asyncio.run(demo_interactive_usage())
        else:
            print("\n❌ Tests failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)