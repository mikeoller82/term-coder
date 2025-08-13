from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import re

from .llm import LLMOrchestrator


@dataclass
class TargetSpec:
    path: Path
    start: Optional[int] = None
    end: Optional[int] = None
    symbol: Optional[str] = None


def parse_target(target: str) -> TargetSpec:
    # forms: path, path:START:END, path#SYMBOL
    path_part = target
    start = end = None
    symbol = None

    if "#" in target:
        path_part, symbol = target.split("#", 1)
    if ":" in path_part:
        parts = path_part.split(":")
        if len(parts) >= 3 and parts[-2].isdigit() and parts[-1].isdigit():
            start = int(parts[-2])
            end = int(parts[-1])
            path_part = ":".join(parts[:-2])
    return TargetSpec(path=Path(path_part), start=start, end=end, symbol=symbol)


def _find_symbol_bounds(text: str, symbol: str) -> Tuple[int, int]:
    # Very simple Python-oriented symbol locator for def/class
    lines = text.splitlines()
    pattern = re.compile(rf"^(\s*)(def|class)\s+{re.escape(symbol)}\b")
    start_idx = -1
    base_indent = 0
    for i, line in enumerate(lines):
        m = pattern.match(line)
        if m:
            start_idx = i
            base_indent = len(m.group(1))
            break
    if start_idx == -1:
        return 1, min(200, len(lines))  # fallback small window
    # find end by lesser indent
    end_idx = start_idx + 1
    for j in range(start_idx + 1, len(lines)):
        line = lines[j]
        # blank lines allowed
        stripped = line.lstrip(" ")
        if not stripped:
            continue
        indent = len(line) - len(stripped)
        if indent <= base_indent:
            end_idx = j
            break
        end_idx = j + 1
    return start_idx + 1, end_idx


def read_snippet(spec: TargetSpec, context: int = 0, max_chars: int = 20000) -> Tuple[str, int, int]:
    p = spec.path.resolve()
    text = p.read_text(errors="ignore")
    start = spec.start
    end = spec.end
    if spec.symbol and (start is None or end is None):
        s, e = _find_symbol_bounds(text, spec.symbol)
        start = start or s
        end = end or e
    if start is None:
        start = 1
    if end is None:
        end = len(text.splitlines())
    start = max(1, start - context)
    end = min(len(text.splitlines()), end + context)
    lines = text.splitlines()
    snippet_lines = lines[start - 1 : end]
    snippet = "\n".join(snippet_lines)
    if len(snippet) > max_chars:
        half = max_chars // 2
        snippet = snippet[:half] + "\n... [truncated] ...\n" + snippet[-half:]
    return snippet, start, end


def language_from_extension(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".md": "markdown",
        ".json": "json",
        ".yml": "yaml",
        ".yaml": "yaml",
    }.get(ext, "text")


def build_explain_prompt(path: Path, snippet: str, start: int, end: int) -> str:
    return (
        "You are a precise code explainer. Explain the following file segment in depth.\n"
        f"File: {path}\nLines: {start}-{end}\n\n"
        "Explain purpose, inputs/outputs, side effects, control flow, and potential issues.\n"
        "Suggest improvements if relevant.\n\n"
        "<code>\n" + snippet + "\n</code>\n"
    )


def explain(spec: TargetSpec, model: Optional[str] = None, offline: Optional[bool] = None) -> str:
    snippet, start, end = read_snippet(spec, context=0)
    prompt = build_explain_prompt(spec.path, snippet, start, end)
    orch = LLMOrchestrator(offline=offline)
    resp = orch.complete(prompt, model=model)
    return resp.text
