from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from aish.config import AishConfig, ConfigNotFoundError, read_config, write_config
from aish.executor import run_command
from aish.history import append_history
from aish.llm import generate_command
from aish.safety import RiskLevel, check_command

app = typer.Typer(name="aish", help="AI-powered shell assistant")
console = Console()
err_console = Console(stderr=True)


@app.command()
def init(
    base_url: Optional[str] = typer.Option(None, "--base-url", help="LLM API base URL"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="LLM API key"),
    model: Optional[str] = typer.Option(None, "--model", help="Model name"),
) -> None:
    """Configure aish with LLM API credentials."""
    resolved_base_url: str = (
        base_url if base_url is not None else typer.prompt("Base URL")
    )
    resolved_api_key: str = (
        api_key if api_key is not None else typer.prompt("API key", hide_input=True)
    )
    resolved_model: str = (
        model if model is not None else typer.prompt("Model", default="gpt-4o")
    )

    try:
        write_config(
            AishConfig(
                base_url=resolved_base_url,
                api_key=resolved_api_key,
                model=resolved_model,
            )
        )
        console.print(
            "[bold green]✓[/bold green] Configuration saved to [cyan]~/.aish/config[/cyan]"
        )
    except Exception as e:
        err_console.print(f"[bold red]Error:[/bold red] Failed to save config: {e}")
        raise typer.Exit(1)


@app.command()
def run(
    prompt: list[str] = typer.Argument(..., help="Natural language request"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Print command but do not execute"
    ),
) -> None:
    """Generate and execute a shell command from natural language."""
    user_prompt = " ".join(prompt)

    try:
        config = read_config()
    except ConfigNotFoundError:
        err_console.print(
            "[bold red]Error:[/bold red] No configuration found. Run [cyan]aish init[/cyan] first."
        )
        raise typer.Exit(1)

    with console.status("[bold cyan]Generating command…[/bold cyan]"):
        try:
            output = generate_command(
                user_prompt, config.base_url, config.api_key, config.model
            )
        except ValueError as e:
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

    if safety_level == RiskLevel.DENY:
        err_console.print(
            "[bold red]✗ Denied:[/bold red] This command matches a dangerous pattern and cannot be executed."
        )
        raise typer.Exit(1)

    confirmed = False

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


if __name__ == "__main__":
    app()
