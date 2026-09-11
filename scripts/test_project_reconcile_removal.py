#!/usr/bin/env python3
"""Exercise removal through the real transport with synthetic GitHub responses."""

import json
import subprocess
import unittest
from unittest.mock import patch

import project_reconcile_live as live
from test_project_reconcile_privacy import issue


class RemovalTransportTest(unittest.TestCase):
    def probe(self, mode):
        dashboard = issue("dashboard-id")
        dashboard["title"] = "Dependency Dashboard"
        dashboard["author"] = {"login": "renovate", "__typename": "Bot"}
        stored = {
            "id": "dashboard-item",
            "__typename": "ProjectV2Item",
            "project": {"id": "project-id"},
            "content": dashboard,
        }
        removed = []
        cursors = []

        def transport(args, **kwargs):
            request = json.loads(kwargs["input"])
            query, variables = request["query"], request["variables"]
            missing = bool(removed) or mode == "already-absent"
            error = {"type": "NOT_FOUND", "path": ["node"], "message": "sentinel"}
            if query == live.SOURCE:
                if missing:
                    return subprocess.CompletedProcess(
                        args,
                        1,
                        json.dumps({"data": {"node": None}, "errors": [error]}),
                        "sentinel",
                    )
                data = {"node": stored}
            elif query == live.REMOVE:
                removed.append(variables["item"])
                data = {"deleteProjectV2Item": {"deletedItemId": "dashboard-item"}}
            elif query.startswith("query Membership("):
                cursor = variables["cursor"]
                cursors.append(cursor)
                if mode == "access-denied":
                    return subprocess.CompletedProcess(
                        args, 1, json.dumps({"errors": [error]}), "sentinel"
                    )
                second = cursor is not None
                nodes = [] if missing else [stored]
                if mode == "still-present":
                    nodes = [stored]
                # The target, when present, is always on the second page.
                page_nodes = (
                    nodes if second else [{"id": "other-item", "content": None}]
                )
                data = {
                    "node": {
                        "__typename": "ProjectV2",
                        "id": "project-id",
                        "items": {
                            "nodes": page_nodes,
                            "totalCount": 1
                            + len(nodes)
                            + (1 if mode == "incomplete" else 0),
                            "pageInfo": {
                                "hasNextPage": not second or mode == "loop",
                                "endCursor": "next",
                            },
                        },
                    }
                }
            else:
                raise AssertionError("Unexpected operation")
            return subprocess.CompletedProcess(args, 0, json.dumps({"data": data}), "")

        report = {
            "missing_open_issues": [],
            "excluded_project_items": [
                {"item_id": "dashboard-item", "node_id": "dashboard-id"}
            ],
        }
        with patch.object(live.subprocess, "run", side_effect=transport):
            result = live.apply_report(live.github, "project-id", report, "z-shell")
        return result, removed, cursors

    def test_deleted_node_not_found_does_not_abort_success(self):
        result, removed, cursors = self.probe("deleted")
        self.assertEqual(1, result["removed_item_count"])
        self.assertEqual(["dashboard-item"], removed)
        self.assertEqual([None, "next", None, "next"], cursors)

    def test_already_absent_item_is_skipped_after_complete_membership_read(self):
        result, removed, cursors = self.probe("already-absent")
        self.assertEqual(0, result["removed_item_count"])
        self.assertEqual([], removed)
        self.assertEqual([None, "next"], cursors)

    def test_unproven_absence_fails_closed(self):
        for mode in ("access-denied", "incomplete", "loop", "still-present"):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.probe(mode)


if __name__ == "__main__":
    unittest.main()
