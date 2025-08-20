from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Optional, Protocol
import os
import contextlib


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


class OpenAIAdapter:
    """OpenAI Chat Completions adapter with graceful fallback to mock if unavailable."""

    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self._client = None
        with contextlib.suppress(Exception):
            from openai import OpenAI  # type: ignore

            # Only initialize if API key present
            if os.getenv("OPENAI_API_KEY"):
                self._client = OpenAI()

    def complete(self, prompt: str, tools: Optional[List[Tool]] = None) -> Response:
        if self._client is None:
            return Response(text=f"[MOCK:openai-disabled] {prompt[:200]}", model=self.model_name)
        try:
            resp = self._client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.choices[0].message.content or ""
            return Response(text=text, model=self.model_name)
        except Exception:
            return Response(text=f"[MOCK:openai-error] {prompt[:200]}", model=self.model_name)

    def stream(self, prompt: str, tools: Optional[List[Tool]] = None) -> Iterator[str]:
        if self._client is None:
            yield f"[MOCK:{self.model_name}] "
            chunk = prompt.strip()
            for i in range(0, min(len(chunk), 600), 60):
                yield chunk[i : i + 60]
            return
        try:
            stream = self._client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
            for event in stream:
                with contextlib.suppress(Exception):
                    delta = event.choices[0].delta.content
                    if delta:
                        yield delta
        except Exception:
            yield f"[MOCK:{self.model_name}] "
            yield prompt[:120]


class AnthropicAdapter:
    """Anthropic Messages adapter with graceful fallback to mock if unavailable."""

    def __init__(self, model_name: str = "claude-3-haiku-20240307"):
        self.model_name = model_name
        self._client = None
        with contextlib.suppress(Exception):
            import anthropic  # type: ignore

            if os.getenv("ANTHROPIC_API_KEY"):
                self._client = anthropic.Anthropic()

    def complete(self, prompt: str, tools: Optional[List[Tool]] = None) -> Response:
        if self._client is None:
            return Response(text=f"[MOCK:anthropic-disabled] {prompt[:200]}", model=self.model_name)
        try:
            msg = self._client.messages.create(
                model=self.model_name,
                max_tokens=8000,
                messages=[{"role": "user", "content": prompt}],
            )
            # Concatenate text parts
            text = "".join(part.text for part in msg.content if getattr(part, "type", None) == "text")
            return Response(text=text, model=self.model_name)
        except Exception:
            return Response(text=f"[MOCK:anthropic-error] {prompt[:200]}", model=self.model_name)

    def stream(self, prompt: str, tools: Optional[List[Tool]] = None) -> Iterator[str]:
        # Anthropics streaming requires async/stream API; for simplicity use non-stream and yield once
        resp = self.complete(prompt, tools)
        yield resp.text


class LocalOllamaAdapter:
    """Local Ollama HTTP adapter. Expects a running ollama daemon at localhost:11434."""

    def __init__(self, model_name: str = "qwen3-coder:latest"):
        self.model_name = model_name
        # Lazy import requests to avoid hard dependency
        self._requests = None
        with contextlib.suppress(Exception):
            import requests  # type: ignore

            self._requests = requests

    def complete(self, prompt: str, tools: Optional[List[Tool]] = None) -> Response:
        if self._requests is None:
            return Response(text=f"[MOCK:ollama-disabled] {prompt[:200]}", model=self.model_name)
        try:
            r = self._requests.post(
                "http://localhost:11434/api/generate",
                json={"model": self.model_name, "prompt": prompt, "stream": False},
                timeout=120,
            )
            text = r.json().get("response", "")
            return Response(text=text, model=self.model_name)
        except Exception:
            return Response(text=f"[MOCK:ollama-error] {prompt[:200]}", model=self.model_name)

    def stream(self, prompt: str, tools: Optional[List[Tool]] = None) -> Iterator[str]:
        # Simplify to non-stream then yield
        resp = self.complete(prompt, tools)
        yield resp.text


class OpenRouterAdapter:
    """OpenRouter adapter with graceful fallback to mock if unavailable."""

    def __init__(self, model_name: str = "openai/gpt-4o-mini"):
        self.model_name = model_name
        self._requests = None
        self._api_key = os.getenv("OPENROUTER_API_KEY")
        
        with contextlib.suppress(Exception):
            import requests  # type: ignore
            self._requests = requests

    def complete(self, prompt: str, tools: Optional[List[Tool]] = None) -> Response:
        if self._requests is None or not self._api_key:
            return Response(text=f"[MOCK:openrouter-disabled] {prompt[:200]}", model=self.model_name)
        
        try:
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "HTTP-Referer": "https://github.com/term-coder/term-coder",
                "X-Title": "Term Coder",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
            }
            
            response = self._requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=data,
                headers=headers,
                timeout=120,
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                return Response(text=text, model=self.model_name)
            else:
                return Response(text=f"[MOCK:openrouter-error-{response.status_code}] {prompt[:200]}", model=self.model_name)
                
        except Exception:
            return Response(text=f"[MOCK:openrouter-error] {prompt[:200]}", model=self.model_name)

    def stream(self, prompt: str, tools: Optional[List[Tool]] = None) -> Iterator[str]:
        if self._requests is None or not self._api_key:
            yield f"[MOCK:{self.model_name}] "
            chunk = prompt.strip()
            for i in range(0, min(len(chunk), 600), 60):
                yield chunk[i : i + 60]
            return
        
        try:
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "HTTP-Referer": "https://github.com/term-coder/term-coder",
                "X-Title": "Term Coder",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
            }
            
            response = self._requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=data,
                headers=headers,
                timeout=120,
                stream=True,
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            line_str = line_str[6:]  # Remove 'data: ' prefix
                            if line_str == '[DONE]':
                                break
                            try:
                                import json
                                data = json.loads(line_str)
                                content = data.get("choices", [{}])[0].get("delta", {}).get("content")
                                if content:
                                    yield content
                            except (json.JSONDecodeError, KeyError):
                                continue
            else:
                yield f"[MOCK:openrouter-stream-error-{response.status_code}] "
                yield prompt[:120]
                
        except Exception:
            yield f"[MOCK:openrouter-stream-error] "
            yield prompt[:120]


class LLMOrchestrator:
    def __init__(self, default_model: str = "mock-llm", offline: bool | None = None, privacy_manager=None, audit_logger=None):
        self.adapters: Dict[str, BaseLLMAdapter] = {
            "mock-llm": MockLLMAdapter("mock-llm"),
            "openai:gpt": OpenAIAdapter("gpt-4o-mini"),
            "anthropic:claude": AnthropicAdapter("claude-3-haiku-20240307"),
            "local:ollama": LocalOllamaAdapter("qwen3-coder:latest"),
            "openrouter": OpenRouterAdapter("openai/gpt-4o-mini"),
        }
        self.default_model = default_model if default_model in self.adapters else "mock-llm"
        self.offline = offline
        self.privacy_manager = privacy_manager
        self.audit_logger = audit_logger

    def get(self, model: Optional[str]) -> BaseLLMAdapter:
        key = model or self.default_model
        if self.offline and key in {"openai:gpt", "anthropic:claude", "openrouter"}:
            return self.adapters["local:ollama"] if "local:ollama" in self.adapters else self.adapters["mock-llm"]
        return self.adapters.get(key, self.adapters[self.default_model])

    def complete(self, prompt: str, model: Optional[str] = None, tools: Optional[List[Tool]] = None) -> Response:
        # Process prompt for privacy
        processed_prompt = prompt
        if self.privacy_manager:
            processed_prompt, metadata = self.privacy_manager.process_text_for_privacy(prompt, "llm_prompt")
            
            # Log security events if secrets were found
            if metadata.get("secrets_found"):
                if self.audit_logger:
                    self.audit_logger.log_security_event(
                        "secrets_detected_in_prompt",
                        "medium",
                        {"secret_count": len(metadata["secrets_found"]), "patterns": [s["pattern"] for s in metadata["secrets_found"]]}
                    )
        
        adapter = self.get(model)
        
        # Log LLM interaction
        if self.audit_logger:
            self.audit_logger.log_llm_interaction(
                model or self.default_model,
                "complete",
                {"prompt_length": len(processed_prompt), "tools_count": len(tools) if tools else 0},
                success=True
            )
        
        try:
            response = adapter.complete(processed_prompt, tools)
            
            # Process response for privacy
            if self.privacy_manager:
                response.text, _ = self.privacy_manager.process_text_for_privacy(response.text, "llm_response")
            
            return response
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_error("llm_completion_failed", str(e), {"model": model or self.default_model})
            raise

    def stream(self, prompt: str, model: Optional[str] = None, tools: Optional[List[Tool]] = None) -> Iterator[str]:
        # Process prompt for privacy
        processed_prompt = prompt
        if self.privacy_manager:
            processed_prompt, metadata = self.privacy_manager.process_text_for_privacy(prompt, "llm_prompt")
            
            # Log security events if secrets were found
            if metadata.get("secrets_found"):
                if self.audit_logger:
                    self.audit_logger.log_security_event(
                        "secrets_detected_in_prompt",
                        "medium",
                        {"secret_count": len(metadata["secrets_found"]), "patterns": [s["pattern"] for s in metadata["secrets_found"]]}
                    )
        
        adapter = self.get(model)
        
        # Log LLM interaction
        if self.audit_logger:
            self.audit_logger.log_llm_interaction(
                model or self.default_model,
                "stream",
                {"prompt_length": len(processed_prompt), "tools_count": len(tools) if tools else 0},
                success=True
            )
        
        try:
            for chunk in adapter.stream(processed_prompt, tools):
                # Process each chunk for privacy if needed
                if self.privacy_manager and self.privacy_manager.should_redact_secrets():
                    processed_chunk, _ = self.privacy_manager.process_text_for_privacy(chunk, "llm_response_chunk")
                    yield processed_chunk
                else:
                    yield chunk
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_error("llm_streaming_failed", str(e), {"model": model or self.default_model})
            raise

