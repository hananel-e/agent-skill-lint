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


@roo_app.command("score")
def roo_score(
    path: str = typer.Argument(".", help="Path to scan (file or directory)."),
    format: OutputFormat = typer.Option(
        OutputFormat.text, "--format", help="Output format (text or json)."
    ),
    config: Optional[Path] = typer.Option(
        None, "--config", help="Path to .skill-lint.yaml config file."
    ),
    ignore: Optional[str] = typer.Option(
        None, "--ignore", help="Comma-separated rule IDs to ignore."
    ),
    fail_under: Optional[int] = typer.Option(
        None, "--fail-under", help="Exit 1 if average score is below this threshold (0-100)."
    ),
) -> None:
    """Score skill files and display A-F quality grades.

    Runs the full lint suite and converts violations into a numeric score
    (0-100) and letter grade per skill, plus an aggregate average.

    Scoring: base 100, -15 per ERROR, -5 per WARNING (clamped to 0).
    Grades: A ≥90, B ≥80, C ≥70, D ≥60, F <60.
    """
    import json as _json
    from skill_lint.config import load_config
    from skill_lint.runner import run_scan
    from skill_lint.scorer import score_result
    from rich.table import Table

    cfg = load_config(config)
    ignored_rules: set[str] = set()
    if ignore:
        ignored_rules.update(r.strip() for r in ignore.split(","))
    ignored_rules.update(cfg.get("ignore_rules", []))

    scan_path = Path(path)
    if not scan_path.exists():
        err_console.print(f"[red]Error:[/red] Path not found: {path}")
        raise typer.Exit(2)

    result = run_scan(scan_path, cfg=cfg, ignored_rules=ignored_rules)
    scan_score = score_result(result)

    if format == OutputFormat.json:
        console.print(_json.dumps(scan_score.to_dict(), indent=2))
        _maybe_fail_under(scan_score.average_score, fail_under)
        return

    # ── text output ──────────────────────────────────────────────────────────
    table = Table(title="Skill Quality Scores", show_lines=True)
    table.add_column("Skill", style="dim")
    table.add_column("Score", justify="right", no_wrap=True)
    table.add_column("Grade", justify="center", no_wrap=True)
    table.add_column("Errors", justify="right", no_wrap=True)
    table.add_column("Warnings", justify="right", no_wrap=True)

    for ss in scan_score.skill_scores:
        table.add_row(
            str(ss.path),
            str(ss.score),
            f"[{ss.grade_style}]{ss.grade}[/{ss.grade_style}]",
            f"[red]{ss.errors}[/red]" if ss.errors else "0",
            f"[yellow]{ss.warnings}[/yellow]" if ss.warnings else "0",
        )

    console.print(table)

    avg = scan_score.average_score
    avg_grade = scan_score.average_grade
    avg_style = {
        "A": "bold green", "B": "green", "C": "yellow",
        "D": "dark_orange", "F": "bold red",
    }.get(avg_grade, "white")

    console.print(
        f"\nAverage score: [bold]{avg:.1f}[/bold]  "
        f"Grade: [{avg_style}]{avg_grade}[/{avg_style}]  "
        f"({scan_score.total_errors} errors, {scan_score.total_warnings} warnings)"
    )

    _maybe_fail_under(avg, fail_under)


def _maybe_fail_under(avg: float, threshold: Optional[int]) -> None:
    if threshold is not None and avg < threshold:
        err_console.print(
            f"[red]Score {avg:.1f} is below --fail-under threshold of {threshold}[/red]"
        )
        raise typer.Exit(1)


@roo_app.command("simulate")
def roo_simulate(
    query: str = typer.Argument(..., help="Natural-language routing query to simulate."),
    path: str = typer.Option(".", "--path", help="Path to scan for skill files."),
    format: OutputFormat = typer.Option(
        OutputFormat.text, "--format", help="Output format (text or json)."
    ),
    config: Optional[Path] = typer.Option(
        None, "--config", help="Path to .skill-lint.yaml config file."
    ),
    top: int = typer.Option(5, "--top", help="Number of top matches to show."),
    fuzzy_threshold: float = typer.Option(
        0.75, "--fuzzy-threshold", help="SequenceMatcher ratio threshold for fuzzy matching (0-1)."
    ),
    embeddings: bool = typer.Option(
        False, "--embeddings/--no-embeddings",
        help="Use sentence-transformers cosine similarity instead of heuristic scoring. "
             "Requires: pip install agent-skill-lint[embeddings]"
    ),
    embedding_model: str = typer.Option(
        "all-MiniLM-L6-v2", "--embedding-model",
        help="sentence-transformers model name (only used with --embeddings)."
    ),
) -> None:
    """Simulate skill routing for a natural-language query.

    Ranks all scanned skills by how well their description matches the query.

    \b
    Default: heuristic keyword scoring (no extra deps).
    With --embeddings: cosine similarity via sentence-transformers (more accurate).

    Useful for spotting ambiguous descriptions or missing coverage before
    deploying to a live agent.
    """
    import json as _json
    from skill_lint.config import load_config
    from skill_lint.runner import run_scan
    from skill_lint.simulator import simulate, DEFAULT_EMBEDDING_MODEL
    from rich.table import Table

    cfg = load_config(config)
    scan_path = Path(path)
    if not scan_path.exists():
        err_console.print(f"[red]Error:[/red] Path not found: {path}")
        raise typer.Exit(2)

    result = run_scan(scan_path, cfg=cfg, ignored_rules=set())
    skills = result.skill_files

    if not skills:
        err_console.print("[yellow]No skill files found to simulate against.[/yellow]")
        raise typer.Exit(0)

    if embeddings:
        try:
            import sentence_transformers  # noqa: F401
        except ImportError:
            err_console.print(
                    "[yellow]Warning:[/yellow] sentence-transformers not installed. "
                    "Falling back to heuristic scoring.\n"
                    "[dim]Install with: pip install 'agent-skill-lint[embeddings]'[/dim]"
                )

    sim = simulate(
        query,
        skills,
        fuzzy_threshold=fuzzy_threshold,
        top_n=top,
        use_embeddings=embeddings,
        embedding_model=embedding_model,
    )

    if format == OutputFormat.json:
        console.print(_json.dumps(sim.to_dict(), indent=2))
        raise typer.Exit(0)

    # ── text output ──────────────────────────────────────────────────────────
    backend = "embeddings" if embeddings else "heuristic"
    console.print(
        f'\n[bold]Routing simulation[/bold] for query: "[italic]{query}[/italic]"  '
        f'[dim]({backend})[/dim]\n'
    )

    if not sim.matches or sim.top_match is None or sim.top_match.score == 0:
        console.print("[yellow]No matching skills found.[/yellow]")
        raise typer.Exit(0)

    if sim.is_ambiguous:
        console.print(
            "[yellow]⚠ Ambiguous routing:[/yellow] top two matches are within 10% of each other.\n"
        )

    table = Table(show_lines=True)
    table.add_column("Rank", justify="right", no_wrap=True, style="dim")
    table.add_column("Skill", no_wrap=True)
    table.add_column("Score", justify="right", no_wrap=True)
    table.add_column("Match", no_wrap=True)
    table.add_column("Matched tokens")
    table.add_column("Description (preview)")

    type_styles = {"exact": "green", "substring": "cyan", "fuzzy": "yellow", "none": "dim"}

    for i, match in enumerate(sim.matches, 1):
        style = type_styles.get(match.match_type, "white")
        score_pct = f"{match.score * 100:.1f}%"
        table.add_row(
            str(i),
            match.skill_name,
            f"[bold]{score_pct}[/bold]" if i == 1 else score_pct,
            f"[{style}]{match.match_type}[/{style}]",
            ", ".join(match.matched_tokens) or "—",
            match.description_preview or "[dim]no description[/dim]",
        )

    console.print(table)
    console.print(
        f"\n[dim]Scanned {len(skills)} skill(s) · "
        f"top match: [bold]{sim.top_match.skill_name}[/bold] "
        f"({sim.top_match.score * 100:.1f}%)[/dim]"
    )


@roo_app.command("sync")
def roo_sync(
    path: str = typer.Argument(".", help="Path to scan (file or directory)."),
    format: OutputFormat = typer.Option(
        OutputFormat.text, "--format", help="Output format (text or json)."
    ),
    config: Optional[Path] = typer.Option(
        None, "--config", help="Path to .skill-lint.yaml config file."
    ),
    roomodes: Optional[Path] = typer.Option(
        None, "--roomodes", help="Path to a specific .roomodes file (default: auto-discover)."
    ),
) -> None:
    """Check alignment between .roomodes definitions and skill files.

    Detects two classes of drift:

    \b
    - Undocumented modes: defined in .roomodes but no skill covers them.
    - Orphaned slugs: a skill's modeSlugs references a mode not in .roomodes.

    Exits 0 if clean, 1 if drift is detected, 2 on error.
    """
    import json as _json
    from skill_lint.config import load_config
    from skill_lint.runner import run_scan, _find_repo_root
    from skill_lint.sync import load_roomodes, sync_report

    cfg = load_config(config)
    scan_path = Path(path)
    if not scan_path.exists():
        err_console.print(f"[red]Error:[/red] Path not found: {path}")
        raise typer.Exit(2)

    result = run_scan(scan_path, cfg=cfg, ignored_rules=set())
    skills = result.skill_files

    repo_root = _find_repo_root(scan_path)

    if roomodes:
        import json as _j
        try:
            data = _j.loads(roomodes.read_text(encoding="utf-8"))
            roomodes_slugs = {
                m["slug"]: roomodes
                for m in data.get("customModes", [])
                if isinstance(m.get("slug"), str)
            }
        except Exception as exc:
            err_console.print(f"[red]Error reading {roomodes}:[/red] {exc}")
            raise typer.Exit(2)
    else:
        roomodes_slugs = load_roomodes(repo_root)

    if not roomodes_slugs:
        console.print(
            "[yellow]No .roomodes files found in the repo.[/yellow] "
            "Sync check requires at least one .roomodes file."
        )
        raise typer.Exit(0)

    report = sync_report(skills, roomodes_slugs)

    if format == OutputFormat.json:
        console.print(_json.dumps(report.to_dict(), indent=2))
        raise typer.Exit(0 if report.is_clean else 1)

    console.print(f"\n[bold]Framework sync report[/bold]  (repo root: {repo_root})\n")
    console.print(
        f"  .roomodes modes : [bold]{len(roomodes_slugs)}[/bold]  "
        f"({', '.join(sorted(roomodes_slugs))})"
    )
    console.print(
        f"  Skills scanned  : [bold]{len(skills)}[/bold]  "
        f"Covered slugs: [bold]{len(report.covered_slugs)}[/bold]\n"
    )

    if report.is_clean:
        console.print("[green]✓ All modes are covered and all skill slugs are defined.[/green]")
        raise typer.Exit(0)

    if report.undocumented_modes:
        console.print(
            f"[yellow]Undocumented modes[/yellow] "
            f"({len(report.undocumented_modes)}) — defined in .roomodes but no skill covers them:"
        )
        for slug in report.undocumented_modes:
            src = report.roomodes_slugs.get(slug)
            console.print(f"  [yellow]•[/yellow] {slug}  [dim]({src})[/dim]")
        console.print()

    if report.orphaned_skill_slugs:
        console.print(
            f"[red]Orphaned skill slugs[/red] "
            f"({len(report.orphaned_skill_slugs)}) — referenced by skills but absent from .roomodes:"
        )
        for slug, paths in sorted(report.orphaned_skill_slugs.items()):
            skill_list = ", ".join(str(p) for p in paths)
            console.print(f"  [red]•[/red] {slug}  [dim]({skill_list})[/dim]")
        console.print()

    raise typer.Exit(1)


@roo_app.command("update-slugs")
def roo_update_slugs(
    timeout: int = typer.Option(10, "--timeout", help="HTTP timeout in seconds."),
) -> None:
    """Fetch the latest known mode slugs from GitHub and update the local cache.

    The cache is stored at ~/.cache/skill-lint/slugs.json and is used by
    ROO005 to validate modeSlugs values without requiring a code update.
    """
    from skill_lint.slug_registry import cache_path, fetch_and_cache

    console.print("[bold]Fetching latest mode slugs…[/bold]")
    ok, message = fetch_and_cache(timeout=timeout)
    if ok:
        console.print(f"  [green]✓[/green] {message}")
        console.print(f"\n[dim]Cache location: {cache_path()}[/dim]")
    else:
        err_console.print(f"  [red]✗[/red] {message}")
        err_console.print(
            "\n[yellow]Tip:[/yellow] ROO005 will continue using the bundled slug list."
        )
        raise typer.Exit(1)


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
