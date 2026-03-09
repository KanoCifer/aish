"""LLM integration for aish — OpenAI-compatible API client."""

from __future__ import annotations
import json
import platform
from dataclasses import dataclass

from openai import OpenAI


@dataclass
class CommandOutput:
    command: str
    explanation: str
    risk_level: str  # "low", "medium", "high"
    risk_tip: str


SYSTEM_PROMPT = """You are a shell command generator. Your job is to convert natural language requests into executable shell commands.

Rules:
1. Return ONLY valid JSON — no markdown, no code blocks, no extra text
2. Return EXACTLY ONE command
3. The command must be executable on {os_name} ({shell})
4. JSON schema: {{"command": "...", "explanation": "...", "risk_level": "low|medium|high", "risk_tip": "..."}}
5. risk_level: "low" for safe commands, "medium" for potentially impactful, "high" for destructive/irreversible
6. risk_tip: brief warning if risk_level is medium/high, otherwise empty string
7. If the request is ambiguous or dangerous, still return the most reasonable command but set risk_level to "high"

Example response:
{{"command": "ls -la", "explanation": "Lists all files in current directory with details", "risk_level": "low", "risk_tip": ""}}"""


def generate_command(
    prompt: str,
    base_url: str,
    api_key: str,
    model: str,
) -> CommandOutput:
    """
    Call the LLM API to generate a shell command from a natural language prompt.
    Raises ValueError if the response cannot be parsed.
    """
    client = OpenAI(api_key=api_key, base_url=base_url)

    os_name = platform.system()
    shell = "bash"  # default shell assumption

    system_msg = SYSTEM_PROMPT.format(os_name=os_name, shell=shell)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        timeout=60,
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("LLM returned empty response")

    # Strip markdown code blocks if present
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first and last lines (``` markers)
        content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    content = content.strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nContent: {content}") from e

    required_fields = ("command", "explanation", "risk_level", "risk_tip")
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise ValueError(f"LLM response missing fields: {missing}")

    return CommandOutput(
        command=data["command"],
        explanation=data["explanation"],
        risk_level=data.get("risk_level", "low"),
        risk_tip=data.get("risk_tip", ""),
    )
