"""Command execution wrapper for aish."""

from __future__ import annotations
import subprocess
from dataclasses import dataclass


@dataclass
class ExecResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.exit_code == 0


def run_command(command: str, timeout: int = 30) -> ExecResult:
    """
    Execute a shell command using shell=True (supports pipes, redirects).
    Returns ExecResult with exit code, stdout, stderr.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return ExecResult(
            command=command,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    except subprocess.TimeoutExpired:
        return ExecResult(
            command=command,
            exit_code=124,  # Standard timeout exit code
            stdout="",
            stderr=f"Command timed out after {timeout} seconds",
        )
    except Exception as e:
        return ExecResult(
            command=command,
            exit_code=1,
            stdout="",
            stderr=str(e),
        )
