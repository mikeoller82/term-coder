from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Optional

import difflib
import re
import shutil
import time

from .utils import is_text_file
from .config import Config


@dataclass
class ImpactAssessment:
    files_changed: int
    lines_added: int
    lines_removed: int


@dataclass
class PatchProposal:
    instruction: str
    diff: str
    rationale: str
    affected_files: List[str]
    safety_score: float
    estimated_impact: ImpactAssessment
    new_contents: Optional[Dict[str, str]] = None


class DiffBuilder:
    """Create unified diffs for proposed file changes.

    Changes are provided as a mapping of relative file path -> new content.
    """

    def __init__(self, root: Path):
        self.root = root.resolve()

    def _read_original(self, rel_path: str) -> List[str]:
        p = (self.root / rel_path).resolve()
        # Guard path traversal
        if not str(p).startswith(str(self.root)):
            return []
        try:
            if not p.exists():
                return []
            if not is_text_file(p):
                return []
            return p.read_text(errors="ignore").splitlines(keepends=True)
        except Exception:
            return []

    def build(self, changes: Dict[str, str], context_lines: int = 3) -> str:
        parts: List[str] = []
        for rel_path, new_content in changes.items():
            original_lines = self._read_original(rel_path)
            new_lines = list(new_content.splitlines(keepends=True))
            # Normalize header paths as relative
            old_header = f"a/{rel_path}"
            new_header = f"b/{rel_path}"
            diff_lines = list(
                difflib.unified_diff(
                    original_lines,
                    new_lines,
                    fromfile=old_header,
                    tofile=new_header,
                    lineterm="",
                    n=context_lines,
                )
            )
            if diff_lines:
                parts.append("\n".join(diff_lines))
        return "\n\n".join(parts)


class DiffAnalyzer:
    """Parse unified diff and compute impacted files and line stats."""

    FILE_RE = re.compile(r"^\+\+\+\s+b/(.+)$")

    @classmethod
    def analyze(cls, diff_text: str) -> Tuple[List[str], ImpactAssessment]:
        files: List[str] = []
        added = 0
        removed = 0
        current_file: str | None = None
        for line in diff_text.splitlines():
            if line.startswith("+++ "):
                m = cls.FILE_RE.match(line)
                if m:
                    current_file = m.group(1)
                    if current_file not in files:
                        files.append(current_file)
                continue
            if not current_file:
                continue
            if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
                continue
            if line.startswith("+"):
                added += 1
            elif line.startswith("-"):
                removed += 1
        impact = ImpactAssessment(files_changed=len(files), lines_added=added, lines_removed=removed)
        return files, impact


class SafetyScorer:
    """Compute a coarse safety score in [0,1] based on diff size and scope."""

    def __init__(self, max_files: int = 50, max_lines: int = 2000):
        self.max_files = max_files
        self.max_lines = max_lines

    def score(self, impact: ImpactAssessment) -> float:
        # Two factors: file scope and line magnitude; combine multiplicatively
        file_factor = max(0.0, 1.0 - (impact.files_changed / max(1, self.max_files)))
        line_total = impact.lines_added + impact.lines_removed
        line_factor = max(0.0, 1.0 - (line_total / max(1, self.max_lines)))
        # Slight bias toward safer scores
        return max(0.0, min(1.0, 0.2 + 0.8 * (0.5 * file_factor + 0.5 * line_factor)))


class PatchSystem:
    def __init__(self, root: Path | None = None, config: Optional[Config] = None):
        self.root = (root or Path.cwd()).resolve()
        self.builder = DiffBuilder(self.root)
        self.analyzer = DiffAnalyzer()
        self.scorer = SafetyScorer()
        self.config = config or Config()

    # -------- Backup & rollback --------
    def create_backup(self, files: Iterable[str]) -> str:
        backup_id = str(int(time.time() * 1000))
        backup_root = self.root / ".term-coder" / "backups" / backup_id
        for rel in files:
            src = (self.root / rel).resolve()
            if not str(src).startswith(str(self.root)):
                continue
            if not src.exists() or not src.is_file():
                continue
            dst = backup_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(src, dst)
            except Exception:
                # best effort
                pass
        return backup_id

    def rollback(self, backup_id: str) -> bool:
        backup_root = self.root / ".term-coder" / "backups" / backup_id
        if not backup_root.exists():
            return False
        # Restore all files contained in backup
        for src in backup_root.rglob("*"):
            if src.is_dir():
                continue
            rel = src.relative_to(backup_root)
            dst = (self.root / rel).resolve()
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(src, dst)
            except Exception:
                return False
        return True

    def propose_from_changes(self, instruction: str, changes: Dict[str, str], rationale: str = "") -> PatchProposal:
        """Create a PatchProposal from explicit file content changes.

        This method is side-effect-free (does not write to disk).
        """
        diff_text = self.builder.build(changes)
        files, impact = self.analyzer.analyze(diff_text)
        safety = self.scorer.score(impact)
        return PatchProposal(
            instruction=instruction,
            diff=diff_text,
            rationale=rationale or "Proposed changes derived from explicit edits.",
            affected_files=files,
            safety_score=safety,
            estimated_impact=impact,
            new_contents=dict(changes),
        )

    # -------- Apply patch --------
    def _run_formatters(self, paths: List[str]) -> None:
        fmt_cfg = self.config.get("formatters", {}) or {}
        # naive mapping by extension
        for rel in paths:
            ext = Path(rel).suffix.lstrip(".")
            if not ext:
                continue
            tools = []
            if ext == "py":
                tools = fmt_cfg.get("python", []) or []
            elif ext in {"js", "ts", "jsx", "tsx"}:
                tools = fmt_cfg.get("javascript", []) or []
            elif ext == "go":
                tools = fmt_cfg.get("go", []) or []
            for tool in tools:
                exe = shutil.which(tool)
                if not exe:
                    continue
                try:
                    # Run formatter in-place; ignore failures to keep non-fatal
                    import subprocess

                    subprocess.run([exe, str(self.root / rel)], check=False)
                except Exception:
                    continue

    def apply_patch(
        self,
        proposal: PatchProposal,
        pick_hunks: Optional[Dict[str, List[int]]] = None,
        create_backup: bool = True,
        run_formatters: bool = True,
        unsafe: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """Apply the proposed patch. Returns (success, backup_id).

        Note: hunk-level selection is ignored unless new contents are provided.
        When new_contents are present, we apply full-file replacements for the
        selected files (or all affected files when pick_hunks is None).
        """
        # Determine files to apply
        affected = list(proposal.affected_files)
        backup_id: Optional[str] = None
        # Safety: require files to be within root; if unsafe is False and file does not exist, skip
        apply_list: List[str] = []
        for rel in affected:
            p = (self.root / rel).resolve()
            if not str(p).startswith(str(self.root)):
                continue
            if (not unsafe) and (not p.exists()):
                continue
            apply_list.append(rel)

        if not apply_list:
            return False, None

        if create_backup:
            backup_id = self.create_backup(apply_list)

        # If we have exact new contents, write them; otherwise, fail for now
        if proposal.new_contents is None:
            # Future: parse and apply hunks. For now, we require new_contents.
            return False, backup_id

        for rel in apply_list:
            new_text = proposal.new_contents.get(rel)
            if new_text is None:
                # If not provided, skip this file
                continue
            dst = (self.root / rel).resolve()
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(new_text)

        if run_formatters:
            try:
                self._run_formatters(apply_list)
            except Exception:
                pass

        return True, backup_id

