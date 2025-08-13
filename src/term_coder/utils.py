from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Set

import fnmatch


DEFAULT_EXCLUDE_DIRS: Set[str] = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
    ".term-coder",
}


def is_text_file(path: Path, max_bytes: int = 4096) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(max_bytes)
        chunk.decode("utf-8")
        return True
    except Exception:
        return False


def iter_source_files(
    root: Path,
    include_globs: Iterable[str] | None = None,
    exclude_globs: Iterable[str] | None = None,
) -> Iterable[Path]:
    include_globs = list(include_globs or [])
    exclude_globs = list(exclude_globs or [])

    for path in root.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(root)
        # Skip any file that resides under an excluded directory
        if any(part in DEFAULT_EXCLUDE_DIRS for part in rel.parts[:-1]):
            continue
        rel_str = str(rel)
        if any(fnmatch.fnmatch(rel_str, g) for g in exclude_globs):
            continue
        if include_globs and not any(fnmatch.fnmatch(rel_str, g) for g in include_globs):
            continue
        yield path

