#!/usr/bin/env python3
"""Build a deterministic GitHub Project reconciliation report from NDJSON."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def parse_timestamp(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO 8601 timestamp")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO 8601 timestamp") from error


def read_ndjson(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{line_number}: invalid JSON") from error
        if not isinstance(record, dict):
            raise ValueError(f"{path}:{line_number}: record must be an object")
        records.append(record)
    return records


def issue_sort_key(issue: dict[str, Any]) -> str:
    url = issue.get("url")
    if not isinstance(url, str):
        raise ValueError("issue url must be a string")
    return url


def is_renovate_dependency_dashboard(issue: dict[str, Any]) -> bool:
    """Return whether an issue is Renovate's repository dashboard."""
    return (
        issue.get("author_type") == "Bot"
        and issue.get("author") == "renovate[bot]"
        and issue.get("title") == "Dependency Dashboard"
    )


def build_report(
    open_issues_path: Path,
    project_items_path: Path,
    *,
    now: str,
    stale_after_days: int,
) -> dict[str, Any]:
    return build_report_from_records(
        read_ndjson(open_issues_path),
        read_ndjson(project_items_path),
        now=now,
        stale_after_days=stale_after_days,
    )


def build_report_from_records(
    open_issues: list[dict[str, Any]],
    project_items: list[dict[str, Any]],
    *,
    now: str,
    stale_after_days: int,
) -> dict[str, Any]:
    """Keep detailed reconciliation records in memory for authorized operations."""
    if stale_after_days < 1:
        raise ValueError("stale_after_days must be at least one")

    project_items_by_node_id: dict[str, list[dict[str, Any]]] = {}
    for item in project_items:
        node_id = item.get("node_id")
        if isinstance(node_id, str):
            project_items_by_node_id.setdefault(node_id, []).append(item)
    project_node_ids = set(project_items_by_node_id)
    cutoff = parse_timestamp(now, field="now") - timedelta(days=stale_after_days)

    excluded_open_issues: list[dict[str, Any]] = []
    excluded_project_items: list[dict[str, Any]] = []
    missing_open_issues: list[dict[str, Any]] = []
    stale_open_issues: list[dict[str, Any]] = []
    for issue in open_issues:
        node_id = issue.get("node_id")
        if not isinstance(node_id, str):
            raise ValueError("issue node_id must be a string")
        updated_at = parse_timestamp(issue.get("updated_at"), field="issue updated_at")
        labels = issue.get("labels")
        if not isinstance(labels, list) or not all(
            isinstance(label, str) for label in labels
        ):
            raise ValueError("issue labels must be a list of strings")
        issue_sort_key(issue)
        if is_renovate_dependency_dashboard(issue):
            excluded_open_issues.append(issue)
            excluded_project_items.extend(project_items_by_node_id.get(node_id, []))
            continue
        if node_id not in project_node_ids:
            missing_open_issues.append(issue)
        if updated_at < cutoff and "status:blocked" not in labels:
            stale_open_issues.append(issue)

    excluded_open_issues.sort(key=issue_sort_key)
    excluded_project_items.sort(key=issue_sort_key)
    missing_open_issues.sort(key=issue_sort_key)
    stale_open_issues.sort(key=issue_sort_key)
    return {
        "schema": "z-shell/project-reconcile-report/v3",
        "open_issue_count": len(open_issues),
        "tracked_open_issue_count": len(open_issues) - len(excluded_open_issues),
        "project_content_count": len(project_items),
        "excluded_open_issues": excluded_open_issues,
        "excluded_project_items": excluded_project_items,
        "missing_open_issues": missing_open_issues,
        "stale_open_issues": stale_open_issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open-issues", type=Path, required=True)
    parser.add_argument("--project-items", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--now", default=datetime.now(UTC).isoformat())
    parser.add_argument("--stale-after-days", type=int, default=5)
    arguments = parser.parse_args()

    try:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(
            json.dumps(
                {
                    "schema": "z-shell/project-reconcile-summary/v1",
                    "status": "error",
                }
            )
            + "\n"
        )
        report = build_report(
            arguments.open_issues,
            arguments.project_items,
            now=arguments.now,
            stale_after_days=arguments.stale_after_days,
        )
        summary = json.dumps(public_summary(report) | {"status": "ok"}, indent=2)
        arguments.output.write_text(summary + "\n")
        print(summary)
        return 0
    except Exception:
        print(
            "Project reconciliation failed; source diagnostics withheld.",
            file=sys.stderr,
        )
        return 1


def public_summary(report: dict[str, Any]) -> dict[str, Any]:
    """Publish only fixed keys and integer counts, never source metadata."""
    return {
        "schema": "z-shell/project-reconcile-summary/v1",
        "open_issue_count": int(report["open_issue_count"]),
        "tracked_open_issue_count": int(report["tracked_open_issue_count"]),
        "project_content_count": int(report["project_content_count"]),
        "excluded_open_issue_count": len(report["excluded_open_issues"]),
        "excluded_project_item_count": len(report["excluded_project_items"]),
        "missing_open_issue_count": len(report["missing_open_issues"]),
        "stale_open_issue_count": len(report["stale_open_issues"]),
    }


if __name__ == "__main__":
    raise SystemExit(main())
