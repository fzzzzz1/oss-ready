"""Audit checks used by the :mod:`oss_ready` command line tool.

Each check is a function taking the project root and returning a list of
:class:`Finding` objects. Checks report problems rather than raising them:
a malformed file is a finding, never a crash.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

OK = "ok"
WARN = "warn"
ERROR = "error"

SKIP_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        "dist",
        "build",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        "target",
        ".idea",
        ".vscode",
    }
)

# Directories that should never be committed.
BUILD_ARTIFACTS = (
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    "target",
)

README_NAMES = ("readme.md", "readme.rst", "readme.txt", "readme")
LICENSE_NAMES = ("license", "licence", "copying", "unlicense")

MIN_README_CHARS = 200
MAX_SCAN_BYTES = 1_000_000
LARGE_FILE_BYTES = 5_000_000
MAX_REPORTED_HITS = 5

GITIGNORE_HINTS = (
    ".env",
    "__pycache__",
    "node_modules",
    "*.log",
    ".venv",
    "dist",
    "build",
    "*.pyc",
)

CI_LOCATIONS = (
    ".github/workflows",
    ".gitlab-ci.yml",
    ".circleci/config.yml",
    "azure-pipelines.yml",
    "Jenkinsfile",
    ".travis.yml",
)

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9]{20,}")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}")),
    ("Slack token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    (
        "private key block",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
    (
        "hardcoded credential",
        re.compile(
            r"(?i)\b(?:password|passwd|secret|api_key|apikey|access_token)"
            r"\s*[:=]\s*['\"][^'\"]{6,}['\"]"
        ),
    ),
)

LICENSE_SIGNATURES: tuple[tuple[str, Callable[[str], bool]], ...] = (
    ("Apache-2.0", lambda t: "apache license" in t and "version 2.0" in t),
    ("AGPL-3.0", lambda t: "gnu affero general public license" in t),
    ("GPL-3.0", lambda t: "gnu general public license" in t and "version 3" in t),
    ("GPL-2.0", lambda t: "gnu general public license" in t and "version 2" in t),
    ("MPL-2.0", lambda t: "mozilla public license" in t),
    (
        "MIT",
        lambda t: "mit license" in t
        or "permission is hereby granted, free of charge" in t,
    ),
    ("BSD", lambda t: "redistribution and use in source and binary forms" in t),
    ("Unlicense", lambda t: "this is free and unencumbered software" in t),
)


@dataclass(frozen=True)
class Finding:
    """A single observation produced by a check."""

    level: str
    check: str
    message: str


def walk_files(root: Path) -> Iterable[Path]:
    """Yield files under *root*, skipping vendor and cache directories."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            yield Path(dirpath) / name


def _read_text(path: Path) -> str:
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    if len(data) > MAX_SCAN_BYTES:
        return ""
    return data.decode("utf-8", errors="ignore")


def _root_file(root: Path, names: tuple[str, ...]) -> Path | None:
    lowered = {name.lower() for name in names}
    for entry in sorted(root.iterdir()):
        if entry.is_file() and entry.name.lower() in lowered:
            return entry
    return None


def check_required_files(root: Path) -> list[Finding]:
    if not _root_file(root, README_NAMES):
        return [Finding(ERROR, "files", "no README found at the project root")]
    if not _root_file(root, LICENSE_NAMES):
        return [Finding(ERROR, "files", "no LICENSE file: nobody may legally reuse this")]
    return [Finding(OK, "files", "README and LICENSE present")]


def check_license(root: Path) -> list[Finding]:
    path = _root_file(root, LICENSE_NAMES)
    if path is None:
        return [Finding(ERROR, "license", "missing LICENSE file")]
    text = _read_text(path).lower()
    if not text.strip():
        return [Finding(WARN, "license", f"{path.name} is empty or unreadable")]
    for name, matches in LICENSE_SIGNATURES:
        if matches(text):
            return [Finding(OK, "license", f"{path.name} looks like {name}")]
    return [
        Finding(
            WARN,
            "license",
            f"{path.name} is present but not a recognised standard license",
        )
    ]


def check_readme(root: Path) -> list[Finding]:
    path = _root_file(root, README_NAMES)
    if path is None:
        return [Finding(ERROR, "readme", "missing README")]
    text = _read_text(path)
    if len(text.strip()) < MIN_README_CHARS:
        return [
            Finding(
                WARN,
                "readme",
                f"README is only {len(text.strip())} characters; "
                f"aim for at least {MIN_README_CHARS}",
            )
        ]
    if not any(line.lstrip().startswith("#") for line in text.splitlines()):
        return [Finding(WARN, "readme", "README has no markdown heading")]
    return [Finding(OK, "readme", f"{path.name} has a heading and real content")]


def check_gitignore(root: Path) -> list[Finding]:
    path = next(
        (p for p in root.iterdir() if p.is_file() and p.name.lower() == ".gitignore"),
        None,
    )
    if path is None:
        return [Finding(WARN, "gitignore", "no .gitignore; caches and secrets may leak")]
    text = _read_text(path).lower()
    hits = sum(1 for hint in GITIGNORE_HINTS if hint in text)
    if hits < 3:
        return [
            Finding(
                WARN,
                "gitignore",
                f".gitignore covers only {hits} of {len(GITIGNORE_HINTS)} common patterns",
            )
        ]
    return [Finding(OK, "gitignore", f".gitignore covers {hits} common patterns")]


def check_artifacts(root: Path) -> list[Finding]:
    found = [
        name
        for name in BUILD_ARTIFACTS
        if (root / name).is_dir()
    ]
    if not found:
        return [Finding(OK, "artifacts", "no build artifacts at the project root")]
    return [
        Finding(WARN, "artifacts", f"build artifact directory present: {name}/")
        for name in found[:MAX_REPORTED_HITS]
    ]


def check_large_files(root: Path) -> list[Finding]:
    large: list[tuple[Path, int]] = []
    for path in walk_files(root):
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > LARGE_FILE_BYTES:
            large.append((path, size))
    if not large:
        return [Finding(OK, "large files", "no file over 5 MB")]
    return [
        Finding(
            WARN,
            "large files",
            f"{path.relative_to(root)} is {size / 1_000_000:.1f} MB; "
            "use Git LFS or keep it out of the repo",
        )
        for path, size in large[:MAX_REPORTED_HITS]
    ]


def check_secrets(root: Path) -> list[Finding]:
    hits: list[str] = []
    for path in walk_files(root):
        try:
            if path.stat().st_size > MAX_SCAN_BYTES:
                continue
        except OSError:
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        if b"\x00" in raw[:8192]:
            continue  # binary
        text = raw.decode("utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    hits.append(f"{path.relative_to(root)}:{lineno} ({label})")
                    break
            if len(hits) >= MAX_REPORTED_HITS:
                break
        if len(hits) >= MAX_REPORTED_HITS:
            break
    if not hits:
        return [Finding(OK, "secrets", "no obvious credentials in tracked text files")]
    return [
        Finding(ERROR, "secrets", f"possible credential at {hit}") for hit in hits
    ]


def check_ci(root: Path) -> list[Finding]:
    for location in CI_LOCATIONS:
        candidate = root / location
        if candidate.is_dir() and any(candidate.iterdir()):
            return [Finding(OK, "ci", f"CI config found at {location}")]
        if candidate.is_file():
            return [Finding(OK, "ci", f"CI config found at {location}")]
    return [Finding(WARN, "ci", "no CI configuration; tests will not run on push")]


CHECKS = (
    check_required_files,
    check_license,
    check_readme,
    check_gitignore,
    check_artifacts,
    check_large_files,
    check_secrets,
    check_ci,
)


def run_all(root: Path) -> list[Finding]:
    """Run every check against *root* and return the findings."""
    root = Path(root)
    findings: list[Finding] = []
    for check in CHECKS:
        findings.extend(check(root))
    return findings


def score(findings: list[Finding]) -> int:
    """Return a 0-100 readiness score (ok=1, warn=0.5, error=0)."""
    if not findings:
        return 0
    points = {OK: 1.0, WARN: 0.5, ERROR: 0.0}
    total = sum(points.get(f.level, 0.0) for f in findings)
    return round(100 * total / len(findings))
