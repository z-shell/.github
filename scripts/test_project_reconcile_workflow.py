#!/usr/bin/env python3
"""Exercise the production workflow's shell entry point without GitHub writes."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WorkflowPrivacyTest(unittest.TestCase):
    def workflow(self):
        text = (ROOT / ".github/workflows/project-reconcile.yml").read_text()
        match = re.search(r"        run: \|\n((?:          .*\n|\n)+)", text)
        self.assertIsNotNone(match)
        assert match is not None
        return text, textwrap.dedent(match.group(1))

    def test_upload_allowlist_contains_only_summary_on_failure_too(self):
        text, script = self.workflow()
        upload = text.split("      - name: Upload reconciliation report\n", 1)[1]
        self.assertIn("        if: always()", upload)
        paths = re.findall(r"^          path: (.+)$", upload, re.MULTILINE)
        self.assertEqual(["${{ runner.temp }}/project-reconcile-summary.json"], paths)
        self.assertNotIn(".ndjson", text)
        self.assertNotIn("gh api", script)
        self.assertIn("--require-token", script)
        self.assertIn("scripts/project_reconcile_live.py", script)

    def test_missing_token_emits_only_failure_summary(self):
        _, script = self.workflow()
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.json"
            env = {
                "PATH": os.environ["PATH"],
                "GH_TOKEN": "",
                "APPLY": "false",
                "ORGANIZATION": "z-shell",
                "PROJECT_NUMBER": "28",
                "REPORT_PATH": str(report),
            }
            result = subprocess.run(
                ["bash", "-c", script],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertEqual("error", json.loads(report.read_text())["status"])
            self.assertEqual([report], list(Path(tmp).iterdir()))
            self.assertNotIn("Traceback", result.stderr)

    def test_apply_flag_is_explicit_and_dry_run_is_default(self):
        _, script = self.workflow()
        for apply in ["false", "true"]:
            with self.subTest(apply=apply):
                env = {
                    "PATH": os.environ["PATH"],
                    "APPLY": apply,
                    "ORGANIZATION": "z-shell",
                    "PROJECT_NUMBER": "28",
                    "REPORT_PATH": "/unused/report.json",
                }
                stub = 'python3() { printf "%s\\n" "$@"; }\n'
                result = subprocess.run(
                    ["bash", "-c", stub + script],
                    cwd=ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(
                    apply == "true", "--apply" in result.stdout.splitlines()
                )

    def test_privacy_suite_has_a_pull_request_ci_caller(self):
        path = ROOT / ".github/workflows/project-reconcile-test.yml"
        self.assertTrue(
            path.exists(), "Privacy regressions need an automatic CI caller"
        )
        text = path.read_text()
        self.assertIn("  pull_request:", text)
        self.assertIn("test_project_reconcile*.py", text)
        self.assertNotIn("secrets.", text)


if __name__ == "__main__":
    unittest.main()
