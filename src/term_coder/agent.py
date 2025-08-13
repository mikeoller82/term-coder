from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import re

from .search import LexicalSearch
from .utils import iter_source_files


@dataclass
class AgentReport:
    title: str
    summary: str
    findings: List[str]
    details: str


class RepoAgent:
    """Heuristic natural-language intent handler for repo analysis.

    Focuses on common developer intents like checking for placeholder data or
    verifying use of real AI endpoints within "ai-agents" code.
    """

    PLACEHOLDER_PATTERNS = [
        r"\bTODO\b",
        r"\bFIXME\b",
        r"\bplaceholder\b",
        r"\bdummy\b",
        r"\bmock\b",
        r"<YOUR[\w_\- ]*>",
        r"REPLACE[_-]?ME",
        r"changeme",
        r"example(_|-)key",
        r"api[_-]?key\s*=\s*[\"'](?:xxx|your|test|placeholder)[^\"']*[\"']",
    ]

    AI_ENDPOINT_PATTERNS = [
        r"https?://[\w\.-]+/v\d+/[\w/\-]+",  # generic versioned API paths
        r"openai|anthropic|ollama|cohere|groq|azure|gemini|vertex|huggingface|bedrock",
        r"/chat/completions|/messages|/v1/",
    ]

    AGENT_DIR_HINTS = ["ai-agent", "ai_agents", "agents", "agent"]

    def __init__(self, root: Optional[Path] = None):
        self.root = (root or Path.cwd()).resolve()
        self.lex = LexicalSearch(self.root)

    def detect_intent(self, prompt: str) -> str:
        p = prompt.lower()
        if any(k in p for k in ["check", "scan", "audit", "verify"]) and any(
            k in p for k in ["agent", "ai-agent", "ai agents", "ai-agents"]
        ):
            if any(k in p for k in ["placeholder", "dummy", "mock"]) or any(
                k in p for k in ["endpoint", "api", "provider", "openai", "anthropic"]
            ):
                return "CHECK_AI_AGENTS"
        return "UNKNOWN"

    def _gather_candidate_files(self) -> List[str]:
        # Prefer directories that look like agents
        includes: List[str] = []
        for h in self.AGENT_DIR_HINTS:
            includes.append(f"**/*{h}*/*")
            includes.append(f"**/*{h}*.py")
            includes.append(f"**/{h}/**/*")

        files: List[str] = []
        for p in iter_source_files(self.root, include_globs=includes):
            try:
                files.append(str(p.relative_to(self.root)))
            except Exception:
                files.append(str(p))
        # Fallback: if nothing found, scan top lexical results for 'agent'
        if not files:
            hits = self.lex.rank_files("agent", include=None, exclude=None, top=50)
            files = [f for f, _ in hits]
        return files

    def _scan_file(self, rel_path: str) -> Tuple[List[Tuple[int, str]], List[Tuple[int, str]]]:
        path = self.root / rel_path
        try:
            text = path.read_text(errors="ignore")
        except Exception:
            return ([], [])
        placeholders: List[Tuple[int, str]] = []
        endpoints: List[Tuple[int, str]] = []
        lines = text.splitlines()
        for idx, line in enumerate(lines, start=1):
            for pat in self.PLACEHOLDER_PATTERNS:
                if re.search(pat, line, re.IGNORECASE):
                    placeholders.append((idx, line.strip()))
                    break
            for pat in self.AI_ENDPOINT_PATTERNS:
                if re.search(pat, line, re.IGNORECASE):
                    endpoints.append((idx, line.strip()))
                    break
        return (placeholders, endpoints)

    def handle_query(self, prompt: str) -> Optional[AgentReport]:
        if self.detect_intent(prompt) != "CHECK_AI_AGENTS":
            return None

        candidates = self._gather_candidate_files()
        findings: List[str] = []
        total_placeholder = 0
        total_endpoints = 0
        for rel in candidates:
            ph, ep = self._scan_file(rel)
            if not ph and not ep:
                continue
            total_placeholder += len(ph)
            total_endpoints += len(ep)
            if ph:
                findings.append(f"[placeholder] {rel} ({len(ph)} hits)")
                for ln, txt in ph[:5]:
                    findings.append(f"  L{ln}: {txt}")
            if ep:
                findings.append(f"[endpoint] {rel} ({len(ep)} hits)")
                for ln, txt in ep[:5]:
                    findings.append(f"  L{ln}: {txt}")

        if not findings:
            return AgentReport(
                title="AI agent audit",
                summary="No placeholder markers or AI endpoints were detected in likely agent files.",
                findings=[],
                details="",
            )

        summary = (
            f"Found {total_placeholder} placeholder markers and {total_endpoints} AI endpoint references across {len(candidates)} candidate files."
        )
        details = "\n".join(findings)
        return AgentReport(
            title="AI agent audit",
            summary=summary,
            findings=findings,
            details=details,
        )
