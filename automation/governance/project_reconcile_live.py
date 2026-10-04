#!/usr/bin/env python3
"""Reconcile public organization issues without exporting source metadata."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from project_reconcile import (
    build_report_from_records,
    is_renovate_dependency_dashboard,
    public_summary,
)

ISSUE_FIELDS = """
  id url title state updatedAt
  author { login __typename }
  labels(first: 100) { nodes { name } pageInfo { hasNextPage } }
  repository { nameWithOwner isPrivate }
"""
OPEN_ISSUES = """
query OpenIssues($search: String!, $cursor: String) {
  search(type: ISSUE, query: $search, first: 100, after: $cursor) {
    issueCount pageInfo { hasNextPage endCursor }
    nodes { __typename ... on Issue { %s } }
  }
}
""" % ISSUE_FIELDS
PROJECT_ITEMS = """
query ProjectItems($org: String!, $number: Int!, $cursor: String) {
  organization(login: $org) {
    projectV2(number: $number) {
      id
      items(first: 100, after: $cursor) {
        totalCount pageInfo { hasNextPage endCursor }
        nodes {
          id
          content {
            __typename
            ... on Issue { id url title repository { nameWithOwner isPrivate } }
            ... on PullRequest { id url title repository { nameWithOwner isPrivate } }
          }
        }
      }
    }
  }
}
"""
Client = Callable[..., dict[str, Any]]
MEMBERSHIP = """query Membership($project: ID!, $cursor: String) {
  node(id: $project) {
    __typename
    ... on ProjectV2 {
      id
      items(first: 100, after: $cursor) {
        totalCount pageInfo { hasNextPage endCursor }
        nodes { id __typename content { __typename ... on Issue { %s } } }
      }
    }
  }
}""" % ISSUE_FIELDS
SOURCE = """query Source($id: ID!) {
  node(id: $id) {
    __typename
    ... on Issue { %s }
    ... on ProjectV2Item {
      id project { id }
      content { __typename ... on Issue { %s } }
    }
  }
}""" % (ISSUE_FIELDS, ISSUE_FIELDS)
ADD = """mutation Add($project: ID!, $content: ID!) {
  addProjectV2ItemById(input: {projectId: $project, contentId: $content}) { item { id } }
}"""
REMOVE = """mutation Remove($project: ID!, $item: ID!) {
  deleteProjectV2Item(input: {projectId: $project, itemId: $item}) { deletedItemId }
}"""


def github(query: str, **variables: Any) -> dict[str, Any]:
    """Capture responses and diagnostics; never echo API errors or source data."""
    result = subprocess.run(
        ["gh", "api", "--hostname", "github.com", "graphql", "--input", "-"],
        input=json.dumps({"query": query, "variables": variables}),
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if result.returncode:
        raise ValueError("GitHub request failed")
    response = json.loads(result.stdout)
    if response.get("errors") or not isinstance(response.get("data"), dict):
        raise ValueError("GitHub response failed validation")
    return response["data"]


def public_source(content: dict[str, Any], organization: str) -> bool:
    """Unknown visibility fails closed; a foreign owner is never in scope."""
    repository = content.get("repository")
    if (
        not isinstance(repository, dict)
        or type(repository.get("isPrivate")) is not bool
    ):
        raise ValueError("Source visibility is unavailable")
    name = repository.get("nameWithOwner")
    if not isinstance(name, str) or name.count("/") != 1:
        raise ValueError("Source ownership is unavailable")
    return (
        not repository["isPrivate"]
        and name.split("/")[0].lower() == organization.lower()
    )


def issue_record(content: dict[str, Any]) -> dict[str, Any]:
    if content["labels"]["pageInfo"]["hasNextPage"]:
        raise ValueError("Issue labels are incomplete")
    author = content.get("author") or {}
    login = author.get("login")
    # GraphQL uses renovate; the existing exact-match policy uses REST's bot login.
    if author.get("__typename") == "Bot" and login == "renovate":
        login = "renovate[bot]"
    return {
        "node_id": content["id"],
        "url": content["url"],
        "title": content["title"],
        "updated_at": content["updatedAt"],
        "author": login,
        "author_type": author.get("__typename"),
        "labels": [label["name"] for label in content["labels"]["nodes"]],
    }


def next_cursor(connection: dict[str, Any], seen: set[str]) -> str | None:
    page = connection["pageInfo"]
    if not page["hasNextPage"]:
        return None
    cursor = page["endCursor"]
    if not isinstance(cursor, str) or not cursor or cursor in seen:
        raise ValueError("Pagination did not advance")
    seen.add(cursor)
    return cursor


def collect(
    client: Client, organization: str, number: int
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    issues, items = [], []
    omitted = {"omitted_open_issue_count": 0, "omitted_project_item_count": 0}
    cursor, seen, ids = None, set(), set()
    while True:
        page = client(
            OPEN_ISSUES,
            search=f"org:{organization} is:issue is:open",
            cursor=cursor,
        )["search"]
        if page["issueCount"] > 1000:
            raise ValueError("Search exceeds GitHub completeness limit")
        for content in page["nodes"]:
            if not content or content.get("__typename") != "Issue":
                raise ValueError("Unexpected search result")
            if content["id"] in ids:
                raise ValueError("Duplicate search result")
            ids.add(content["id"])
            if public_source(content, organization):
                if content["state"] != "OPEN":
                    raise ValueError("Source state changed")
                issues.append(issue_record(content))
            else:
                omitted["omitted_open_issue_count"] += 1
        cursor = next_cursor(page, seen)
        if cursor is None:
            if len(ids) != page["issueCount"]:
                raise ValueError("Search inventory is incomplete")
            break

    cursor, seen, ids = None, set(), set()
    while True:
        project = client(PROJECT_ITEMS, org=organization, number=number, cursor=cursor)[
            "organization"
        ]["projectV2"]
        page = project["items"]
        for item in page["nodes"]:
            if item["id"] in ids:
                raise ValueError("Duplicate Project item")
            ids.add(item["id"])
            content = item.get("content")
            if not content or content.get("__typename") not in ("Issue", "PullRequest"):
                omitted["omitted_project_item_count"] += 1
                continue
            if not public_source(content, organization):
                omitted["omitted_project_item_count"] += 1
                continue
            items.append(
                {
                    "item_id": item["id"],
                    "node_id": content["id"],
                    "url": content["url"],
                    "title": content["title"],
                }
            )
        cursor = next_cursor(page, seen)
        if cursor is None:
            if len(ids) != page["totalCount"]:
                raise ValueError("Project inventory is incomplete")
            return project["id"], issues, items, omitted


def membership_item(
    client: Client, project: str, item_id: str
) -> dict[str, Any] | None:
    """Prove membership or absence through a complete, successful Project read."""
    cursor, seen, ids = None, set(), set()
    found = None
    expected = None
    while True:
        node = client(MEMBERSHIP, project=project, cursor=cursor)["node"]
        if (
            not node
            or node.get("__typename") != "ProjectV2"
            or node.get("id") != project
        ):
            raise ValueError("Project access verification failed")
        page = node["items"]
        if expected is None:
            expected = page["totalCount"]
        if type(expected) is not int or expected < 0 or page["totalCount"] != expected:
            raise ValueError("Project inventory changed")
        for item in page["nodes"]:
            if item["id"] in ids:
                raise ValueError("Duplicate Project item")
            ids.add(item["id"])
            if item["id"] == item_id:
                found = dict(item, project={"id": project})
        cursor = next_cursor(page, seen)
        if cursor is None:
            if len(ids) != expected:
                raise ValueError("Project inventory is incomplete")
            return found


def apply_report(
    client: Client,
    project: str,
    report: dict[str, Any],
    organization: str,
) -> dict[str, int]:
    """Recheck source access boundaries and verify each approved membership write."""
    counts = {"added_item_count": 0, "removed_item_count": 0}
    for issue in report["missing_open_issues"]:
        source = client(SOURCE, id=issue["node_id"])["node"]
        if (
            not source
            or source.get("__typename") != "Issue"
            or source.get("id") != issue["node_id"]
            or not public_source(source, organization)
            or source["state"] != "OPEN"
            or is_renovate_dependency_dashboard(issue_record(source))
        ):
            raise ValueError("Addition eligibility changed")
        result = client(ADD, project=project, content=source["id"])
        item_id = result["addProjectV2ItemById"]["item"]["id"]
        stored = client(SOURCE, id=item_id)["node"]
        if (
            not stored
            or stored["project"]["id"] != project
            or stored["content"]["id"] != source["id"]
            or not public_source(stored["content"], organization)
        ):
            raise ValueError("Addition verification failed")
        counts["added_item_count"] += 1
    for item in report["excluded_project_items"]:
        stored = membership_item(client, project, item["item_id"])
        if stored is None:
            continue
        source = stored.get("content")
        if (
            stored.get("__typename") != "ProjectV2Item"
            or stored["project"]["id"] != project
            or not source
            or source.get("__typename") != "Issue"
            or source.get("id") != item["node_id"]
            or not public_source(source, organization)
            or source["state"] != "OPEN"
            or not is_renovate_dependency_dashboard(issue_record(source))
        ):
            raise ValueError("Removal eligibility changed")
        result = client(REMOVE, project=project, item=item["item_id"])
        if result["deleteProjectV2Item"]["deletedItemId"] != item["item_id"]:
            raise ValueError("Removal response failed validation")
        if membership_item(client, project, item["item_id"]) is not None:
            raise ValueError("Removal verification failed")
        counts["removed_item_count"] += 1
    return counts


def main(argv: list[str] | None = None, *, client: Client = github) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organization", default="z-shell")
    parser.add_argument("--project-number", type=int, default=28)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--require-token", action="store_true")
    arguments = parser.parse_args(argv)
    failure = {"schema": "z-shell/project-reconcile-summary/v1", "status": "error"}
    try:
        # Overwrite stale output before touching privileged inputs. Only this file is uploaded.
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(json.dumps(failure) + "\n")
        if arguments.require_token and not os.environ.get("GH_TOKEN"):
            raise ValueError("Project credential is unavailable")
        if (
            not re.fullmatch(r"[A-Za-z0-9-]+", arguments.organization)
            or arguments.project_number < 1
        ):
            raise ValueError("Invalid scope")
        project, issues, items, omitted = collect(
            client, arguments.organization, arguments.project_number
        )
        report = build_report_from_records(
            issues,
            items,
            now=datetime.now(UTC).isoformat(),
            stale_after_days=5,
        )
        summary = public_summary(report) | omitted | {"status": "ok"}
        if arguments.apply:
            summary |= apply_report(client, project, report, arguments.organization)
        arguments.output.write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary))
        return 0
    except Exception:
        # Even decoding, validation and transport exceptions can contain private values.
        print(
            "Project reconciliation failed; source diagnostics withheld.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
