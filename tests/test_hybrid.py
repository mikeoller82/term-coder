from __future__ import annotations

from pathlib import Path

from term_coder.search import HybridSearch
from term_coder.config import Config
from term_coder.generator import generate as generate_file, render_template, to_snake, to_kebab, to_camel


def test_hybrid_combines_sources(tmp_path: Path):
    (tmp_path / "x.py").write_text("def hello():\n    return 'world'\n")
    (tmp_path / "y.md").write_text("hello world documentation")

    hs = HybridSearch(tmp_path, alpha=0.5, config=Config())
    results = hs.search("hello world", top=5)
    assert results
    # should include at least one of the files
    files = [p for p, _ in results]
    assert any(p.endswith("x.py") for p in files) or any(p.endswith("y.md") for p in files)


def test_lexical_rank_and_cli_types(tmp_path: Path):
    # Create files with different extensions and repeated matches
    (tmp_path / "a.py").write_text("hello\nhello\nhello\n")
    (tmp_path / "b.md").write_text("hello once\n")

    from term_coder.search import LexicalSearch

    lex = LexicalSearch(tmp_path)
    ranked = lex.rank_files("hello", include=["**/*.py", "**/*.md"], exclude=None, top=2)
    assert ranked
    # a.py should have higher score than b.md due to more occurrences
    assert ranked[0][0].endswith("a.py")


def test_code_generation_python_module(tmp_path: Path):
    result = generate_file("python", "module", "MyFeature", out_dir=tmp_path)
    assert result.path.exists()
    assert result.validated
    content = result.path.read_text()
    assert "def my_feature_run" in content
    # Name converters
    assert to_snake("MyFeature") == "my_feature"
    assert to_kebab("MyFeature") == "my-feature"
    assert to_camel("my_feature") == "myFeature"
