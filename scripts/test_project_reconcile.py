#!/usr/bin/env python3
"""Tests for the Project 28 reconciliation report generator."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import project_reconcile


class ProjectReconcileTest(unittest.TestCase):
    def write_ndjson(self, directory: Path, name: str, records: list[dict[str, object]]) -> Path:
        path = directory / name
        path.write_text("".join(json.dumps(record) + "\n" for record in records))
        return path

    def test_report_identifies_missing_and_stale_open_issues(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            open_issues = self.write_ndjson(
                directory,
                "open-issues.ndjson",
                [
                    {
                        "url": "https://github.com/z-shell/example/issues/3",
                        "node_id": "issue-3",
                        "updated_at": "2026-08-10T00:00:00Z",
                        "labels": [],
                    },
                    {
                        "url": "https://github.com/z-shell/example/issues/2",
                        "node_id": "issue-2",
                        "updated_at": "2026-08-20T00:00:00Z",
                        "labels": [],
                    },
                    {
                        "url": "https://github.com/z-shell/example/issues/1",
                        "node_id": "issue-1",
                        "updated_at": "2026-08-01T00:00:00Z",
                        "labels": ["status:blocked"],
                    },
                ],
            )
            project_items = self.write_ndjson(
                directory,
                "project-items.ndjson",
                [{"node_id": "issue-2"}],
            )

            report = project_reconcile.build_report(
                open_issues,
                project_items,
                now="2026-08-21T00:00:00Z",
                stale_after_days=5,
            )

        self.assertEqual(3, report["open_issue_count"])
        self.assertEqual(1, report["project_content_count"])
        self.assertEqual(
            [
                "https://github.com/z-shell/example/issues/1",
                "https://github.com/z-shell/example/issues/3",
            ],
            [issue["url"] for issue in report["missing_open_issues"]],
        )
        self.assertEqual(
            ["https://github.com/z-shell/example/issues/3"],
            [issue["url"] for issue in report["stale_open_issues"]],
        )

    def test_report_rejects_issue_without_updated_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            open_issues = self.write_ndjson(
                directory,
                "open-issues.ndjson",
                [{"url": "https://github.com/z-shell/example/issues/1", "node_id": "issue-1", "labels": []}],
            )
            project_items = self.write_ndjson(directory, "project-items.ndjson", [])

            with self.assertRaisesRegex(ValueError, "updated_at"):
                project_reconcile.build_report(
                    open_issues,
                    project_items,
                    now="2026-08-21T00:00:00Z",
                    stale_after_days=5,
                )


if __name__ == "__main__":
    unittest.main()
