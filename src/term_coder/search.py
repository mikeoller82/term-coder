from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from .utils import iter_source_files
from .semantic import SemanticSearch, create_embedding_model_from_config
from .config import Config


@dataclass
class SearchHit:
    file_path: str
    line_number: int
    line_text: str


class LexicalSearch:
    def __init__(self, root: Path):
        self.root = root
        self._rg = shutil.which("rg")

    def search(
        self,
        query: str,
        include: Optional[Iterable[str]] = None,
        exclude: Optional[Iterable[str]] = None,
        case_insensitive: bool = True,
        limit: int = 200,
    ) -> List[SearchHit]:
        if self._rg:
            return self._search_with_rg(query, include, exclude, case_insensitive, limit)
        return self._search_python(query, include, exclude, case_insensitive, limit)

    def rank_files(
        self,
        query: str,
        include: Optional[Iterable[str]] = None,
        exclude: Optional[Iterable[str]] = None,
        case_insensitive: bool = True,
        top: int = 20,
    ) -> List[Tuple[str, float]]:
        """Aggregate lexical hits by file and rank by frequency.

        Returns a list of (file_path, score) where score is a simple count-based
        relevance in [0, 1] after min-max normalization over observed counts.
        """
        hits = self.search(query, include=include, exclude=exclude, case_insensitive=case_insensitive, limit=10_000)
        counts: dict[str, int] = {}
        for h in hits:
            counts[h.file_path] = counts.get(h.file_path, 0) + 1
        if not counts:
            return []
        max_count = max(counts.values()) or 1
        ranked: List[Tuple[str, float]] = []
        for path, count in counts.items():
            ranked.append((path, count / max_count))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:top]

    def _search_with_rg(
        self,
        query: str,
        include: Optional[Iterable[str]],
        exclude: Optional[Iterable[str]],
        case_insensitive: bool,
        limit: int,
    ) -> List[SearchHit]:
        cmd = [self._rg, "--line-number", "--with-filename", "-n", "-S"]
        if case_insensitive:
            cmd.append("-i")
        for g in include or []:
            cmd.extend(["-g", g])
        for g in exclude or []:
            cmd.extend(["-g", f"!{g}"])
        cmd.extend([query, str(self.root)])
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            hits: List[SearchHit] = []
            for line in proc.stdout.splitlines():
                try:
                    path_str, rest = line.split(":", 1)
                    line_no_str, text = rest.split(":", 1)
                    hits.append(SearchHit(file_path=path_str, line_number=int(line_no_str), line_text=text))
                    if len(hits) >= limit:
                        break
                except ValueError:
                    continue
            return hits
        except Exception:
            return []

    def _search_python(
        self,
        query: str,
        include: Optional[Iterable[str]],
        exclude: Optional[Iterable[str]],
        case_insensitive: bool,
        limit: int,
    ) -> List[SearchHit]:
        needle = query.lower() if case_insensitive else query
        hits: List[SearchHit] = []
        for path in iter_source_files(self.root, include_globs=include, exclude_globs=exclude):
            try:
                for idx, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
                    hay = line.lower() if case_insensitive else line
                    if needle in hay:
                        hits.append(SearchHit(file_path=str(path), line_number=idx, line_text=line))
                        if len(hits) >= limit:
                            return hits
            except Exception:
                continue
        return hits


@dataclass
class SemanticHit:
    file_path: str
    relevance_score: float


class HybridSearch:
    """Combines lexical and semantic scores with a simple weighted sum.

    This implementation favors simplicity: lexical hits contribute a base score
    of 1.0 per occurrence (clipped), while semantic scores are already in [0,1].
    """

    def __init__(self, root: Path, alpha: float = 0.7, config: Config | None = None):
        self.root = root
        self.alpha = alpha
        self.lexical = LexicalSearch(root)
        # create model per config
        cfg = config or Config()
        model = create_embedding_model_from_config(cfg)
        self.semantic = SemanticSearch(root, model=model)

    def search(self, query: str, include: Optional[Iterable[str]] = None, exclude: Optional[Iterable[str]] = None, top: int = 20) -> List[Tuple[str, float]]:
        # Run lexical and semantic; map to scores per file
        lex_hits = self.lexical.search(query, include=include, exclude=exclude, limit=1000)
        sem_hits = self.semantic.search(query, top_k=100, include=include, exclude=exclude)

        file_to_lex_score: dict[str, float] = {}
        for h in lex_hits:
            file_to_lex_score[h.file_path] = min(1.0, file_to_lex_score.get(h.file_path, 0.0) + 0.1)

        file_to_sem_score: dict[str, float] = {path: score for path, score in sem_hits}

        files = set(file_to_lex_score) | set(file_to_sem_score)
        combined: List[Tuple[str, float]] = []
        for f in files:
            ls = file_to_lex_score.get(f, 0.0)
            ss = file_to_sem_score.get(f, 0.0)
            score = self.alpha * ss + (1 - self.alpha) * ls
            combined.append((f, score))

        combined.sort(key=lambda x: x[1], reverse=True)
        return combined[:top]
