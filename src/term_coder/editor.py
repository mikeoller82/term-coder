from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import json
import re
import contextlib

from .config import Config
from .patcher import PatchSystem, PatchProposal


PENDING_FILE = Path(".term-coder/pending_edit.json")


@dataclass
class PendingEdit:
    instruction: str
    proposal: PatchProposal


def save_pending(pending: PendingEdit) -> None:
    PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    obj = {
        "instruction": pending.instruction,
        "proposal": {
            "instruction": pending.proposal.instruction,
            "diff": pending.proposal.diff,
            "rationale": pending.proposal.rationale,
            "affected_files": pending.proposal.affected_files,
            "safety_score": pending.proposal.safety_score,
            "estimated_impact": {
                "files_changed": pending.proposal.estimated_impact.files_changed,
                "lines_added": pending.proposal.estimated_impact.lines_added,
                "lines_removed": pending.proposal.estimated_impact.lines_removed,
            },
            "new_contents": pending.proposal.new_contents or {},
        },
    }
    PENDING_FILE.write_text(json.dumps(obj, indent=2))


def load_pending() -> Optional[PendingEdit]:
    if not PENDING_FILE.exists():
        return None
    try:
        obj = json.loads(PENDING_FILE.read_text())
        from .patcher import ImpactAssessment

        prop = obj.get("proposal", {})
        impact = ImpactAssessment(
            files_changed=int(prop.get("estimated_impact", {}).get("files_changed", 0)),
            lines_added=int(prop.get("estimated_impact", {}).get("lines_added", 0)),
            lines_removed=int(prop.get("estimated_impact", {}).get("lines_removed", 0)),
        )
        proposal = PatchProposal(
            instruction=prop.get("instruction", ""),
            diff=prop.get("diff", ""),
            rationale=prop.get("rationale", ""),
            affected_files=list(prop.get("affected_files", [])),
            safety_score=float(prop.get("safety_score", 0.0)),
            estimated_impact=impact,
            new_contents=dict(prop.get("new_contents", {})),
        )
        return PendingEdit(instruction=obj.get("instruction", ""), proposal=proposal)
    except Exception:
        return None


def clear_pending() -> None:
    with contextlib.suppress(Exception):
        PENDING_FILE.unlink()


def _apply_simple_instruction(instruction: str, files: List[str], root: Path) -> Dict[str, str]:
    """Heuristic non-LLM instruction processor for offline use.

    Supports patterns:
      - append 'TEXT' to <file>
      - prepend 'TEXT' to <file>
      - replace 'A' -> 'B' in <file>
    Only operates on files listed in `files` for safety.
    """
    changes: Dict[str, str] = {}
    for rel in files:
        p = (root / rel).resolve()
        try:
            original = p.read_text()
        except Exception:
            original = ""

        # replace
        m = re.search(r"replace\s+'(.+?)'\s*->\s*'(.+?)'", instruction, re.IGNORECASE)
        if m:
            a, b = m.group(1), m.group(2)
            changes[rel] = original.replace(a, b)
            continue

        # append
        m = re.search(r"append\s+'(.+?)'", instruction, re.IGNORECASE)
        if m:
            text = m.group(1)
            changes[rel] = original + ("\n" if not original.endswith("\n") else "") + text + "\n"
            continue

        # prepend
        m = re.search(r"prepend\s+'(.+?)'", instruction, re.IGNORECASE)
        if m:
            text = m.group(1)
            changes[rel] = text + "\n" + original
            continue

    return changes


def generate_edit_proposal(
    instruction: str,
    files: List[str],
    cfg: Optional[Config] = None,
    use_llm: bool = True,
) -> Optional[PendingEdit]:
    """Generate a PatchProposal from an instruction and target files.

    If use_llm is True and a real LLM is available (API keys, online), delegates to LLM;
    otherwise applies limited deterministic transformations to the specified files.
    """
    cfg = cfg or Config()
    root = Path.cwd().resolve()
    ps = PatchSystem(root, cfg)

    changes: Dict[str, str] = {}

    if use_llm:
        # Prepare an instruction for the model to update the full files and return JSON
        from .prompts import render_chat_prompt
        from .context import ContextSelection, ContextFile
        from .llm import LLMOrchestrator

        # Build minimal context from the files
        ctx = ContextSelection(files=[ContextFile(path=f, relevance_score=1.0) for f in files])
        system_user = (
            "Modify the following repository files to satisfy the user's instruction. "
            "Return a JSON object with exact new file contents as: {\"changes\": {\"path\": \"<full new content>\"}, \"rationale\": \"why\"}. "
            "Do not include code fences or extra commentary."
        )
        rp = render_chat_prompt(system_user + "\n\nInstruction: " + instruction, ctx, max_context_chars=64000)

        orch = LLMOrchestrator(offline=bool(cfg.get("privacy.offline", False)))
        text = "".join(list(orch.stream(rp.user)))

        # Try to extract JSON object
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                obj = json.loads(text[start : end + 1])
                changes = {str(k): str(v) for k, v in (obj.get("changes") or {}).items()}
                rationale = str(obj.get("rationale") or "")
            else:
                changes = {}
                rationale = ""
        except Exception:
            changes = {}
            rationale = ""

        if not changes:
            # Fall back to simple deterministic transforms
            changes = _apply_simple_instruction(instruction, files, root)
            rationale = rationale or "Applied deterministic transformations based on instruction."
    else:
        rationale = "Applied deterministic transformations based on instruction."
        changes = _apply_simple_instruction(instruction, files, root)

    if not changes:
        return None

    proposal = ps.propose_from_changes(instruction, changes, rationale=rationale)
    return PendingEdit(instruction=instruction, proposal=proposal)
