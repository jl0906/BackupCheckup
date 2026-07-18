#!/usr/bin/env python3
"""Enforce separate statement and branch coverage thresholds."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    """Read coverage.py JSON totals and enforce both coverage dimensions."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage-json", default="coverage.json")
    parser.add_argument("--statements", type=float, default=95.0)
    parser.add_argument("--branches", type=float, default=85.0)
    args = parser.parse_args()

    report_path = Path(args.coverage_json)
    if not report_path.is_file():
        print(f"Coverage report not found: {report_path}", file=sys.stderr)
        return 2

    totals = json.loads(report_path.read_text(encoding="utf-8")).get("totals", {})
    statement_coverage = float(totals.get("percent_statements_covered", 0.0))
    branch_coverage = float(totals.get("percent_branches_covered", 0.0))
    print(
        f"Statement coverage: {statement_coverage:.2f}% "
        f"(required {args.statements:.2f}%)"
    )
    print(f"Branch coverage: {branch_coverage:.2f}% (required {args.branches:.2f}%)")
    failed = statement_coverage < args.statements or branch_coverage < args.branches
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
