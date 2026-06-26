"""CLI entry point for skill-lint."""

from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

# Eagerly import all rule modules so RULE_REGISTRY is populated for every subcommand
import skill_lint.rules.roo.registry  # noqa: F401

app = typer.Typer(
    name="skill-lint",
    help="Static quality linter for AI agent skill definitions (SKILL.md files).",
    no_args_is_help=True,
)

roo_app = typer.Typer(
    name="roo",
    help="Lint Roo skill definitions.",
    no_args_is_help=True,
)
app.add_typer(roo_app, name="roo")

console = Console()
err_console = Console(stderr=True)


class OutputFormat(str, Enum):
    text = "text"
    json = "json"
    github = "github"


class SeverityFilter(str, Enum):
    error = "error"
    warning = "warning"


@roo_app.command("check")
def roo_check(
    path: str = typer.Argument(".", help="Path to scan (file or directory)."),
    severity: Optional[SeverityFilter] = typer.Option(
        None, "--severity", help="Filter violations by minimum severity."
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.text, "--format", help="Output format."
    ),
    ignore: Optional[str] = typer.Option(
        None, "--ignore", help="Comma-separated rule IDs to ignore."
    ),
    config: Optional[Path] = typer.Option(
        None, "--config", help="Path to .skill-lint.yaml config file."
    ),
) -> None:
    """Lint Roo skill.md files found under PATH."""
    from skill_lint.config import load_config
    from skill_lint.runner import run_scan
    from skill_lint.reporters.console import ConsoleReporter
    from skill_lint.reporters.json_reporter import JsonReporter
    from skill_lint.models import Severity

    # Load config
    cfg = load_config(config)

    # Build ignore set
    ignored_rules: set[str] = set()
    if ignore:
        ignored_rules.update(r.strip() for r in ignore.split(","))
    ignored_rules.update(cfg.get("ignore_rules", []))

    # Severity filter
    min_severity: Severity | None = None
    if severity == SeverityFilter.error:
        min_severity = Severity.ERROR

    scan_path = Path(path)
    if not scan_path.exists():
        err_console.print(f"[red]Error:[/red] Path not found: {path}")
        raise typer.Exit(2)

    result = run_scan(scan_path, cfg=cfg, ignored_rules=ignored_rules)

    # Apply severity filter
    if min_severity == Severity.ERROR:
        result.violations = [
            v for v in result.violations if v.severity == Severity.ERROR
        ]

    if format == OutputFormat.json:
        reporter = JsonReporter()
        reporter.report(result)
    elif format == OutputFormat.github:
        _report_github(result)
    else:
        reporter = ConsoleReporter(console=console)
        reporter.report(result)

    if result.errors > 0 or result.warnings > 0:
        raise typer.Exit(1)
    raise typer.Exit(0)


@roo_app.command("rules")
def roo_rules() -> None:
    """List all available Roo lint rules."""
    from skill_lint.rules.base import RULE_REGISTRY
    from rich.table import Table

    table = Table(title="Roo Skill Lint Rules", show_lines=True)
    table.add_column("Rule ID", style="bold cyan", no_wrap=True)
    table.add_column("Severity", no_wrap=True)
    table.add_column("Description")

    for rule_id in sorted(RULE_REGISTRY.keys()):
        rule = RULE_REGISTRY[rule_id]
        sev_style = "red" if rule.severity.value == "error" else "yellow"
        table.add_row(
            rule_id,
            f"[{sev_style}]{rule.severity.value}[/{sev_style}]",
            rule.description,
        )

    console.print(table)


@roo_app.command("explain")
def roo_explain(
    rule_id: str = typer.Argument(..., help="Rule ID to explain (e.g. ROO013).")
) -> None:
    """Show detailed documentation for a specific rule."""
    from skill_lint.rules.base import RULE_REGISTRY

    rule_id = rule_id.upper()
    if rule_id not in RULE_REGISTRY:
        err_console.print(f"[red]Unknown rule:[/red] {rule_id}")
        raise typer.Exit(2)

    rule = RULE_REGISTRY[rule_id]
    sev_style = "red" if rule.severity.value == "error" else "yellow"

    console.print(f"\n[bold cyan]{rule_id}[/bold cyan]  [{sev_style}]{rule.severity.value}[/{sev_style}]")
    console.print(f"[bold]{rule.description}[/bold]\n")
    if rule.rationale:
        console.print(rule.rationale)
    console.print()


@app.command("doctor")
def doctor() -> None:
    """Check tool dependencies and environment."""
    import importlib

    deps = [
        ("typer", "typer"),
        ("rich", "rich"),
        ("frontmatter", "python-frontmatter"),
        ("markdown_it", "markdown-it-py"),
        ("yaml", "pyyaml"),
    ]

    all_ok = True
    for module, package in deps:
        try:
            importlib.import_module(module)
            console.print(f"  [green]✓[/green] {package}")
        except ImportError:
            console.print(f"  [red]✗[/red] {package} — not installed")
            all_ok = False

    if all_ok:
        console.print("\n[green]All dependencies satisfied.[/green]")
    else:
        console.print("\n[red]Some dependencies are missing. Run: pip install skill-lint[/red]")
        raise typer.Exit(2)


def _report_github(result) -> None:
    """Emit GitHub Actions annotation lines."""
    for v in result.violations:
        level = "error" if v.severity.value == "error" else "warning"
        line_part = f",line={v.line}" if v.line else ""
        print(f"::{level} file={v.file}{line_part}::{v.rule}: {v.message}")


if __name__ == "__main__":
    app()
