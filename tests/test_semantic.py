from __future__ import annotations

from pathlib import Path

from term_coder.semantic import SimpleHashEmbeddingModel, SemanticIndexer, SemanticSearch
from term_coder.refactor import RefactorEngine
from term_coder.patcher import DiffBuilder, DiffAnalyzer, PatchSystem


def test_simple_hash_embedding_stability():
    model = SimpleHashEmbeddingModel()
    v1 = model.embed_text("hello world")
    v2 = model.embed_text("hello world")
    assert v1 == v2
    assert abs(sum(x * x for x in v1) - 1.0) < 1e-6


def test_semantic_index_and_search(tmp_path: Path):
    # create small files
    (tmp_path / "a.txt").write_text("alpha beta gamma")
    (tmp_path / "b.txt").write_text("beta gamma delta")
    (tmp_path / "c.txt").write_text("unrelated content")

    indexer = SemanticIndexer(model=SimpleHashEmbeddingModel())
    count = indexer.build(tmp_path)
    assert count == 3

    search = SemanticSearch(tmp_path, model=SimpleHashEmbeddingModel())
    results = search.search("alpha gamma", top_k=2)
    assert len(results) == 2
    # a.txt should rank higher than unrelated
    assert results[0][0] in {"a.txt", "b.txt"}


def test_diff_builder_and_analyzer(tmp_path: Path):
    old = tmp_path / "file.txt"
    old.write_text("line1\nline2\n")

    # Build diff against current workspace by creating builder rooted at tmp_path
    builder = DiffBuilder(tmp_path)
    diff = builder.build({"file.txt": "line1\nline2 changed\nnew\n"})
    assert "+++ b/file.txt" in diff
    files, impact = DiffAnalyzer.analyze(diff)
    assert files == ["file.txt"]
    assert impact.lines_added >= 1 and impact.lines_removed >= 1

    ps = PatchSystem(tmp_path)
    proposal = ps.propose_from_changes("update file", {"file.txt": "line1\nline2 changed\nnew\n"})
    assert proposal.diff
    assert proposal.safety_score >= 0 and proposal.safety_score <= 1
    # Apply and rollback
    ok, backup_id = ps.apply_patch(proposal)
    assert ok and backup_id
    # Now rollback should restore previous content
    assert ps.rollback(backup_id)
    assert (tmp_path / "file.txt").read_text() == "line1\nline2\n"


def test_token_aware_refactor_rename(tmp_path: Path):
    code = """\
def foo():
    bar = 1  # foo in comment should not change
    s = "foo in string"
    return bar
"""
    p = tmp_path / "a.py"
    p.write_text(code)
    engine = RefactorEngine(tmp_path)
    plan = engine.rename_symbol_python("foo", "baz")
    # Should replace def foo -> def baz but not string/comment
    assert plan.safety.files_changed == 1
    assert any(cs.replacements >= 1 for cs in plan.change_stats)
