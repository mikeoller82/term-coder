from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Iterable, Tuple

from .context import ContextSelection


@dataclass
class RenderedPrompt:
    system: str
    user: str


def _read_file_safe(root: Path, relative_path: str, max_chars: int) -> str:
    try:
        text = (root / relative_path).read_text(errors="ignore")
        if len(text) > max_chars:
            head = text[: max_chars // 2]
            tail = text[-max_chars // 2 :]
            return head + "\n\n... [truncated] ...\n\n" + tail
        return text
    except Exception:
        return "<unreadable>"


def render_chat_prompt(
    prompt_text: str,
    context: ContextSelection,
    max_context_chars: int = 32_000,
    history: Iterable[Tuple[str, str]] | None = None,
) -> RenderedPrompt:
    root = Path.cwd().resolve()

    # Build a simple context preamble, bounded by max_context_chars
    remaining = max_context_chars
    parts: List[str] = []
    for cf in context.files:
        if remaining <= 0:
            break
        file_header = f"# File: {cf.path} (score={cf.relevance_score:.3f})\n"
        content = _read_file_safe(root, cf.path, max(0, remaining - len(file_header)))
        snippet = file_header + content
        snippet_len = len(snippet)
        if snippet_len > remaining:
            snippet = snippet[:remaining]
            snippet_len = remaining
        parts.append(snippet)
        remaining -= snippet_len

    system = (
        "You are an expert software engineer AI called Term Coder. "
        "Your sole purpose is to directly fulfill the user's request by generating or editing code. "
        "Follow these instructions precisely:\n"
        "1.  **Analyze the user's request and the provided context.**\n"
        "2.  **Generate the code or code patch required to fulfill the request.**\n"
        "3.  **Output ONLY the code or patch.** Do not include any explanations, apologies, or conversational filler. "
        "Do not explain how to perform the task. Just do it."
    )

    history_text = ""
    if history:
        hist_parts: List[str] = ["<history>\n"]
        for role, content in history:
            role_t = "USER" if role == "user" else "ASSISTANT"
            hist_parts.append(f"[{role_t}]\n{content}\n\n")
        hist_parts.append("</history>\n\n")
        history_text = "".join(hist_parts)

    user = "".join([history_text, "".join(parts), "\n\n", prompt_text])
    return RenderedPrompt(system=system, user=user)
