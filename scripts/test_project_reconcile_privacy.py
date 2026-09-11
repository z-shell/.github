#!/usr/bin/env python3
"""Synthetic end-to-end privacy and mutation-boundary tests."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import project_reconcile
import project_reconcile_live as live


def issue(node_id="public-id", *, private=False, owner="z-shell"):
    return {
        "__typename": "Issue",
        "id": node_id,
        "url": f"https://github.com/{owner}/example/issues/1",
        "title": "metadata-sentinel",
        "state": "OPEN",
        "updatedAt": "2026-08-01T00:00:00Z",
        "author": {"login": "human", "__typename": "User"},
        "labels": {"nodes": [], "pageInfo": {"hasNextPage": False}},
        "repository": {"nameWithOwner": f"{owner}/example", "isPrivate": private},
    }


class FixtureClient:
    def __init__(self, issues=None, items=None):
        self.issues = issues if issues is not None else [issue()]
        self.items = items if items is not None else []
        self.calls = []
        self.nodes = {x["id"]: x for x in self.issues}
        self.nodes.update({x["id"]: x for x in self.items})

    def __call__(self, query, **variables) -> dict[str, Any]:
        self.calls.append((query, variables))
        if query == live.OPEN_ISSUES:
            return {
                "search": {
                    "issueCount": len(self.issues),
                    "nodes": self.issues,
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        if query == live.PROJECT_ITEMS:
            return {
                "organization": {
                    "projectV2": {
                        "id": "project-id",
                        "items": {
                            "totalCount": len(self.items),
                            "nodes": self.items,
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        },
                    }
                }
            }
        raise AssertionError("Unexpected API operation")


class PrivacyTest(unittest.TestCase):
    def test_apply_verifies_public_addition_and_exact_dashboard_removal(self):
        public = issue()
        dashboard = issue("dashboard-id")
        dashboard["title"] = "Dependency Dashboard"
        dashboard["author"] = {"login": "renovate", "__typename": "Bot"}
        stored = {
            "id": "dashboard-item",
            "__typename": "ProjectV2Item",
            "project": {"id": "project-id"},
            "content": dashboard,
        }
        fixture = FixtureClient([public, dashboard], [stored])
        nodes = {"public-id": public, "dashboard-item": stored}
        mutations = []

        def client(query, **variables):
            if query == live.MEMBERSHIP:
                items = [value for value in nodes.values() if "project" in value]
                return {
                    "node": {
                        "__typename": "ProjectV2",
                        "id": "project-id",
                        "items": {
                            "nodes": items,
                            "totalCount": len(items),
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        },
                    }
                }
            if query == live.SOURCE:
                return {"node": nodes.get(variables["id"])}
            if query == live.ADD:
                self.assertEqual(
                    {"project": "project-id", "content": "public-id"}, variables
                )
                mutations.append("add")
                nodes["new-item"] = {
                    "id": "new-item",
                    "project": {"id": "project-id"},
                    "content": public,
                }
                return {"addProjectV2ItemById": {"item": {"id": "new-item"}}}
            if query == live.REMOVE:
                self.assertEqual(
                    {"project": "project-id", "item": "dashboard-item"}, variables
                )
                mutations.append("remove")
                del nodes["dashboard-item"]
                return {"deleteProjectV2Item": {"deletedItemId": "dashboard-item"}}
            return fixture(query, **variables)

        code, summary = self.run_main(client, "--apply")
        self.assertEqual(0, code)
        self.assertEqual(["add", "remove"], mutations)
        self.assertEqual(1, summary["added_item_count"])
        self.assertEqual(1, summary["removed_item_count"])

    def test_removal_rejects_private_rebound_and_changed_dashboard(self):
        dashboard = issue("dashboard-id")
        dashboard["title"] = "Dependency Dashboard"
        dashboard["author"] = {"login": "renovate", "__typename": "Bot"}
        record = live.issue_record(dashboard)
        report = project_reconcile.build_report_from_records(
            [record],
            [dict(record, item_id="dashboard-item")],
            now="2026-09-11T00:00:00Z",
            stale_after_days=5,
        )
        for mode in [
            "private",
            "foreign",
            "unknown",
            "renamed",
            "rebound",
            "other-project",
        ]:
            with self.subTest(mode=mode):
                source = copy.deepcopy(dashboard)
                stored = {
                    "__typename": "ProjectV2Item",
                    "id": "dashboard-item",
                    "project": {"id": "project-id"},
                    "content": source,
                }
                if mode == "private":
                    source["repository"]["isPrivate"] = True
                elif mode == "foreign":
                    source["repository"]["nameWithOwner"] = "elsewhere/example"
                elif mode == "unknown":
                    del source["repository"]["isPrivate"]
                elif mode == "renamed":
                    source["title"] = "Not a dashboard"
                elif mode == "rebound":
                    source["id"] = "different-source"
                else:
                    stored["project"]["id"] = "other-project"

                def client(query, stored=stored, **variables):
                    self.assertEqual(live.MEMBERSHIP, query)
                    return {
                        "node": {
                            "__typename": "ProjectV2",
                            "id": stored["project"]["id"],
                            "items": {
                                "nodes": [stored],
                                "totalCount": 1,
                                "pageInfo": {"hasNextPage": False, "endCursor": None},
                            },
                        }
                    }

                with self.assertRaises(ValueError):
                    live.apply_report(client, "project-id", report, "z-shell")

    def test_collection_paginates_both_connections(self):
        fixture = FixtureClient()
        cursors = []

        def client(query, **variables):
            cursors.append((query, variables.get("cursor")))
            data = fixture(query, **variables)
            second = variables["cursor"] is not None
            content = issue("second" if second else "first")
            if query == live.OPEN_ISSUES:
                page = data["search"]
                page["issueCount"] = 2
                page["nodes"] = [content]
            else:
                page = data["organization"]["projectV2"]["items"]
                page["totalCount"] = 2
                page["nodes"] = [{"id": "item-" + content["id"], "content": content}]
            page["pageInfo"] = {"hasNextPage": not second, "endCursor": "next-page"}
            return data

        code, summary = self.run_main(client)
        self.assertEqual(0, code)
        self.assertEqual(2, summary["open_issue_count"])
        self.assertEqual(2, summary["project_content_count"])
        self.assertEqual(
            [None, "next-page", None, "next-page"], [c for _, c in cursors]
        )

    def test_closed_private_pr_cannot_enter_public_report(self):
        private = dict(issue(private=True), __typename="PullRequest", state="CLOSED")
        code, summary = self.run_main(
            FixtureClient([], [{"id": "private-pr", "content": private}])
        )
        self.assertEqual(0, code)
        self.assertEqual(0, summary["project_content_count"])
        self.assertEqual(1, summary["omitted_project_item_count"])

    def test_ci_missing_project_token_fails_without_using_other_credentials(self):
        client = FixtureClient()
        with patch.dict(os.environ, {"GH_TOKEN": ""}):
            code, summary = self.run_main(client, "--require-token")
        self.assertEqual(1, code)
        self.assertEqual("error", summary["status"])
        self.assertEqual([], client.calls)

    def run_main(self, client, *extra):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "summary.json"
            output.write_text("stale-secret-sentinel")
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = live.main(["--output", str(output), *extra], client=client)
            published = output.read_text() + stdout.getvalue() + stderr.getvalue()
            self.assertNotIn("sentinel", published)
            self.assertNotIn("https://github.com/", published)
            self.assertEqual([output], list(Path(tmp).iterdir()))
            return code, json.loads(output.read_text())

    def test_graphql_renovate_identity_preserves_exact_dashboard_exclusion(self):
        dashboard = issue()
        dashboard["author"] = {"login": "renovate", "__typename": "Bot"}
        dashboard["title"] = "Dependency Dashboard"
        self.assertTrue(
            project_reconcile.is_renovate_dependency_dashboard(
                live.issue_record(dashboard)
            )
        )
        dashboard["author"]["__typename"] = "User"
        self.assertFalse(
            project_reconcile.is_renovate_dependency_dashboard(
                live.issue_record(dashboard)
            )
        )
        dashboard["author"]["__typename"] = "Bot"
        dashboard["title"] = "Renovate configuration warning"
        self.assertFalse(
            project_reconcile.is_renovate_dependency_dashboard(
                live.issue_record(dashboard)
            )
        )

    def test_public_private_foreign_draft_and_redacted_records(self):
        public = issue()
        private = issue("private-id-sentinel", private=True)
        foreign = issue("foreign-id-sentinel", owner="other")
        items = [
            {"id": "item-" + x["id"], "content": x} for x in [public, private, foreign]
        ]
        items += [
            {"id": "draft", "content": {"__typename": "DraftIssue"}},
            {"id": "redacted", "content": None},
        ]
        code, summary = self.run_main(FixtureClient([public, private, foreign], items))
        self.assertEqual(0, code)
        self.assertEqual(1, summary["open_issue_count"])
        self.assertEqual(1, summary["project_content_count"])
        self.assertEqual(2, summary["omitted_open_issue_count"])
        self.assertEqual(4, summary["omitted_project_item_count"])
        self.assertEqual(0, summary["missing_open_issue_count"])

    def test_unknown_visibility_is_not_treated_as_public(self):
        for visibility in [None, "false", 0]:
            with self.subTest(visibility=visibility):
                unknown = issue()
                unknown["repository"]["isPrivate"] = visibility
                code, summary = self.run_main(FixtureClient([unknown]))
                self.assertEqual(1, code)
                self.assertEqual("error", summary["status"])

    def test_api_error_diagnostics_cannot_enter_artifact_or_logs(self):
        def failing_client(*args, **kwargs):
            raise ValueError("api-private-sentinel")

        code, summary = self.run_main(failing_client)
        self.assertEqual(1, code)
        self.assertEqual(
            {"schema": "z-shell/project-reconcile-summary/v1", "status": "error"},
            summary,
        )

    def test_transport_captures_stderr_and_graphql_error_body(self):
        for result in [
            subprocess.CompletedProcess([], 1, "private-sentinel", "token-sentinel"),
            subprocess.CompletedProcess(
                [], 0, '{"errors":[{"message":"private-sentinel"}]}', ""
            ),
        ]:
            with self.subTest(result=result.returncode), patch.object(
                live.subprocess, "run", return_value=result
            ):
                with self.assertRaises(ValueError) as caught:
                    live.github("query Fixture { viewer { login } }")
                self.assertNotIn("sentinel", str(caught.exception))

    def test_incomplete_or_duplicate_inventory_fails_closed(self):
        for mode in ["cap", "count", "duplicate", "cursor"]:
            with self.subTest(mode=mode):
                base = FixtureClient()

                def client(query, base=base, mode=mode, **variables):
                    data = base(query, **variables)
                    if query == live.OPEN_ISSUES:
                        page = data["search"]
                        if mode == "cap":
                            page["issueCount"] = 1001
                        elif mode == "count":
                            page["issueCount"] = 2
                        elif mode == "duplicate":
                            page["nodes"] = [issue(), issue()]
                        else:
                            page["pageInfo"] = {"hasNextPage": True, "endCursor": None}
                    return data

                code, summary = self.run_main(client)
                self.assertEqual(1, code)
                self.assertEqual("error", summary["status"])

    def test_apply_rechecks_visibility_before_any_mutation(self):
        self.assertTrue(
            hasattr(live, "apply_report"), "Apply must have a fresh privacy gate"
        )
        record = live.issue_record(issue())
        report = project_reconcile.build_report_from_records(
            [record],
            [],
            now="2026-09-11T00:00:00Z",
            stale_after_days=5,
        )
        calls = []

        def changed_source(query, **variables):
            calls.append(query)
            if query.startswith("mutation"):
                self.fail("A private source must never be mutated")
            return {"node": issue(private=True)}

        with self.assertRaises(ValueError):
            live.apply_report(changed_source, "project-id", report, "z-shell")
        self.assertEqual(1, len(calls))


if __name__ == "__main__":
    unittest.main()
