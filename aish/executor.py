"""Command execution wrapper for aish."""

from __future__ import annotations

import subprocess

from pydantic import BaseModel, Field

from aish.logger import logger


class ExecResult(BaseModel):
    command: str = Field(..., description="The command that was executed")
    exit_code: int = Field(..., description="Exit code of the command")
    stdout: str = Field(..., description="Standard output from the command")
    stderr: str = Field(..., description="Standard error from the command")

    @property
    def success(self) -> bool:
        return self.exit_code == 0


def run_command(command: str, timeout: int = 30) -> ExecResult:
    """
    运行shell命令并返回结果
    :param command: 要执行的命令
    :param timeout: 命令执行的超时时间（秒）
    :return: ExecResult对象，包含命令、退出码、标准输出和标准错误
    """
    logger.info(f"Executing command: {command[:100]}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        logger.debug(f"Command completed: exit_code={result.returncode}")
        return ExecResult(
            command=command,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    except subprocess.TimeoutExpired:
        logger.warning(f"Command timed out after {timeout}s: {command[:100]}...")
        return ExecResult(
            command=command,
            exit_code=124,  # Standard timeout exit code
            stdout="",
            stderr=f"Command timed out after {timeout} seconds",
        )
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        return ExecResult(
            command=command,
            exit_code=1,
            stdout="",
            stderr=str(e),
        )
