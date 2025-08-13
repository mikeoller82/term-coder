from __future__ import annotations

from term_coder.llm import LLMOrchestrator
from term_coder.prompts import render_chat_prompt
from term_coder.context import ContextSelection, ContextFile
from term_coder.explain import parse_target, read_snippet


def test_mock_orchestrator_complete():
    orch = LLMOrchestrator()
    resp = orch.complete("Hello")
    assert "MOCK" in resp.text


def test_mock_orchestrator_stream():
    orch = LLMOrchestrator()
    chunks = list(orch.stream("Hello world"))
    assert chunks
    assert any("MOCK" in c for c in chunks)


def test_render_chat_prompt_with_history():
    ctx = ContextSelection(files=[ContextFile(path="a.txt", relevance_score=0.9)])
    rp = render_chat_prompt("Hi", ctx, history=[("user", "prev Q"), ("assistant", "prev A")])
    assert "<history>" in rp.user
    assert "# File: a.txt" in rp.user


def test_parse_target_and_read_snippet(tmp_path):
    p = tmp_path / "m.py"
    p.write_text("""\
def alpha():
    pass

class Beta:
    def gamma(self):
        return 1
""")
    spec = parse_target(str(p) + "#Beta")
    snippet, s, e = read_snippet(spec)
    assert "class Beta" in snippet
