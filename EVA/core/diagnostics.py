"""Human-friendly diagnostics command and repo-safe health probes.

This module intentionally never prints secrets or provider-state details. It
returns a minimal, structured report for a developer to inspect in a CLI.
"""
from __future__ import annotations

import json
import os
import platform
import sys
import time
from pathlib import Path


def diagnostic_report(root: str | Path = ".") -> dict[str, object]:
    """Return a safe turn/task diagnostics envelope without exposing secrets."""
    root = Path(root)
    report = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "platform_system": platform.system(),
        "workspace_root": str(root.resolve()),
        "gitignore_exists": (root / ".gitignore").exists(),
        "env_example_exists": (root / ".env.example").exists(),
        "config_manifest_exists": (root / "config" / "api_keys.json").exists(),
        "safe_subprocess_module": "core.safe_subprocess",
        "safe_logging_module": "core.safe_logging",
        "service_boundaries_module": "core.service_boundaries",
        "tests": "python -m pytest -q",
        "diagnostics": "python -m core.diagnostics --report",
        "notes": "Secrets and certificates are never committed or logged.",
    }
    return report


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if "--report" in argv or "--json" in argv:
        print(json.dumps(diagnostic_report(Path(__file__).resolve().parent.parent), indent=2, sort_keys=True))
        return 0
    print("MARK L diagnostics: safe repository metadata only")
    for key, value in diagnostic_report(Path(__file__).resolve().parent.parent).items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
