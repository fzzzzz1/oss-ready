"""Tests for the oss-ready checks."""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from oss_ready.checks import ERROR, OK, WARN, run_all, score
from oss_ready.cli import main

MIT_LICENSE = """MIT License

Copyright (c) 2026 deepseek1 contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction.
"""

README = """# sample

A small sample project used by the test suite. It exists so the audit has
something realistic to look at: a heading, a paragraph of prose that goes on
for a little while, and enough characters to clear the minimum length check.
"""

GITIGNORE = "__pycache__/\n.venv/\n.env\n*.log\ndist/\nbuild/\n"


class ProjectFixture:
    """Build a throwaway project tree inside a temporary directory."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def __enter__(self) -> "ProjectFixture":
        return self

    def __exit__(self, *exc: object) -> None:
        self._tmp.cleanup()

    def write(self, relative: str, content: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def clean(self) -> Path:
        self.write("README.md", README)
        self.write("LICENSE", MIT_LICENSE)
        self.write(".gitignore", GITIGNORE)
        self.write(".github/workflows/ci.yml", "name: ci\non: push\n")
        return self.root


def levels(findings):
    return [f.level for f in findings]


class CleanProjectTests(unittest.TestCase):
    def test_clean_project_has_no_errors_or_warnings(self):
        with ProjectFixture() as fx:
            findings = run_all(fx.clean())
            self.assertEqual(levels(findings), [OK] * len(findings))
            self.assertEqual(score(findings), 100)

    def test_cli_exits_zero_on_clean_project(self):
        with ProjectFixture() as fx:
            root = fx.clean()
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = main([str(root)])
            self.assertEqual(code, 0)
            self.assertIn("score 100%", buffer.getvalue())


class MissingFileTests(unittest.TestCase):
    def test_missing_license_is_an_error(self):
        with ProjectFixture() as fx:
            fx.clean()
            (fx.root / "LICENSE").unlink()
            findings = run_all(fx.root)
            self.assertIn(ERROR, levels(findings))
            self.assertTrue(
                any("LICENSE" in f.message for f in findings if f.level == ERROR)
            )

    def test_missing_readme_is_an_error(self):
        with ProjectFixture() as fx:
            fx.clean()
            (fx.root / "README.md").unlink()
            findings = run_all(fx.root)
            self.assertIn(ERROR, levels(findings))

    def test_missing_gitignore_warns(self):
        with ProjectFixture() as fx:
            fx.clean()
            (fx.root / ".gitignore").unlink()
            findings = run_all(fx.root)
            self.assertIn(WARN, levels(findings))
            self.assertNotIn(ERROR, levels(findings))


class LicenseTests(unittest.TestCase):
    def test_unknown_license_warns(self):
        with ProjectFixture() as fx:
            fx.clean()
            (fx.root / "LICENSE").write_text(
                "Proprietary. All rights reserved.\n", encoding="utf-8"
            )
            findings = run_all(fx.root)
            self.assertIn(WARN, levels(findings))

    def test_apache_license_is_recognised(self):
        with ProjectFixture() as fx:
            fx.clean()
            (fx.root / "LICENSE").write_text(
                "Apache License\nVersion 2.0, January 2004\n", encoding="utf-8"
            )
            findings = run_all(fx.root)
            self.assertNotIn(ERROR, levels(findings))
            self.assertTrue(
                any("Apache-2.0" in f.message for f in findings if f.level == OK)
            )


class ContentTests(unittest.TestCase):
    def test_short_readme_warns(self):
        with ProjectFixture() as fx:
            fx.clean()
            (fx.root / "README.md").write_text("# tiny\n", encoding="utf-8")
            findings = run_all(fx.root)
            self.assertIn(WARN, levels(findings))

    def test_detected_secret_is_an_error(self):
        with ProjectFixture() as fx:
            fx.clean()
            # Assembled at runtime so this file does not trip its own scanner.
            key = "AKIA" + "IOSFODNN7EXAMPLE"
            fx.write("config.py", f'AWS_KEY = "{key}"\n')
            findings = run_all(fx.root)
            errors = [f for f in findings if f.level == ERROR]
            self.assertTrue(any("AWS access key" in f.message for f in errors))

    def test_vendor_directories_are_skipped(self):
        with ProjectFixture() as fx:
            fx.clean()
            key = "AKIA" + "IOSFODNN7EXAMPLE"
            fx.write("node_modules/pkg/index.js", f'const k = "{key}"\n')
            findings = run_all(fx.root)
            self.assertNotIn(ERROR, levels(findings))

    def test_build_artifact_warns(self):
        with ProjectFixture() as fx:
            fx.clean()
            fx.write("dist/bundle.js", "console.log(1)\n")
            findings = run_all(fx.root)
            self.assertTrue(
                any(f.check == "artifacts" and f.level == WARN for f in findings)
            )


class ScoreTests(unittest.TestCase):
    def test_score_is_bounded(self):
        with ProjectFixture() as fx:
            findings = run_all(fx.clean())
            self.assertGreaterEqual(score(findings), 0)
            self.assertLessEqual(score(findings), 100)

    def test_score_drops_with_errors(self):
        with ProjectFixture() as fx:
            clean = run_all(fx.clean())
            (fx.root / "LICENSE").unlink()
            broken = run_all(fx.root)
            self.assertLess(score(broken), score(clean))


if __name__ == "__main__":
    unittest.main()
