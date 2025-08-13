from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Callable

import io
import re
import tokenize

from .utils import iter_source_files
from .patcher import PatchSystem, PatchProposal


@dataclass
class RefactorChange:
    path: str
    replacements: int


@dataclass
class SafetyReport:
    files_changed: int
    total_replacements: int
    max_files_allowed: int
    ok: bool
    notes: List[str]


@dataclass
class RefactorPlan:
    template: str
    old: str
    new: str
    include: List[str]
    exclude: List[str]
    changes: Dict[str, str]
    change_stats: List[RefactorChange]
    safety: SafetyReport
    proposal: Optional[PatchProposal] = None


def _rename_tokens_python(source: str, old: str, new: str) -> Tuple[str, int]:
    """Rename identifier tokens exactly matching 'old' to 'new'.

    Does not modify strings or comments, only NAME tokens.
    Returns (new_source, num_replacements).
    """
    replaced = 0
    out: List[Tuple[int, str]] = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except tokenize.TokenError:
        # Fallback to regex word-boundary replace if tokenization fails
        pattern = re.compile(rf"\b{re.escape(old)}\b")
        new_text, replaced = pattern.subn(new, source)
        return new_text, replaced

    for tok in tokens:
        tok_type, tok_str, start, end, line = tok
        if tok_type == tokenize.NAME and tok_str == old:
            out.append((tok_type, new))
            replaced += 1
        else:
            out.append((tok_type, tok_str))

    # Reconstruct using untokenize
    rebuilt = tokenize.untokenize(out)
    return rebuilt, replaced


class RefactorEngine:
    def __init__(self, root: Optional[Path] = None):
        self.root = (root or Path.cwd()).resolve()

    def rename_symbol_python(
        self,
        old: str,
        new: str,
        include: Optional[Iterable[str]] = None,
        exclude: Optional[Iterable[str]] = None,
        max_files: int = 200,
    ) -> RefactorPlan:
        include = list(include or ["**/*.py", "*.py"])
        exclude = list(exclude or [])
        changes: Dict[str, str] = {}
        change_stats: List[RefactorChange] = []
        total_replacements = 0
        notes: List[str] = []

        for path in iter_source_files(self.root, include_globs=include, exclude_globs=exclude):
            rel = str(path.relative_to(self.root))
            try:
                text = path.read_text()
            except Exception:
                continue
            new_text, replaced = _rename_tokens_python(text, old, new)
            if replaced > 0:
                changes[rel] = new_text
                change_stats.append(RefactorChange(path=rel, replacements=replaced))
                total_replacements += replaced
                if len(changes) > max_files:
                    notes.append(f"Aborting: exceeded max_files limit {max_files}.")
                    break

        safety = SafetyReport(
            files_changed=len(changes),
            total_replacements=total_replacements,
            max_files_allowed=max_files,
            ok=(len(changes) <= max_files and len(changes) > 0),
            notes=notes,
        )

        plan = RefactorPlan(
            template="rename_symbol_python",
            old=old,
            new=new,
            include=list(include),
            exclude=list(exclude),
            changes=changes,
            change_stats=change_stats,
            safety=safety,
        )

        # Build proposal diff
        ps = PatchSystem(self.root)
        plan.proposal = ps.propose_from_changes(
            instruction=f"Rename symbol {old} -> {new}",
            changes=changes,
            rationale="Rename applied to Python NAME tokens only; strings/comments left unchanged.",
        )
        return plan

    def apply_and_validate(
        self,
        plan: RefactorPlan,
        run_tests: bool = True,
        test_runner: Optional[Callable[[], Tuple[int, int]]] = None,
    ) -> Tuple[bool, Optional[str], Optional[Tuple[int, int]]]:
        """Apply the refactor plan via PatchSystem. Optionally run tests.

        test_runner: optional callback returning (failed, passed) for validation.
        Returns (applied_ok, backup_id, test_result)
        """
        if not plan.proposal or not plan.changes:
            return False, None, None
        ps = PatchSystem(self.root)
        ok, backup_id = ps.apply_patch(plan.proposal, unsafe=True)
        if not ok:
            return False, backup_id, None

        if run_tests:
            if test_runner is not None:
                result = test_runner()
                failed, passed = result
            else:
                # Use built-in tester
                from .tester import run_tests

                report = run_tests()
                failed, passed = report.failed, report.passed
            if failed > 0:
                # Rollback
                if backup_id:
                    ps.rollback(backup_id)
                return False, backup_id, (failed, passed)
            return True, backup_id, (failed, passed)
        return True, backup_id, None
