from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import contextlib

import git  # type: ignore

from .config import Config
from .llm import LLMOrchestrator


@dataclass
class RepoStatus:
    is_repo: bool
    untracked: List[str]
    staged: List[str]
    modified: List[str]


class GitIntegration:
    def __init__(self, repo_path: Optional[Path] = None):
        self.root = (repo_path or Path.cwd()).resolve()
        with contextlib.suppress(Exception):
            self.repo = git.Repo(self.root)
        if not hasattr(self, "repo"):
            raise RuntimeError(f"Not a git repository: {self.root}")

    @staticmethod
    def is_repo(path: Path) -> bool:
        try:
            _ = git.Repo(path)
            return True
        except Exception:
            return False

    def status(self) -> RepoStatus:
        untracked = list(self.repo.untracked_files)
        # Staged: index vs HEAD
        try:
            staged_diffs = self.repo.index.diff("HEAD")
            staged = sorted({d.a_path or d.b_path for d in staged_diffs if (d.a_path or d.b_path)})
        except Exception:
            staged = []
        # Modified (unstaged): working tree vs index
        wt_diffs = self.repo.index.diff(None)
        modified = sorted({d.a_path or d.b_path for d in wt_diffs if (d.a_path or d.b_path)})
        return RepoStatus(is_repo=True, untracked=untracked, staged=staged, modified=modified)

    def diff_staged(self, context_lines: int = 3) -> str:
        return self.repo.git.diff("--cached", f"-U{context_lines}")

    def diff_range(self, range_spec: str, context_lines: int = 3) -> str:
        return self.repo.git.diff(range_spec, f"-U{context_lines}")

    def changed_files_from_diff(self, diff_text: str) -> List[str]:
        files: List[str] = []
        for line in diff_text.splitlines():
            if line.startswith("+++ b/"):
                files.append(line[len("+++ b/") :].strip())
        return files

    def generate_commit_message(self, diff_text: str, cfg: Optional[Config] = None, model: Optional[str] = None) -> str:
        files = self.changed_files_from_diff(diff_text)
        add = sum(1 for l in diff_text.splitlines() if l.startswith("+") and not l.startswith("+++"))
        rem = sum(1 for l in diff_text.splitlines() if l.startswith("-") and not l.startswith("---"))
        heuristic = f"update {' ,'.join(files[:3])}{' and others' if len(files)>3 else ''} (+{add} -{rem})"
        cfg = cfg or Config()
        if bool(cfg.get("privacy.offline", False)):
            return heuristic
        try:
            orch = LLMOrchestrator()
            prompt = (
                "Summarize the following diff as a concise, imperative commit message (<= 72 chars).\n\n"
                + diff_text[:12000]
            )
            resp = orch.complete(prompt, model=model)
            text = resp.text.strip().splitlines()[0]
            return text or heuristic
        except Exception:
            return heuristic

    def review_changes(self, diff_text: str, cfg: Optional[Config] = None, model: Optional[str] = None) -> str:
        files = self.changed_files_from_diff(diff_text)
        header = "Changed files:\n- " + "\n- ".join(files) if files else "No file list available"
        cfg = cfg or Config()
        if bool(cfg.get("privacy.offline", False)):
            return header

    def generate_pr_description(self, diff_text: str, cfg: Optional[Config] = None, model: Optional[str] = None) -> str:
        files = self.changed_files_from_diff(diff_text)
        header = ["## Summary", f"- Changes across {len(files)} files" if files else "- Changes detected"]
        header.append("\n## Files\n" + "\n".join(f"- {f}" for f in files[:50]))
        cfg = cfg or Config()
        if bool(cfg.get("privacy.offline", False)):
            header.append("\n## Risks\n- Offline mode: unable to analyze risks with model")
            header.append("\n## Test plan\n- Run unit tests: `tc test`\n- Manual validation of critical paths")
            return "\n".join(header)
        try:
            orch = LLMOrchestrator()
            prompt = (
                "Create a pull request description with sections: Summary, Risks, and Test plan.\n\n"
                + diff_text[:12000]
            )
            resp = orch.complete(prompt, model=model)
            return "\n".join(header) + "\n\n" + resp.text
        except Exception:
            header.append("\n## Risks\n- N/A")
            header.append("\n## Test plan\n- N/A")
            return "\n".join(header)

    # --- Mutating operations ---
    def stage_files(self, paths: Optional[List[str]] = None, all_changes: bool = False) -> None:
        if all_changes:
            self.repo.git.add("-A")
        elif paths:
            self.repo.index.add(paths)

    def commit(self, message: str) -> str:
        c = self.repo.index.commit(message)
        return c.hexsha


