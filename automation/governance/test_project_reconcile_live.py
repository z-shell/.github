#!/usr/bin/env python3
"""Privacy regressions use synthetic records, never real restricted metadata."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path


class LiveReconcileTest(unittest.TestCase):
    def test_live_export_does_not_persist_restricted_inputs(self) -> None:
        script = Path(__file__).with_name("project_reconcile_live.py")
        self.assertTrue(script.exists(), "A privacy-safe live collector is required")
        spec = importlib.util.spec_from_file_location("project_reconcile_live", script)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        calls = []

        def client(query, **variables):
            calls.append(query)
            repository = {"nameWithOwner": "z-shell/example", "isPrivate": False}
            issue = {
                "__typename": "Issue",
                "id": "public-id",
                "url": "https://github.com/z-shell/example/issues/1",
                "title": "Public work",
                "state": "OPEN",
                "updatedAt": "2026-08-01T00:00:00Z",
                "author": {"login": "human", "__typename": "User"},
                "labels": {"nodes": [], "pageInfo": {"hasNextPage": False}},
                "repository": repository,
            }
            if "query OpenIssues" in query:
                return {
                    "search": {
                        "issueCount": 1,
                        "nodes": [issue],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }
            if "query ProjectItems" in query:
                private = dict(
                    issue,
                    id="private-id-sentinel",
                    title="private-title-sentinel",
                    repository={
                        "nameWithOwner": "elsewhere/private-sentinel",
                        "isPrivate": True,
                    },
                )
                return {
                    "organization": {
                        "projectV2": {
                            "id": "project-id",
                            "items": {
                                "totalCount": 2,
                                "nodes": [
                                    {"id": "public-item", "content": issue},
                                    {"id": "private-item-sentinel", "content": private},
                                ],
                                "pageInfo": {"hasNextPage": False, "endCursor": None},
                            },
                        }
                    }
                }
            self.fail("Unexpected API operation")

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "summary.json"
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = module.main(["--output", str(output)], client=client)
            self.assertEqual(0, code)
            published = output.read_text() + stdout.getvalue() + stderr.getvalue()
            self.assertNotIn("sentinel", published)
            self.assertNotIn("https://github.com/", published)
            self.assertEqual([output], list(Path(tmp).iterdir()))
            summary = json.loads(output.read_text())
            self.assertEqual(1, summary["project_content_count"])
            self.assertEqual(1, summary["omitted_project_item_count"])
            self.assertFalse(any("mutation" in q for q in calls))


if __name__ == "__main__":
    unittest.main()
