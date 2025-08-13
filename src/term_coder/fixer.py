from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import json
import re

from .config import Config
from .editor import generate_edit_proposal, PendingEdit
from .llm import LLMOrchestrator


LAST_RUN_FILE = Path(".term-coder/last_run.json")


@dataclass
class FixSuggestion:
    kind: str  # "command" | "edit" | "none"
    rationale: str
    command: Optional[str] = None
    pending_edit: Optional[PendingEdit] = None


def _read_last_run() -> Optional[Dict]:
    try:
        return json.loads(LAST_RUN_FILE.read_text())
    except Exception:
        return None


def _heuristic_fix(last: Dict) -> FixSuggestion:
    stderr = (last.get("stderr") or "") + "\n" + (last.get("stdout") or "")
    # ModuleNotFoundError pattern (Python)
    m = re.search(r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]", stderr)
    if m:
        pkg = m.group(1)
        return FixSuggestion(
            kind="command",
            command=f"pip install {pkg}",
            rationale=f"Detected missing Python module '{pkg}'. Installing it should resolve the import error.",
        )

    # Command not found (shell)
    m = re.search(r"(?:command not found|: not found)[:]*\s*([\w\-]+)", stderr)
    if m:
        cmd = m.group(1)
        return FixSuggestion(
            kind="command",
            command=f"# Install or add to PATH: {cmd}",
            rationale=f"Shell reports '{cmd}' not found. Install it or ensure it is on PATH.",
        )

    # SyntaxError reference with file and line
    m = re.search(r"File\s+['\"](.+?)['\"],\s+line\s+(\d+).+?\n\s*SyntaxError", stderr, re.DOTALL)
    if m:
        file_path = m.group(1)
        line_no = m.group(2)
        return FixSuggestion(
            kind="command",
            command=f"# Fix syntax at {file_path}:{line_no}",
            rationale="Detected Python SyntaxError. Review and correct the code at the indicated line.",
        )

    return FixSuggestion(kind="none", rationale="No specific heuristic matched.")


def generate_fix(cfg: Optional[Config] = None, use_last_run: bool = True) -> FixSuggestion:
    cfg = cfg or Config()
    last = _read_last_run() if use_last_run else None
    if not last:
        return FixSuggestion(kind="none", rationale="No last run logs found.")

    # If offline is disabled, try LLM-based structured fix first
    if not bool(cfg.get("privacy.offline", False)):
        orch = LLMOrchestrator(offline=False)
        prompt = (
            "You are a build & runtime fixer. Given the last command output, propose a minimal fix.\n"
            "Return strict JSON with either a command to run OR explicit full new file contents.\n"
            "Schema: {\n  \"kind\": \"command\"|\"edit\",\n  \"rationale\": \"...\",\n  \"command\": \"...\" (when kind=command),\n  \"changes\": {\"path\": \"<full new content>\"} (when kind=edit)\n}\n"
            f"Exit: {last.get('exit_code')}\nSTDERR:\n{last.get('stderr','')[:4000]}\n\nSTDOUT:\n{last.get('stdout','')[:2000]}\n"
        )
        text = "".join(list(orch.stream(prompt)))
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                obj = json.loads(text[start : end + 1])
                kind = obj.get("kind")
                rationale = obj.get("rationale") or ""
                if kind == "command" and obj.get("command"):
                    return FixSuggestion(kind="command", rationale=rationale, command=str(obj.get("command")))
                if kind == "edit" and obj.get("changes"):
                    changes = {str(k): str(v) for k, v in (obj.get("changes") or {}).items()}
                    files = list(changes.keys())
                    pe = generate_edit_proposal("Fix runtime error", files, cfg, use_llm=False)
                    # overwrite new contents using LLM-provided changes
                    if pe:
                        pe.proposal.new_contents = changes
                        from .patcher import PatchSystem

                        ps = PatchSystem(Path.cwd(), cfg)
                        pe.proposal = ps.propose_from_changes(pe.instruction, changes, rationale=rationale or pe.proposal.rationale)
                        return FixSuggestion(kind="edit", rationale=rationale, pending_edit=pe)
        except Exception:
            pass

    # Fallback heuristic suggestion
    return _heuristic_fix(last)
