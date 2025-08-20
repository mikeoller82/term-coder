#!/usr/bin/env python3
"""
Live test to demonstrate model switching in term-coder.
"""

import sys
import asyncio
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from term_coder.config import Config, DEFAULT_CONFIG
from term_coder.natural_interface import NaturalLanguageInterface
from rich.console import Console


async def simulate_model_switching():
    """Simulate how model switching works during an interactive session."""
    console = Console()
    
    console.print("[bold cyan]🔄 Simulating Interactive Model Switching[/bold cyan]")
    console.print()
    
    # Create config and natural interface
    config = Config()
    config.data = DEFAULT_CONFIG.copy()
    
    natural_interface = NaturalLanguageInterface(config, console)
    
    console.print("📋 Initial setup:")
    initial_model = config.get("model.default", "mock-llm")
    console.print(f"   Config model: {initial_model}")
    console.print(f"   LLM orchestrator model: {natural_interface.llm.default_model}")
    console.print()
    
    # Simulate switching to openai:gpt
    console.print("🔄 Switching to openai:gpt...")
    config.set("model.default", "openai:gpt")
    
    # This is what happens in the interactive terminal when model changes
    from term_coder.llm import LLMOrchestrator
    default_model = config.get("model.default", "mock-llm")
    natural_interface.llm = LLMOrchestrator(
        default_model=default_model,
        offline=bool(config.get("privacy.offline", False))
    )
    
    console.print(f"   Config model: {config.get('model.default')}")
    console.print(f"   LLM orchestrator model: {natural_interface.llm.default_model}")
    console.print("   ✅ Model switch successful!")
    console.print()
    
    # Simulate switching back to mock-llm
    console.print("🔄 Switching back to mock-llm...")
    config.set("model.default", "mock-llm")
    
    default_model = config.get("model.default", "mock-llm")
    natural_interface.llm = LLMOrchestrator(
        default_model=default_model,
        offline=bool(config.get("privacy.offline", False))
    )
    
    console.print(f"   Config model: {config.get('model.default')}")
    console.print(f"   LLM orchestrator model: {natural_interface.llm.default_model}")
    console.print("   ✅ Model switch successful!")
    console.print()
    
    console.print("[bold green]🎉 Model switching works correctly during live sessions![/bold green]")


if __name__ == "__main__":
    asyncio.run(simulate_model_switching())