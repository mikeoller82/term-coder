from __future__ import annotations

import shlex
import subprocess
import time
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float


class CommandRunner:
    def run_command(self, command: str, timeout: int = 30, env: Optional[Dict[str, str]] = None) -> CommandResult:
        start = time.time()
        try:
            proc = subprocess.run(
                command,
                shell=True,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True,
            )
            return CommandResult(
                command=command,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                execution_time=time.time() - start,
            )
        except subprocess.TimeoutExpired as e:
            return CommandResult(
                command=command,
                exit_code=124,
                stdout=e.stdout or "",
                stderr=(e.stderr or "") + "\n[TIMEOUT]",
                execution_time=time.time() - start,
            )

