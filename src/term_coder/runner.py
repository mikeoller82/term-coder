from __future__ import annotations

import shlex
import subprocess
import time
from dataclasses import dataclass
from typing import Dict, Optional
import os
import json
import shutil
import resource
from pathlib import Path


@dataclass
class EnvironmentSnapshot:
    cwd: str
    env: Dict[str, str]
    timestamp: float


@dataclass
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    snapshot: EnvironmentSnapshot


LAST_RUN_FILE = ".term-coder/last_run.json"


class CommandRunner:
    def __init__(self, cpu_seconds: int | None = None, memory_mb: int | None = None, no_network: bool | None = None, audit_logger=None):
        from .config import Config

        cfg = Config()
        sb = cfg.get("sandbox", {}) or {}
        self.cpu_seconds = int(cpu_seconds if cpu_seconds is not None else sb.get("cpu_seconds", 5))
        self.memory_mb = int(memory_mb if memory_mb is not None else sb.get("memory_mb", 512))
        self.no_network = bool(no_network if no_network is not None else sb.get("no_network", False))
        self.audit_logger = audit_logger

    def _snapshot(self) -> EnvironmentSnapshot:
        return EnvironmentSnapshot(cwd=os.getcwd(), env=dict(os.environ), timestamp=time.time())

    def _preexec(self):
        # Apply resource limits in child process
        try:
            if self.cpu_seconds:
                resource.setrlimit(resource.RLIMIT_CPU, (self.cpu_seconds, self.cpu_seconds))
        except Exception:
            pass
        try:
            if self.memory_mb:
                bytes_limit = self.memory_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (bytes_limit, bytes_limit))
        except Exception:
            pass

    def _wrap_command(self, command: str) -> str:
        # Optionally isolate networking using unshare if available
        if self.no_network and shutil.which("unshare"):
            return f"unshare -n -- bash -lc {shlex.quote(command)}"
        return command

    def run_command(self, command: str, timeout: int = 30, env: Optional[Dict[str, str]] = None) -> CommandResult:
        start = time.time()
        snapshot = self._snapshot()
        wrapped = self._wrap_command(command)
        try:
            proc = subprocess.run(
                wrapped,
                shell=True,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True,
                preexec_fn=self._preexec,
            )
            result = CommandResult(
                command=command,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                execution_time=time.time() - start,
                snapshot=snapshot,
            )
        except subprocess.TimeoutExpired as e:
            result = CommandResult(
                command=command,
                exit_code=124,
                stdout=e.stdout or "",
                stderr=(e.stderr or "") + "\n[TIMEOUT]",
                execution_time=time.time() - start,
                snapshot=snapshot,
            )

        # Log command execution
        if self.audit_logger:
            self.audit_logger.log_command_execution(
                command=command,
                success=(result.exit_code == 0),
                details={
                    "exit_code": result.exit_code,
                    "execution_time": result.execution_time,
                    "timeout": timeout,
                    "cpu_limit": self.cpu_seconds,
                    "memory_limit": self.memory_mb,
                    "network_isolated": self.no_network,
                    "stdout_length": len(result.stdout),
                    "stderr_length": len(result.stderr)
                }
            )

        # Persist last run
        try:
            Path(LAST_RUN_FILE).parent.mkdir(parents=True, exist_ok=True)
            Path(LAST_RUN_FILE).write_text(
                json.dumps(
                    {
                        "command": result.command,
                        "exit_code": result.exit_code,
                        "stdout": result.stdout[-100000:],
                        "stderr": result.stderr[-100000:],
                        "execution_time": result.execution_time,
                        "snapshot": {
                            "cwd": result.snapshot.cwd,
                            "timestamp": result.snapshot.timestamp,
                            "env_sample": {k: result.snapshot.env.get(k, "") for k in list(result.snapshot.env)[:20]},
                        },
                    }
                )
            )
        except Exception:
            pass

        return result

