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

app = typer.Typer(name="aish", help="AI-powered shell assistant")
console = Console()
err_console = Console(stderr=True)


def version_callback(value: bool) -> None:
    if value:
        console.print(f"aish v{__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "-v",
        callback=version_callback,
        help="Show version information and exit",
    ),
) -> None:
    """aish: AI-powered shell command assistant"""
    if ctx.invoked_subcommand is not None:
        return

    text = "[bold cyan]Welcome to aish![/bold cyan]\n\n[dim]Your AI Shell Assistant[/dim]\n\nUse [cyan]aish --help[/cyan] to see available commands."
    console.print(
        Panel(
            text,
            title="aish",
            subtitle="Your AI Shell Assistant",
            border_style="cyan",
            expand=False,
        )
    )


@app.command()
def init(
    base_url: Optional[str] = typer.Option(None, "--base-url", help="LLM API base URL"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="LLM API key"),
    model: Optional[str] = typer.Option(None, "--model", help="Model name"),
    alias: Optional[str] = typer.Option(None, "--alias", help="Optional config alias"),
) -> None:
    """
    初始化配置
    Configure aish with LLM API credentials."""
    resolved_base_url: str = (
        base_url if base_url is not None else typer.prompt("Base URL")
    )
    resolved_api_key: str = (
        api_key if api_key is not None else typer.prompt("API key", hide_input=True)
    )
    resolved_model: str = (
        model if model is not None else typer.prompt("Model", default="gpt-4o")
    )
    alias = (
        alias
        if alias is not None
        else typer.prompt("Alias (optional)", default="").strip() or None
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
            "[bold green]✓[/bold green] Configuration saved to [cyan]~/.aish/config.json[/cyan]"
        )
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        err_console.print(f"[bold red]Error:[/bold red] Failed to save config: {e}")
        raise typer.Exit(1)


@app.command()
def run(
    prompt: Optional[list[str]] = typer.Argument(None, help="Natural language request"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Print command but do not execute"
    ),
    last: bool = typer.Option(
        False, "--last", "-l", help="Execute the last command from history"
    ),
) -> None:
    """
    通过自然语言生成并执行 shell 命令
    Generate and execute a shell command from natural language."""

    pending_command = None
    confirmed = False
    user_prompt: str = ""

    if last:
        history_items = get_history(limit=1)
        if not history_items:
            err_console.print(
                "[bold red]Error:[/bold red] No history found to use as prompt."
            )
            raise typer.Exit(1)
        pending_command = history_items[0]["command"]
        user_prompt = history_items[0].get("prompt", "Re-run last command")
        console.print(
            f"[bold cyan]Using last command from history:[/bold cyan] {pending_command}"
        )

    if pending_command:
        output = CommandOutput(
            command=pending_command,
            explanation="Command retrieved from history.",
            risk_level="low",
            risk_tip="",
        )
        confirmed = True
    else:
        user_prompt = (
            " ".join(prompt)
            if prompt
            else typer.prompt("What do you want to do?你想执行什么命令？")
        )
        try:
            configs: AishConfigs = read_config()
            using_config: AishConfig | None = next(
                (c for c in configs.configs if c.using), None
            )
        except ConfigNotFoundError:
            err_console.print(
                "[bold red]Error:[/bold red] No configuration found. Run [cyan]aish init[/cyan] first."
            )
            raise typer.Exit(1)

        if not using_config:
            err_console.print(
                "[bold red]Error:[/bold red] No active configuration found. Use [cyan]aish model -a[/cyan] to add and activate a config."
            )
            raise typer.Exit(1)

        with console.status("[bold cyan]Generating command…[/bold cyan]"):
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
                err_console.print(f"[bold red]Error:[/bold red] {e}")
                raise typer.Exit(1)

    risk_color = {"low": "green", "medium": "yellow", "high": "red"}.get(
        output.risk_level, "white"
    )
    console.print(
        Panel(
            f"[bold]{output.command}[/bold]",
            title="[bold]Command[/bold]",
            border_style=risk_color,
        )
    )
    console.print(f"[dim]Explanation:[/dim] {output.explanation}")
    console.print(f"[dim]Risk:[/dim] [{risk_color}]{output.risk_level}[/{risk_color}]")

    safety_level, _ = check_command(output.command)
    logger.info(f"Safety check result: {safety_level.value}")

    if safety_level == RiskLevel.DENY:
        logger.warning(f"Command denied by safety check: {output.command}")
        err_console.print(
            "[bold red]✗ Denied:[/bold red] This command matches a dangerous pattern and cannot be executed."
        )
        raise typer.Exit(1)

    if safety_level == RiskLevel.WARN:
        if output.risk_tip:
            console.print(f"[bold yellow]⚠ Warning:[/bold yellow] {output.risk_tip}")
        confirmed = typer.confirm(
            "This command is potentially dangerous. Execute anyway?"
        )
        if not confirmed:
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

    timestamp = datetime.now(timezone.utc).isoformat()

    if dry_run:
        console.print("[bold yellow]Dry run — not executing.[/bold yellow]")
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
        confirmed = typer.confirm("Execute this command?")
        if not confirmed:
            console.print("[yellow]Aborted.[/yellow]")
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
    console.print(f"{exit_label} Exit code: [bold]{result.exit_code}[/bold]")

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
        10, "--limit", "-l", help="Number of history items to display"
    ),
    clear: bool = typer.Option(False, "--clear", "-c", help="Clear command history"),
) -> None:
    """
    显示命令历史
    Show command history."""

    if clear:
        try:
            clear_history()
            logger.info("Command history cleared")
            console.print("[bold green]✓[/bold green] Command history cleared.")
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
            err_console.print(
                f"[bold red]Error:[/bold red] Failed to clear history: {e}"
            )
            raise typer.Exit(1)

    history_items = get_history(limit=limit)
    for item in history_items:
        console.print(f"[dim]{item['timestamp']}[/dim] {item['command']}")


@app.command()
def model(
    add_config: bool = typer.Option(
        False, "-a", "--add", help="Add or update model configuration"
    ),
    switch: Optional[str] = typer.Option(
        None,
        "-s",
        "--switch",
        help="Switch active model configuration by alias or model name",
    ),
    list: bool = typer.Option(
        False,
        "-l",
        "--list",
        help="List all model configurations with active one highlighted",
    ),
):
    """
    显示当前使用的模型
    Show current LLM model."""
    try:
        configs: AishConfigs = read_config()
    except ConfigNotFoundError:
        err_console.print(
            "[bold red]Error:[/bold red] No configuration found. Run [cyan]aish init[/cyan] first."
        )
        raise typer.Exit(1)

    if list:
        console.print("\n[bold]Available Configurations:[/bold]")
        for config in configs.configs:
            active_marker = "[green]✓[/green]" if config.using else " "
            alias_part = f" (alias: {config.alias})" if config.alias else ""
            console.print(f"{active_marker} [cyan]{config.model}[/cyan]{alias_part}\n")

    if switch:
        # 显示所有配置列表，找到匹配 switch 参数的配置，并切换到该配置
        target = switch
        target_config = next(
            (c for c in configs.configs if c.alias == target or c.model == target), None
        )
        if not target_config:
            err_console.print(
                f"[bold red]Error:[/bold red] No configuration found with alias or model name '{target}'."
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
                f"[bold green]✓[/bold green] Switched active configuration to [cyan]{target_config.model}[/cyan]."
            )
        except Exception as e:
            logger.error(f"Failed to switch config: {e}")
            err_console.print(
                f"[bold red]Error:[/bold red] Failed to switch config: {e}"
            )
            raise typer.Exit(1)

    if add_config:
        console.print("[bold cyan]Add or update model configuration[/bold cyan]")
        base_url = typer.prompt("Base URL")
        api_key = typer.prompt("API key", hide_input=True)
        model = typer.prompt("Model")
        alias = typer.prompt("Alias (optional)", default="").strip() or None

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
                "[bold green]✓[/bold green] Configuration updated successfully."
            )
        except Exception as e:
            err_console.print(
                f"[bold red]Error:[/bold red] Failed to update config: {e}"
            )
            raise typer.Exit(1)

    using_config: AishConfig | None = next(
        (c for c in configs.configs if c.using), None
    )
    if using_config:
        console.print(f"Current active model: [cyan]{using_config.model}[/cyan]")


if __name__ == "__main__":
    app()
