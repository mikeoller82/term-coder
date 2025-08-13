from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import json
import math

from .utils import iter_source_files, is_text_file


VECTORS_FILE = Path(".term-coder/vectors.jsonl")


class EmbeddingModel:
    """Abstract embedding model interface.

    Lightweight interface so we can swap to real providers later without
    changing call sites. For now, we ship a deterministic local hash-based
    implementation that requires no external dependencies.
    """

    def __init__(self, dimension: int = 768):
        self.dimension = dimension

    def embed_text(self, text: str) -> List[float]:
        raise NotImplementedError


class SimpleHashEmbeddingModel(EmbeddingModel):
    """Very simple embedding using token hashing into a fixed-size bag-of-words.

    This is NOT semantic in a deep sense but serves as an offline-compatible
    stand-in until real embeddings are wired. It is deterministic, fast, and
    provides useful approximate similarity via cosine.
    """

    def __init__(self, dimension: int = 768):
        super().__init__(dimension)

    def embed_text(self, text: str) -> List[float]:
        vec = [0.0] * self.dimension
        # Simple tokenization by whitespace; lowercase for stability
        for raw_token in text.lower().split():
            # strip common punctuations
            token = raw_token.strip("\t\n\r.,;:()[]{}'\"`<>=+-/*\\|!?")
            if not token:
                continue
            idx = hash(token) % self.dimension
            vec[idx] += 1.0
        # L2 normalize to stabilize cosine similarity
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    # assume both are normalized
    length = min(len(a), len(b))
    return sum(a[i] * b[i] for i in range(length))


@dataclass
class VectorEntry:
    path: str
    vector: List[float]


class VectorStore:
    """Very small JSONL-backed vector store for file-level embeddings."""

    def __init__(self):
        self.path_to_vector: Dict[str, List[float]] = {}
        if VECTORS_FILE.exists():
            for line in VECTORS_FILE.read_text().splitlines():
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict) and "path" in obj and "vector" in obj:
                        self.path_to_vector[obj["path"]] = obj["vector"]
                except Exception:
                    continue

    def upsert(self, entries: Iterable[VectorEntry]) -> None:
        # Update memory
        for e in entries:
            self.path_to_vector[e.path] = e.vector
        # Persist all (rewrite small file for simplicity and consistency)
        VECTORS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with VECTORS_FILE.open("w") as f:
            for path, vector in self.path_to_vector.items():
                f.write(json.dumps({"path": path, "vector": vector}) + "\n")

    def query(self, query_vector: List[float], top_k: int = 20, include: List[str] | None = None) -> List[Tuple[str, float]]:
        include = include or []
        results: List[Tuple[str, float]] = []
        for path, vector in self.path_to_vector.items():
            if include and not any(Path(path).match(g) for g in include):
                continue
            score = cosine_similarity(query_vector, vector)
            results.append((path, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


class SemanticIndexer:
    """Builds file-level embeddings using an embedding model."""

    def __init__(self, model: EmbeddingModel | None = None):
        self.model = model or SimpleHashEmbeddingModel()
        self.vectors = VectorStore()

    def build(self, root: Path, include: Iterable[str] | None = None, exclude: Iterable[str] | None = None) -> int:
        root = root.resolve()
        entries: List[VectorEntry] = []
        for path in iter_source_files(root, include_globs=include, exclude_globs=exclude):
            try:
                if not is_text_file(path):
                    continue
                text = path.read_text(errors="ignore")
                # Truncate extremely large files to keep things light
                if len(text) > 200_000:
                    text = text[:200_000]
                vec = self.model.embed_text(text)
                rel = str(path.relative_to(root))
                entries.append(VectorEntry(path=rel, vector=vec))
            except Exception:
                continue
        if entries:
            self.vectors.upsert(entries)
        return len(entries)

    def ensure_built(self, root: Path) -> None:
        # If vector store is empty, construct it from index scope
        if not self.vectors.path_to_vector:
            self.build(root)


class SemanticSearch:
    def __init__(self, root: Path, model: EmbeddingModel | None = None):
        self.root = root.resolve()
        self.model = model or SimpleHashEmbeddingModel()
        self.indexer = SemanticIndexer(self.model)

    def search(self, query: str, top_k: int = 20, include: Iterable[str] | None = None, exclude: Iterable[str] | None = None) -> List[Tuple[str, float]]:
        # Make sure we have vectors
        self.indexer.ensure_built(self.root)
        qv = self.model.embed_text(query)
        # Optionally filter by include globs. Exclude handled during build; we filter on include only here.
        return self.indexer.vectors.query(qv, top_k=top_k, include=list(include or []))
