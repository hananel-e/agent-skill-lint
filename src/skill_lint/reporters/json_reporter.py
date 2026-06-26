"""JSON reporter for skill-lint."""

from __future__ import annotations

import json
import sys

from skill_lint.models import ScanResult


class JsonReporter:
    """Renders scan results as JSON to stdout."""

    def report(self, result: ScanResult) -> None:
        output = result.to_dict()
        print(json.dumps(output, indent=2))
