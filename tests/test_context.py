from __future__ import annotations

from pathlib import Path

from term_coder.context import ContextEngine
from term_coder.config import Config
from term_coder.runner import CommandRunner


def test_context_respects_token_budget(tmp_path: Path):
    # Create files of different sizes
    (tmp_path / "small.txt").write_text("a" * 100)
    (tmp_path / "large.txt").write_text("a" * 20000)

    # change cwd for the duration of selection
    import os
    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        cfg = Config()
        cfg.set("retrieval.max_tokens", 200)
        engine = ContextEngine(cfg)
        sel = engine.select_context(query="a", budget_tokens=200)
        # should not include large file due to budget
        included = [cf.path for cf in sel.files]
        assert "large.txt" not in included
    finally:
        os.chdir(prev)


def test_command_runner_snapshot_and_timeout(tmp_path):
    # Run a quick command
    cr = CommandRunner(cpu_seconds=1, memory_mb=64, no_network=False)
    res = cr.run_command("python -c 'print(123)'", timeout=5)
    assert res.exit_code == 0
    assert res.stdout.strip() == "123"
    assert res.snapshot.cwd

    # Force a timeout
    res2 = cr.run_command("python -c 'import time; time.sleep(2)'", timeout=1)
    assert res2.exit_code == 124
    assert "TIMEOUT" in res2.stderr
