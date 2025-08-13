from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .config import Config
from .search import HybridSearch


@dataclass
class ContextFile:
    path: str
    relevance_score: float = 0.0


@dataclass
class ContextSelection:
    files: List[ContextFile]


class ContextEngine:
    def __init__(self, config: Config):
        self.config = config

    def _estimate_tokens_for_file(self, root: Path, relative_path: str) -> int:
        # Very rough heuristic: ~4 chars per token on average
        p = (root / relative_path).resolve()
        try:
            size = p.stat().st_size
        except Exception:
            size = 0
        return max(1, size // 4)

    def select_context(self, files: Optional[List[str]] = None, query: Optional[str] = None, budget_tokens: int = 8000) -> ContextSelection:
        selected: List[ContextFile] = []
        root = Path.cwd().resolve()

        # 1) Explicit files always included first
        for f in files or []:
            selected.append(ContextFile(path=f, relevance_score=1.0))

        # 2) If a query is provided, expand with hybrid search respecting config
        if query:
            alpha = float(self.config.get("retrieval.hybrid_weight", 0.7))
            hybrid = HybridSearch(root, alpha=alpha)
            # Use a moderately high cap; we will trim by token budget below
            candidates = hybrid.search(query, top=100)
            for path, score in candidates:
                if any(cf.path == path for cf in selected):
                    # bump relevance if already explicit
                    for cf in selected:
                        if cf.path == path:
                            cf.relevance_score = max(cf.relevance_score, score)
                    continue
                selected.append(ContextFile(path=path, relevance_score=score))

        # 3) Enforce token budget by approximate size
        max_tokens = int(self.config.get("retrieval.max_tokens", budget_tokens))
        # sort by relevance desc then smaller first
        selected.sort(key=lambda c: (-c.relevance_score, self._estimate_tokens_for_file(root, c.path)))

        total_tokens = 0
        budgeted: List[ContextFile] = []
        for cf in selected:
            file_tokens = self._estimate_tokens_for_file(root, cf.path)
            if total_tokens + file_tokens > max_tokens:
                continue
            budgeted.append(cf)
            total_tokens += file_tokens

        return ContextSelection(files=budgeted)

