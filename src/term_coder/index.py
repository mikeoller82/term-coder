from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from .config import Config
from .utils import iter_source_files, is_text_file
from .semantic import SemanticIndexer, create_embedding_model_from_config


INDEX_FILE = Path(".term-coder/index.tsv")


@dataclass
class IndexStats:
    total_files: int
    indexed_files: int
    semantic_vectors: int = 0


class IndexSystem:
    def __init__(self, config: Config):
        self.config = config
        # Create embedding model from configuration so semantic indexing
        # respects user settings (backend, model, keys).
        model = create_embedding_model_from_config(config)
        self._semantic_indexer = SemanticIndexer(model)

    def build_index(self, root: Path, include: Iterable[str] | None = None, exclude: Iterable[str] | None = None) -> IndexStats:
        lines: List[str] = []
        total = 0
        indexed = 0
        root = root.resolve()
        for path in iter_source_files(root, include_globs=include, exclude_globs=exclude):
            total += 1
            if not is_text_file(path):
                continue
            indexed += 1
            rel = path.relative_to(root)
            size = path.stat().st_size
            lines.append(f"{rel}\t{size}")

        INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        INDEX_FILE.write_text("\n".join(lines))

        # Build/update semantic vectors as part of indexing (best-effort)
        vectors_built = 0
        try:
            # Rebuild vectors fully to reflect include/exclude scope
            vectors_built = self._semantic_indexer.build(root, include=include, exclude=exclude, reset=True)
        except Exception:
            # Non-fatal; semantic search remains optional
            vectors_built = 0

        return IndexStats(total_files=total, indexed_files=indexed, semantic_vectors=vectors_built)

