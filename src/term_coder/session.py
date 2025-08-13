from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, List, Iterable

from collections import deque
import json
from datetime import datetime

SESSION_DIR = Path(".term-coder/sessions")
RECENT_FILE_LIMIT = 100


@dataclass
class SessionMemory:
    recent_files: Deque[str] = field(default_factory=lambda: deque(maxlen=RECENT_FILE_LIMIT))

    def add_recent_file(self, path: str) -> None:
        if path in self.recent_files:
            try:
                self.recent_files.remove(path)
            except ValueError:
                pass
        self.recent_files.appendleft(path)

    def get_recent_files(self, limit: int = 20) -> List[str]:
        return list(list(self.recent_files)[:limit])

    def save(self) -> None:
        # Minimal persistence stub: write a single file with newline paths
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        (SESSION_DIR / "recent.txt").write_text("\n".join(self.recent_files))

    def load(self) -> None:
        try:
            text = (SESSION_DIR / "recent.txt").read_text()
            paths = [p for p in text.splitlines() if p]
            self.recent_files = deque(paths[:RECENT_FILE_LIMIT], maxlen=RECENT_FILE_LIMIT)
        except Exception:
            # ignore if missing
            self.recent_files = deque(maxlen=RECENT_FILE_LIMIT)


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str
    ts: str


class ChatSession:
    """JSONL-backed chat transcript for session continuity."""

    def __init__(self, name: str = "default"):
        self.name = name
        self.path = SESSION_DIR / f"{self.name}.jsonl"
        self.messages: List[Message] = []
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        self.messages = []
        try:
            text = self.path.read_text()
        except Exception:
            self._loaded = True
            return
        for line in text.splitlines():
            try:
                obj = json.loads(line)
                role = obj.get("role")
                content = obj.get("content", "")
                ts = obj.get("ts") or datetime.utcnow().isoformat()
                if role in {"user", "assistant"}:
                    self.messages.append(Message(role=role, content=content, ts=ts))
            except Exception:
                continue
        self._loaded = True

    def append(self, role: str, content: str) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("role must be 'user' or 'assistant'")
        msg = Message(role=role, content=content, ts=datetime.utcnow().isoformat())
        self.messages.append(msg)

    def save(self) -> None:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        with self.path.open("w") as f:
            for m in self.messages:
                f.write(json.dumps({"role": m.role, "content": m.content, "ts": m.ts}) + "\n")

    def history_pairs(self, limit_chars: int = 4000) -> List[tuple[str, str]]:
        """Return list of (role, content) bounded by character budget from the tail."""
        acc: List[tuple[str, str]] = []
        total = 0
        for m in reversed(self.messages):
            if total + len(m.content) > limit_chars:
                break
            acc.append((m.role, m.content))
            total += len(m.content)
        return list(reversed(acc))
