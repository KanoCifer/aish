"""LLM integration for aish — Agno-based agent for shell command generation."""

from __future__ import annotations

import platform
from dataclasses import dataclass

from agno.agent import Agent, RunOutput
from agno.models.openai.like import OpenAILike
from pydantic import BaseModel, Field

from aish.logger import logger


class CommandSchema(BaseModel):
    """Structured output schema for shell command generation."""

    command: str = Field(..., description="The executable shell command")
    explanation: str = Field(
        ..., description="Brief explanation of what the command does"
    )
    risk_level: str = Field(
        ...,
        description="Risk level: low, medium, or high",
    )
    risk_tip: str = Field(
        default="",
        description="Warning message if risk_level is medium/high, otherwise empty string",
    )


@dataclass
class CommandOutput:
    command: str
    explanation: str
    risk_level: str  # "low", "medium", "high"
    risk_tip: str


SYSTEM_PROMPT = """你是一个 Shell 命令生成器。你的任务是将用户的自然语言请求转换为可执行的 Shell 命令。

规则：
1. 只返回合法的 JSON — 不要返回 Markdown、代码块或任何额外文本
2. 只返回一个命令
3. 命令必须可在当前操作系统和 Shell 上执行
4. explanation 字段：如果用户使用中文，返回中文解释；如果用户使用英文，返回英文解释
5. risk_level：安全命令用 "low"，有潜在影响用 "medium"，破坏性/不可逆操作用 "high"
6. risk_tip：当 risk_level 为 medium/high 时给出简短警告，否则为空字符串
7. 如果请求有歧义或危险，仍返回最合理的命令，但将 risk_level 设为 "high"

当前系统：{os_name}，Shell：{shell}

中文示例：
{{"command": "brew update", "explanation": "更新 Homebrew 的包列表", "risk_level": "low", "risk_tip": ""}}
{{"command": "rm -rf /tmp/cache", "explanation": "删除 /tmp/cache 目录及其所有内容", "risk_level": "high", "risk_tip": "此操作不可恢复，请确认路径正确"}}

英文示例：
{{"command": "ls -la", "explanation": "Lists all files in current directory with details", "risk_level": "low", "risk_tip": ""}}"""


def generate_command(
    prompt: str,
    base_url: str,
    api_key: str,
    model: str,
) -> CommandOutput:
    """
    Generate a shell command from natural language using Agno agent.

    :param prompt: User's natural language request
    :param base_url: LLM API base URL
    :param api_key: LLM API key
    :param model: LLM model name to use
    :return: CommandOutput with command, explanation, risk_level, and risk_tip
    """
    os_name: str = platform.system()
    shell: str = "bash" if os_name != "Windows" else "PowerShell"

    system_msg = SYSTEM_PROMPT.format(os_name=os_name, shell=shell)

    logger.debug(f"Calling LLM via Agno: model={model}, base_url={base_url}")

    agent = Agent(
        model=OpenAILike(
            id=model,
            api_key=api_key,
            base_url=base_url,
        ),
        description=system_msg,
        output_schema=CommandSchema,
        use_json_mode=True,
    )

    response: RunOutput = agent.run(prompt)

    logger.debug("LLM response received")

    if not response.content:
        raise ValueError("LLM returned empty response")

    # Parse structured output
    content = response.content
    if isinstance(content, CommandSchema):
        return CommandOutput(
            command=content.command,
            explanation=content.explanation,
            risk_level=content.risk_level,
            risk_tip=content.risk_tip,
        )

    # Fallback: try to parse as dict
    if isinstance(content, dict):
        return CommandOutput(
            command=content["command"],
            explanation=content["explanation"],
            risk_level=content.get("risk_level", "low"),
            risk_tip=content.get("risk_tip", ""),
        )

    # Fallback: parse string as JSON
    if isinstance(content, str):
        import json

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Strip markdown code fences if present
            cleaned = content.strip()
            if cleaned.startswith("```"):
                cleaned = "\n".join(cleaned.split("\n")[1:-1])
            data = json.loads(cleaned)
        return CommandOutput(
            command=data["command"],
            explanation=data["explanation"],
            risk_level=data.get("risk_level", "low"),
            risk_tip=data.get("risk_tip", ""),
        )

    raise ValueError(f"Unexpected response type: {type(content)}")
