from __future__ import annotations

from typing import Optional


class TokenEstimator:
    def __init__(self, model_hint: Optional[str] = None):
        self.model_hint = model_hint or "gpt-4o-mini"
        try:
            import tiktoken  # type: ignore
        except Exception:  # pragma: no cover
            self._enc = None
        else:
            try:
                self._enc = tiktoken.encoding_for_model(self.model_hint)
            except Exception:
                self._enc = tiktoken.get_encoding("cl100k_base")

    def estimate(self, text: str) -> int:
        if not text:
            return 0
        if getattr(self, "_enc", None) is None:
            # fallback heuristic: ~4 chars per token
            return max(1, len(text) // 4)
        return len(self._enc.encode(text))
