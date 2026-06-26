"""Rich terminal reporter for skill-lint."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from rich.console import Console
from rich.rule import Rule
from rich.text import Text

from skill_lint.models import ScanResult, Severity, Violation


class ConsoleReporter:
    """Renders scan results as a rich terminal output."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def report(self, result: ScanResult) -> None:
        # Group violations by file
        by_file: dict[str, list[Violation]] = defaultdict(list)
        for v in result.violations:
            by_file[v.file].append(v)

        # Print per-file sections
        for file_path in sorted(by_file.keys()):
            violations = by_file[file_path]
            self.console.print(f"\n[bold]{file_path}[/bold]")
            for v in sorted(violations, key=lambda x: (x.line or 0, x.rule)):
                self._print_violation(v)

        # Print clean files (only if there are any)
        # We don't have the full file list here, so we just note the count

        # Summary line
        self.console.print()
        self.console.print(Rule(style="dim"))
        summary = self._build_summary(result)
        self.console.print(summary)

    def _print_violation(self, v: Violation) -> None:
        if v.severity == Severity.ERROR:
            icon = "[red]✗[/red]"
            sev_label = "[red][error][/red]"
        else:
            icon = "[yellow]⚠[/yellow]"
            sev_label = "[yellow][warning][/yellow]"

        line_str = f":{v.line}" if v.line else ""
        rule_str = f"[cyan]{v.rule}[/cyan]"
        self.console.print(
            f"  {icon} {rule_str}  {v.message}{line_str}  {sev_label}"
        )

    def _build_summary(self, result: ScanResult) -> Text:
        parts = []

        if result.errors > 0:
            parts.append(Text(f"{result.errors} error{'s' if result.errors != 1 else ''}", style="bold red"))
        else:
            parts.append(Text("0 errors", style="green"))

        parts.append(Text("  |  ", style="dim"))

        if result.warnings > 0:
            parts.append(Text(f"{result.warnings} warning{'s' if result.warnings != 1 else ''}", style="bold yellow"))
        else:
            parts.append(Text("0 warnings", style="green"))

        parts.append(Text("  |  ", style="dim"))
        parts.append(Text(f"{result.files_scanned} file{'s' if result.files_scanned != 1 else ''} scanned", style="dim"))
        parts.append(Text("  |  ", style="dim"))

        if result.files_clean > 0:
            parts.append(Text(f"{result.files_clean} clean", style="green"))
        else:
            parts.append(Text("0 clean", style="dim"))

        combined = Text()
        for part in parts:
            combined.append_text(part)
        return combined
