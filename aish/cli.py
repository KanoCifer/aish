from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import typer
from pydantic import SecretStr
from rich.console import Console
from rich.panel import Panel

from aish import __version__
from aish.config import (
    AishConfig,
    AishConfigs,
    ConfigNotFoundError,
    read_config,
    update_config,
    write_config,
)
from aish.executor import run_command
from aish.history import append_history, clear_history, get_history
from aish.llm import CommandOutput, generate_command
from aish.logger import logger
from aish.safety import RiskLevel, check_command

app = typer.Typer(
    name="aish", help="AI 驱动的 Shell 命令助手 / AI-powered shell assistant"
)
console = Console()
err_console = Console(stderr=True)


def version_callback(value: bool) -> None:
    if value:
        console.print(f"aish v{__version__}")
        raise typer.Exit()


def history_callback(value: bool) -> None:
    if value:
        history_items = get_history(limit=10)
        if not history_items:
            console.print("[dim]暂无历史记录 / No history found.[/dim]")
            raise typer.Exit(0)
        console.print("\n[bold]最近的命令历史 / Recent Command History:[/bold]")
        for item in history_items:
            timestamp = item.get("timestamp", "未知时间 / unknown time")
            command = item.get("command", "未知命令 / unknown command")
            console.print(f"[dim]{timestamp}[/dim] {command}")
        raise typer.Exit(0)


def models_callback(value: bool) -> None:
    if value:
        try:
            configs: AishConfigs = read_config()
            if not configs.configs:
                console.print(
                    "[dim]未找到模型配置 / No model configurations found.[/dim]"
                )
                raise typer.Exit(0)
            console.print("\n[bold]模型配置列表 / Model Configurations:[/bold]")
            for config in configs.configs:
                active_marker = "[green]✓[/green]" if config.using else " "
                alias_part = f"（别名：{config.alias}）" if config.alias else ""
                console.print(
                    f"{active_marker} [cyan]{config.model}[/cyan]{alias_part}\n"
                )
        except ConfigNotFoundError:
            console.print(
                "[dim]未找到配置。请先运行 [cyan]aish init[/cyan] / No configuration found. Run [cyan]aish init[/cyan] first.[/dim]"
            )
        raise typer.Exit(0)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "-v",
        callback=version_callback,
        help="显示版本信息并退出 / Show version and exit",
    ),
    history: bool = typer.Option(
        False,
        "--history",
        "-H",
        callback=history_callback,
        help="显示命令历史并退出 / Show command history and exit",
    ),
    models: bool = typer.Option(
        False,
        "--models",
        "-M",
        callback=models_callback,
        help="列出模型配置并退出 / List model configurations and exit",
    ),
) -> None:
    """aish：AI 驱动的 Shell 命令助手 / AI-powered shell command assistant"""
    if ctx.invoked_subcommand is not None:
        return

    text = (
        "[bold cyan]欢迎使用 aish！[/bold cyan]\n\n"
        "[dim]你的 AI Shell 助手 / Your AI Shell Assistant[/dim]\n\n"
        "使用 [cyan]aish --help[/cyan] 查看可用命令。"
    )
    console.print(
        Panel(
            text,
            title="aish",
            subtitle="AI Shell 助手 / Your AI Shell Assistant",
            border_style="cyan",
            expand=False,
        )
    )


@app.command()
def init(
    base_url: Optional[str] = typer.Option(
        None, "--base-url", help="LLM API 地址 / API base URL"
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", help="LLM API 密钥 / API key"
    ),
    model: Optional[str] = typer.Option(None, "--model", help="模型名称 / Model name"),
    alias: Optional[str] = typer.Option(
        None, "--alias", help="配置别名 / Config alias"
    ),
) -> None:
    """初始化 aish 配置 / Configure aish with LLM API credentials"""
    resolved_base_url: str = (
        base_url if base_url is not None else typer.prompt("API 地址 / Base URL")
    )
    resolved_api_key: str = (
        api_key
        if api_key is not None
        else typer.prompt("API 密钥 / API key", hide_input=True)
    )
    resolved_model: str = (
        model
        if model is not None
        else typer.prompt("模型名称 / Model", default="gpt-4o")
    )
    alias = (
        alias
        if alias is not None
        else typer.prompt("别名（可选）/ Alias (optional)", default="").strip() or None
    )

    try:
        write_config(
            AishConfig(
                base_url=resolved_base_url,
                api_key=SecretStr(resolved_api_key),
                model=resolved_model,
                alias=alias,
                using=True,
            )
        )
        logger.info(f"Configuration saved: model={resolved_model}, alias={alias}")
        console.print(
            "[bold green]✓[/bold green] 配置已保存 / Configuration saved to [cyan]~/.aish/config.json[/cyan]"
        )
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        err_console.print(
            f"[bold red]错误 / Error:[/bold red] 保存配置失败 / Failed to save config: {e}"
        )
        raise typer.Exit(1)


@app.command()
def run(
    prompt: Optional[list[str]] = typer.Argument(
        None, help="自然语言描述 / Natural language request"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="跳过确认 / Skip confirmation"),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="仅显示不执行 / Print command only"
    ),
    last: bool = typer.Option(
        False, "--last", "-l", help="执行上次命令 / Execute last command"
    ),
) -> None:
    """通过自然语言生成并执行 Shell 命令 / Generate and execute shell command from natural language"""

    pending_command = None
    confirmed = False
    user_prompt: str = ""

    if last:
        history_items = get_history(limit=1)
        if not history_items:
            err_console.print(
                "[bold red]错误 / Error:[/bold red] 未找到历史记录 / No history found."
            )
            raise typer.Exit(1)
        pending_command = history_items[0]["command"]
        user_prompt = history_items[0].get("prompt", "重新执行 / Re-run last command")
        console.print(
            f"[bold cyan]使用历史命令 / Using last command:[/bold cyan] {pending_command}"
        )

    if pending_command:
        output = CommandOutput(
            command=pending_command,
            explanation="从历史记录中获取 / Command retrieved from history.",
            risk_level="low",
            risk_tip="",
        )
        confirmed = True
    else:
        user_prompt = (
            " ".join(prompt)
            if prompt
            else typer.prompt("你想执行什么操作？/ What do you want to do?")
        )
        try:
            configs: AishConfigs = read_config()
            using_config: AishConfig | None = next(
                (c for c in configs.configs if c.using), None
            )
        except ConfigNotFoundError:
            err_console.print(
                "[bold red]错误 / Error:[/bold red] 未找到配置，请先运行 [cyan]aish init[/cyan] / No configuration found. Run [cyan]aish init[/cyan] first."
            )
            raise typer.Exit(1)

        if not using_config:
            err_console.print(
                "[bold red]错误 / Error:[/bold red] 未找到活跃配置 / No active config. 使用 [cyan]aish model -a[/cyan] 添加 / Use [cyan]aish model -a[/cyan] to add."
            )
            raise typer.Exit(1)

        with console.status(
            "[bold cyan]正在生成命令… / Generating command…[/bold cyan]"
        ):
            try:
                logger.info(f"Generating command for prompt: {user_prompt[:50]}...")
                output: CommandOutput = generate_command(
                    prompt=user_prompt,
                    base_url=using_config.base_url,
                    api_key=using_config.api_key.get_secret_value(),
                    model=using_config.model,
                )
                logger.info(
                    f"Generated command: {output.command}, risk: {output.risk_level}"
                )
            except ValueError as e:
                logger.error(f"Failed to generate command: {e}")
                err_console.print(f"[bold red]错误 / Error:[/bold red] {e}")
                raise typer.Exit(1)

    risk_color = {"low": "green", "medium": "yellow", "high": "red"}.get(
        output.risk_level, "white"
    )
    console.print(
        Panel(
            f"[bold]{output.command}[/bold]",
            title="[bold]命令 / Command[/bold]",
            border_style=risk_color,
        )
    )
    console.print(f"[dim]说明 / Explanation:[/dim] {output.explanation}")
    console.print(
        f"[dim]风险 / Risk:[/dim] [{risk_color}]{output.risk_level}[/{risk_color}]"
    )

    safety_level, _ = check_command(output.command)
    logger.info(f"Safety check result: {safety_level.value}")

    if safety_level == RiskLevel.DENY:
        logger.warning(f"Command denied by safety check: {output.command}")
        err_console.print(
            "[bold red]✗ 已拒绝 / Denied:[/bold red] 此命令匹配危险模式，无法执行 / This command matches a dangerous pattern."
        )
        raise typer.Exit(1)

    if safety_level == RiskLevel.WARN:
        if output.risk_tip:
            console.print(
                f"[bold yellow]⚠ 警告 / Warning:[/bold yellow] {output.risk_tip}"
            )
        confirmed = typer.confirm(
            "此命令可能有风险，确定要执行吗？/ This command is potentially dangerous. Execute anyway?"
        )
        if not confirmed:
            console.print("[yellow]已取消 / Aborted.[/yellow]")
            raise typer.Exit(0)

    timestamp = datetime.now(timezone.utc).isoformat()

    if dry_run:
        console.print(
            "[bold yellow]预览模式，未执行 / Dry run — not executing.[/bold yellow]"
        )
        append_history(
            {
                "timestamp": timestamp,
                "prompt": user_prompt,
                "command": output.command,
                "exit_code": None,
                "executed": False,
            }
        )
        raise typer.Exit(0)

    if not yes and not confirmed:
        confirmed = typer.confirm("执行此命令？/ Execute this command?")
        if not confirmed:
            console.print("[yellow]已取消 / Aborted.[/yellow]")
            raise typer.Exit(0)

    result = run_command(output.command)
    logger.info(f"Command executed: exit_code={result.exit_code}")

    if result.stdout:
        console.print(Panel(result.stdout.rstrip(), title="stdout", border_style="dim"))
    if result.stderr:
        console.print(
            Panel(result.stderr.rstrip(), title="stderr", border_style="red dim")
        )

    exit_label = "[green]✓[/green]" if result.success else "[red]✗[/red]"
    console.print(f"{exit_label} 退出码 / Exit code: [bold]{result.exit_code}[/bold]")

    append_history(
        {
            "timestamp": timestamp,
            "prompt": user_prompt,
            "command": output.command,
            "exit_code": result.exit_code,
            "executed": True,
        }
    )


@app.command()
def history(
    limit: int = typer.Option(
        10,
        "--limit",
        "-l",
        help="显示的历史记录数量 / Number of history items to display",
    ),
    clear: bool = typer.Option(
        False, "--clear", "-c", help="清除命令历史 / Clear command history"
    ),
) -> None:
    """显示命令历史 / Show command history"""

    if clear:
        try:
            clear_history()
            logger.info("Command history cleared")
            console.print(
                "[bold green]✓[/bold green] 命令历史已清除 / Command history cleared."
            )
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
            err_console.print(
                f"[bold red]错误 / Error:[/bold red] 清除历史失败 / Failed to clear history: {e}"
            )
            raise typer.Exit(1)

    history_items = get_history(limit=limit)
    for item in history_items:
        console.print(f"[dim]{item['timestamp']}[/dim] {item['command']}")


@app.command()
def model(
    add_config: bool = typer.Option(
        False,
        "-a",
        "--add",
        help="添加或更新模型配置 / Add or update model configuration",
    ),
    switch: Optional[str] = typer.Option(
        None,
        "-s",
        "--switch",
        help="切换活跃模型配置 / Switch active model configuration",
    ),
    list: bool = typer.Option(
        False,
        "-l",
        "--list",
        help="列出所有模型配置 / List all model configurations",
    ),
):
    """管理模型配置 / Manage model configurations"""
    try:
        configs: AishConfigs = read_config()
    except ConfigNotFoundError:
        err_console.print(
            "[bold red]错误 / Error:[/bold red] 未找到配置，请先运行 [cyan]aish init[/cyan] / No configuration found. Run [cyan]aish init[/cyan] first."
        )
        raise typer.Exit(1)

    if list:
        console.print("\n[bold]可用配置 / Available Configurations:[/bold]")
        for config in configs.configs:
            active_marker = "[green]✓[/green]" if config.using else " "
            alias_part = f"（别名：{config.alias}）" if config.alias else ""
            console.print(f"{active_marker} [cyan]{config.model}[/cyan]{alias_part}\n")

    if switch:
        # 查找匹配的配置并切换
        target = switch
        target_config = next(
            (c for c in configs.configs if c.alias == target or c.model == target), None
        )
        if not target_config:
            err_console.print(
                f"[bold red]错误 / Error:[/bold red] 未找到别名或模型名为 '{target}' 的配置 / No config found with alias or model name '{target}'."
            )
            raise typer.Exit(1)

        try:
            update_config(
                AishConfig(
                    base_url=target_config.base_url,
                    api_key=target_config.api_key,
                    model=target_config.model,
                    alias=target_config.alias,
                    using=True,
                )
            )
            logger.info(f"Switched to model: {target_config.model}")
            console.print(
                f"[bold green]✓[/bold green] 已切换到配置 / Switched to [cyan]{target_config.model}[/cyan]."
            )
        except Exception as e:
            logger.error(f"Failed to switch config: {e}")
            err_console.print(
                f"[bold red]错误 / Error:[/bold red] 切换配置失败 / Failed to switch config: {e}"
            )
            raise typer.Exit(1)

    if add_config:
        console.print(
            "[bold cyan]添加或更新模型配置 / Add or update model configuration[/bold cyan]"
        )
        base_url = typer.prompt("API 地址 / Base URL")
        api_key = typer.prompt("API 密钥 / API key", hide_input=True)
        model = typer.prompt("模型名称 / Model")
        alias = (
            typer.prompt("别名（可选）/ Alias (optional)", default="").strip() or None
        )

        try:
            write_config(
                AishConfig(
                    base_url=base_url,
                    api_key=api_key,
                    model=model,
                    alias=alias,
                    using=True,
                )
            )
            console.print(
                "[bold green]✓[/bold green] 配置已更新 / Configuration updated successfully."
            )
        except Exception as e:
            err_console.print(
                f"[bold red]错误 / Error:[/bold red] 更新配置失败 / Failed to update config: {e}"
            )
            raise typer.Exit(1)

    using_config: AishConfig | None = next(
        (c for c in configs.configs if c.using), None
    )
    if using_config:
        console.print(
            f"当前活跃模型 / Current active model: [cyan]{using_config.model}[/cyan]"
        )


if __name__ == "__main__":
    app()
