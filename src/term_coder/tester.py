from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import json
import re

from .config import Config
from .runner import CommandRunner


LAST_TEST_FILE = Path(".term-coder/last_test.json")


@dataclass
class TestCaseFailure:
    test_id: str  # e.g., tests/test_file.py::TestClass::test_method
    message: str


@dataclass
class TestReport:
    framework: str
    command: str
    passed: int
    failed: int
    skipped: int
    failures: List[TestCaseFailure]
    stdout: str
    stderr: str


def detect_framework(root: Path) -> str:
    # Simple heuristics
    if (root / "pyproject.toml").exists() or (root / "pytest.ini").exists() or list(root.glob("tests/test_*.py")):
        return "pytest"
    if (root / "package.json").exists() or (root / "jest.config.js").exists():
        return "jest"
    if (root / "go.mod").exists():
        return "gotest"
    return "pytest"


def default_command_for(framework: str, cfg: Optional[Config] = None) -> str:
    cfg = cfg or Config()
    # Allow configuration override in future; for now, pick sensible defaults
    if framework == "pytest":
        return "pytest -q"
    if framework == "jest":
        return "npm test --silent"
    if framework == "gotest":
        return "go test ./..."
    return "pytest -q"


def parse_pytest_output(out: str) -> Tuple[int, int, int, List[TestCaseFailure]]:
    # Combine counts from summary like "2 failed, 10 passed, 1 skipped"
    failed = passed = skipped = 0
    summary = re.findall(r"(\d+)\s+(failed|passed|skipped)", out)
    for count, kind in summary:
        n = int(count)
        if kind == "failed":
            failed = n
        elif kind == "passed":
            passed = n
        elif kind == "skipped":
            skipped = n
    failures: List[TestCaseFailure] = []
    for line in out.splitlines():
        m = re.match(r"^FAILED\s+(.+?)\s+-\s+(.*)$", line.strip())
        if m:
            failures.append(TestCaseFailure(test_id=m.group(1), message=m.group(2)))
    return passed, failed, skipped, failures


def parse_jest_output(out: str) -> Tuple[int, int, int, List[TestCaseFailure]]:
    # Minimal stub; Jest summaries vary widely
    failed = passed = skipped = 0
    failures: List[TestCaseFailure] = []
    for line in out.splitlines():
        if line.strip().startswith("FAIL "):
            failures.append(TestCaseFailure(test_id=line.strip()[5:], message="Failed suite"))
    return passed, failed, skipped, failures


def parse_go_test_output(out: str) -> Tuple[int, int, int, List[TestCaseFailure]]:
    failed = passed = skipped = 0
    failures: List[TestCaseFailure] = []
    for line in out.splitlines():
        if line.startswith("--- FAIL:"):
            parts = line.split()
            if len(parts) >= 3:
                failures.append(TestCaseFailure(test_id=parts[2], message=""))
            failed += 1
        if line.startswith("PASS"):
            passed += 1
        if line.startswith("SKIP"):
            skipped += 1
    return passed, failed, skipped, failures


def parse_output(framework: str, stdout: str, stderr: str) -> Tuple[int, int, int, List[TestCaseFailure]]:
    out = stdout + "\n" + stderr
    if framework == "pytest":
        return parse_pytest_output(out)
    if framework == "jest":
        return parse_jest_output(out)
    if framework == "gotest":
        return parse_go_test_output(out)
    return 0, 0, 0, []


def run_tests(command: Optional[str] = None, framework: Optional[str] = None, cfg: Optional[Config] = None) -> TestReport:
    cfg = cfg or Config()
    root = Path.cwd().resolve()
    framework = framework or detect_framework(root)
    command = command or default_command_for(framework, cfg)

    runner = CommandRunner()
    result = runner.run_command(command, timeout=600)
    passed, failed, skipped, failures = parse_output(framework, result.stdout, result.stderr)
    report = TestReport(
        framework=framework,
        command=command,
        passed=passed,
        failed=failed,
        skipped=skipped,
        failures=failures,
        stdout=result.stdout,
        stderr=result.stderr,
    )

    try:
        LAST_TEST_FILE.parent.mkdir(parents=True, exist_ok=True)
        LAST_TEST_FILE.write_text(
            json.dumps(
                {
                    "framework": framework,
                    "command": command,
                    "passed": passed,
                    "failed": failed,
                    "skipped": skipped,
                    "failures": [{"test_id": f.test_id, "message": f.message} for f in failures],
                }
            )
        )
    except Exception:
        pass

    return report
