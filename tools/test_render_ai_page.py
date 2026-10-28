"""Tests for the staging /ai page renderer."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "render_ai_page.py"
PRODUCTION = "https://punkto.xyz"
TARGET = "https://stage.example.test"


class RenderAiPageTest(unittest.TestCase):
    def run_renderer(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], cwd=ROOT,
            text=True, capture_output=True, check=False,
        )

    def test_render_replaces_every_origin_and_changes_nothing_else(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.html"
            output = Path(tmp) / "output.html"
            original = f"one {PRODUCTION} two {PRODUCTION}/nodes.json\n"
            source.write_text(original, encoding="utf-8")
            result = self.run_renderer("--source", str(source), "--origin", TARGET, "--output", str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            rendered = output.read_bytes()
            self.assertEqual(rendered, original.replace(PRODUCTION, TARGET).encode("utf-8"))
            self.assertNotIn(PRODUCTION.encode(), rendered)
            self.assertEqual(rendered.count(TARGET.encode()), original.count(PRODUCTION))

    def test_rejects_invalid_origins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.html"
            output = Path(tmp) / "output.html"
            source.write_text(PRODUCTION, encoding="utf-8")
            for origin in ("punkto.xyz", "https://stage.example.test/", "https://stage.example.test/path"):
                with self.subTest(origin=origin):
                    result = self.run_renderer("--source", str(source), "--origin", origin, "--output", str(output))
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("--origin", result.stderr)

    def test_nonexistent_output_directory_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.html"
            source.write_text(PRODUCTION, encoding="utf-8")
            output = Path(tmp) / "missing" / "output.html"
            result = self.run_renderer("--source", str(source), "--origin", TARGET, "--output", str(output))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("error:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_check_matches_and_detects_difference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.html"
            output = Path(tmp) / "output.html"
            source.write_text(f"{PRODUCTION}/nodes.json\n", encoding="utf-8")
            args = ("--source", str(source), "--origin", TARGET, "--output", str(output))
            self.assertEqual(self.run_renderer(*args).returncode, 0)
            check_args = (*args, "--check")
            self.assertEqual(self.run_renderer(*check_args).returncode, 0)
            output.write_text("different", encoding="utf-8")
            failed = self.run_renderer(*check_args)
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("--check failed", failed.stderr)


if __name__ == "__main__":
    unittest.main()
