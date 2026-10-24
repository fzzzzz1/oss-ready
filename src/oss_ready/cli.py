"""Command line interface for oss-ready."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .checks import ERROR, OK, WARN, Finding, run_all, score

MARKERS = {OK: "[ok]  ", WARN: "[warn]", ERROR: "[!!]  "}

BANNER = "oss-ready {version} - is this project ready to go public?"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oss-ready",
        description="Audit a project directory before making it public.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="project directory to audit (default: current directory)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of a text report",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero when warnings are present, not just errors",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="oss-ready 0.1.0",
    )
    return parser


def render(root: Path, findings: list[Finding], total: int) -> str:
    lines = [
        BANNER.format(version="0.1.0"),
        f"root: {root}",
        "-" * 64,
    ]
    for finding in findings:
        marker = MARKERS.get(finding.level, "[?]   ")
        lines.append(f"  {marker} {finding.check:<11} {finding.message}")
    counts = {level: sum(1 for f in findings if f.level == level) for level in (OK, WARN, ERROR)}
    lines.append("-" * 64)
    lines.append(
        f"  score {total}%   "
        f"({counts[OK]} ok, {counts[WARN]} warn, {counts[ERROR]} error)"
    )
    if counts[ERROR]:
        lines.append("  verdict: NOT ready - fix the errors above first")
    elif counts[WARN]:
        lines.append("  verdict: mostly ready - review the warnings")
    else:
        lines.append("  verdict: ready to publish")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.path).expanduser()
    if not root.is_dir():
        print(f"oss-ready: not a directory: {root}", file=sys.stderr)
        return 2
    root = root.resolve()

    findings = run_all(root)
    total = score(findings)

    if args.json:
        payload = {
            "root": str(root),
            "score": total,
            "findings": [
                {"level": f.level, "check": f.check, "message": f.message}
                for f in findings
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render(root, findings, total))

    failed = any(f.level == ERROR for f in findings)
    if args.strict and any(f.level == WARN for f in findings):
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
