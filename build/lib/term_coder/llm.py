from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Optional, Protocol


@dataclass
class Tool:
    name: str
    description: str


@dataclass
class Response:
    text: str
    model: str


class ResponseChunk(Protocol):
    def __str__(self) -> str: ...


class BaseLLMAdapter(Protocol):
    """Adapter interface for different LLM providers."""

    model_name: str

    def complete(self, prompt: str, tools: Optional[List[Tool]] = None) -> Response:
        ...

    def stream(self, prompt: str, tools: Optional[List[Tool]] = None) -> Iterator[str]:
        ...

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)


class MockLLMAdapter:
    def __init__(self, model_name: str = "mock-llm"):
        self.model_name = model_name

    def complete(self, prompt: str, tools: Optional[List[Tool]] = None) -> Response:
        return Response(text=f"[MOCK:{self.model_name}] {prompt[:200]}", model=self.model_name)

    def stream(self, prompt: str, tools: Optional[List[Tool]] = None) -> Iterator[str]:
        yield f"[MOCK:{self.model_name}] "
        # crude chunking for demonstration
        chunk = prompt.strip()
        for i in range(0, min(len(chunk), 600), 60):
            yield chunk[i : i + 60]

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)


class OpenAIAdapter(MockLLMAdapter):
    """Placeholder adapter; inherits mock behavior for now."""


class AnthropicAdapter(MockLLMAdapter):
    """Placeholder adapter; inherits mock behavior for now."""


class LocalOllamaAdapter(MockLLMAdapter):
    """Placeholder adapter; inherits mock behavior for now."""


class LLMOrchestrator:
    def __init__(self, default_model: str = "mock-llm"):
        self.adapters: Dict[str, BaseLLMAdapter] = {
            "mock-llm": MockLLMAdapter("mock-llm"),
            "openai:gpt": OpenAIAdapter("openai:gpt"),
            "anthropic:claude": AnthropicAdapter("anthropic:claude"),
            "local:ollama": LocalOllamaAdapter("local:ollama"),
        }
        self.default_model = default_model if default_model in self.adapters else "mock-llm"

    def get(self, model: Optional[str]) -> BaseLLMAdapter:
        if model and model in self.adapters:
            return self.adapters[model]
        return self.adapters[self.default_model]

    def complete(self, prompt: str, model: Optional[str] = None, tools: Optional[List[Tool]] = None) -> Response:
        adapter = self.get(model)
        return adapter.complete(prompt, tools)

    def stream(self, prompt: str, model: Optional[str] = None, tools: Optional[List[Tool]] = None) -> Iterator[str]:
        adapter = self.get(model)
        return adapter.stream(prompt, tools)

