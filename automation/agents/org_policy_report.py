#!/usr/bin/env python3
"""Read-only organization policy coverage and conservative change-impact reports.

No repository, tracker or settings writes. GitHub reads require --live; offline
coverage accepts a saved paginated repository inventory and optional checkout map.
Reports distinguish declarations, local validation and published observations.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import re
import subprocess  # nosec B404 - argument arrays, read-only git and gh commands
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

SPEC = importlib.util.spec_from_file_location(
    "org_routing", Path(__file__).with_name("org-routing.py")
)
assert SPEC and SPEC.loader
routing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(routing)
DELIVERY_SPEC = importlib.util.spec_from_file_location(
    "knowledge_delivery", Path(__file__).parents[1] / "knowledge/knowledge-delivery.py"
)
assert DELIVERY_SPEC and DELIVERY_SPEC.loader
delivery = importlib.util.module_from_spec(DELIVERY_SPEC)
DELIVERY_SPEC.loader.exec_module(delivery)
CALLER = "z-shell/.github/.github/workflows/org-routing.yml@"


class EvidenceError(Exception):
    """An observation was unavailable, never a passing result."""


def command(args: list[str]) -> str:
    result = subprocess.run(  # nosec B603 - fixed executables, separate arguments
        args, capture_output=True, text=True, timeout=60, check=False
    )
    if result.returncode:
        # Avoid echoing authentication diagnostics or arbitrary remote text.
        raise EvidenceError(f"{args[0]} read failed (exit {result.returncode})")
    return result.stdout


def github(endpoint: str, *, paginate: bool = False):
    args = ["gh", "api", "--method", "GET", endpoint]
    if paginate:
        args += ["--paginate", "--slurp"]
    value = json.loads(command(args))
    return [item for page in value for item in page] if paginate else value


def inventory_rows(value) -> list[dict]:
    if not isinstance(value, list):
        raise ValueError("inventory must be a repository list or slurped page list")
    rows = (
        [item for page in value for item in page]
        if value and isinstance(value[0], list)
        else value
    )
    seen = set()
    for row in rows:
        name = row.get("full_name") if isinstance(row, dict) else None
        if not isinstance(name, str) or not routing.REPOSITORY_PATTERN.fullmatch(name):
            raise ValueError("inventory contains an invalid organization repository")
        if name in seen:
            raise ValueError(f"duplicate inventory repository: {name}")
        for field in ("archived", "private", "fork"):
            if not isinstance(row.get(field), bool):
                raise ValueError(f"{name}: inventory requires boolean {field}")
        seen.add(name)
    return sorted(rows, key=lambda row: row["full_name"].lower())


def revision(root: Path) -> str | None:
    try:
        return command(["git", "-C", str(root), "rev-parse", "HEAD"]).strip()
    except (EvidenceError, OSError, subprocess.SubprocessError):
        return None


def canonical_inputs(root: Path) -> dict[str, str]:
    """Bind observations to working content even before that content is committed."""
    paths = [routing.MANIFEST_PATH, routing.APPROVED_PATH]
    if (root / delivery.MANIFEST).exists():
        paths.append(delivery.MANIFEST)
    if (root / delivery.PROJECT_MANIFEST).exists():
        paths.append(delivery.PROJECT_MANIFEST)
    return {
        path: hashlib.sha256((root / path).read_bytes()).hexdigest()
        for path in paths
    }


def callers(texts: dict[str, str]) -> list[dict]:
    result = []
    for path, text in sorted(texts.items()):
        # These are reference observations, not YAML or trigger validation.
        for line in text.splitlines():
            match = re.match(
                r"\s*uses:\s*['\"]?" + re.escape(CALLER) + r"([^\s'\"#]+)", line
            )
            if match:
                ref = match[1]
                result.append(
                    {
                        "path": path,
                        "ref": ref,
                        "immutable": bool(routing.SHA_PATTERN.fullmatch(ref)),
                    }
                )
    return result


def published(name: str, entry: dict, org, api=github) -> dict:
    """Observe immutable default-branch content; keep runtime and semantics unknown."""
    metadata = api(f"repos/{name}")
    branch = metadata["default_branch"]
    sha = api(f"repos/{name}/commits/{quote(branch, safe='')}")["sha"]
    if not routing.SHA_PATTERN.fullmatch(sha):
        raise EvidenceError("invalid published commit")
    tree = api(f"repos/{name}/git/trees/{sha}?recursive=1")
    if tree.get("truncated"):
        raise EvidenceError("published tree is truncated")
    paths = {item["path"]: item for item in tree["tree"]}

    def read(path: str) -> str | None:
        item = paths.get(path)
        if item is None:
            return None
        if item.get("type") != "blob" or item.get("mode") not in ("100644", "100755"):
            raise EvidenceError(f"non-regular published file: {path}")
        if item.get("size", 0) > 1024 * 1024:
            raise EvidenceError(f"published file exceeds observation limit: {path}")
        value = api(f"repos/{name}/git/blobs/{item['sha']}")
        return base64.b64decode(value["content"]).decode("utf-8")

    agents = read("AGENTS.md")
    expected = routing.render(entry, org)
    routing_state = "missing"
    if agents is not None:
        try:
            routing_state = (
                "current"
                if routing.splice(agents, expected, name) == agents
                else "drift"
            )
        except routing.RoutingError:
            routing_state = "invalid"
    workflows = {}
    for path in paths:
        if path.startswith(".github/workflows/") and path.endswith((".yml", ".yaml")):
            workflows[path] = read(path) or ""
    skills = {}
    for skill in sorted(set(entry.get("vendored_skills", [])) | {"code-review"}):
        directory = f".github/skills/{skill}"
        text = read(f"{directory}/SKILL.md")
        record = org.approved["skills"].get(skill)
        state = {
            "presence": "present" if text else "missing",
            "suitability": "unassessed",
            "invocation": "unverified",
        }
        if text and record:
            try:
                _, metadata, _ = routing.parse_skill(text)
                state["revision"] = metadata.get("github-pinned")
                state["provenance"] = (
                    "current"
                    if metadata.get("github-repo")
                    == routing.source_url(routing.skill_source(record))
                    and metadata.get("github-path") == record["path"]
                    and metadata.get("github-ref", state["revision"])
                    == state["revision"]
                    else "invalid"
                )
                state["currency"] = (
                    "current" if state["revision"] == record["revision"] else "stale"
                )
                state["content"] = (
                    "current"
                    if routing.skill_digest(text, strict_metadata=True)
                    == record["digest"]
                    else "modified"
                )
                resources = sorted(
                    path[len(directory) + 1 :]
                    for path, item in paths.items()
                    if path.startswith(directory + "/") and item.get("type") != "tree"
                )
                state["resources"] = (
                    "current" if resources == sorted(record["files"]) else "modified"
                )
                # Multi-file approved skills need the full verifier, not a body-only claim.
                if record["files"] != ["SKILL.md"]:
                    state["content"] = "unverified"
            except ValueError:
                state["content"] = "invalid"
        skills[skill] = state
    result = {
        "branch": branch,
        "revision": sha,
        "routing_block": routing_state,
        "caller_references": callers(workflows),
        "skills": skills,
        "runtime_discovery": "unverified",
        "full_routing_check": "unverified",
    }
    # Branch rules are separate evidence. Failure here must not erase file evidence.
    try:
        rules = api(
            f"repos/{name}/rules/branches/{quote(branch, safe='')}?per_page=100",
            paginate=True,
        )
        result["ruleset_required_checks"] = sorted(
            {
                check["context"]
                for rule in rules
                if rule.get("type") == "required_status_checks"
                for check in rule["parameters"]["required_status_checks"]
            }
        )
    except (EvidenceError, ValueError, KeyError, OSError, subprocess.SubprocessError):
        result["ruleset_required_checks"] = "unverified"
    return result


def coverage(
    org_root: Path,
    inventory,
    checkouts: dict | None = None,
    *,
    live: bool = False,
    api=github,
) -> dict:
    org = routing.load_org(org_root)
    entries = {entry["repository"]: entry for entry in org.downstream}
    rows = inventory_rows(inventory)
    present = {row["full_name"] for row in rows}
    results = []
    for row in rows:
        name = row["full_name"]
        classification = (
            "excluded-archived"
            if row["archived"]
            else (
                "canonical-owner"
                if name == routing.CANONICAL_REPOSITORY
                else (
                    "declared"
                    if name in entries
                    else "unassessed-fork" if row["fork"] else "unassessed"
                )
            )
        )
        result = {
            "repository": name,
            "private": row["private"],
            "classification": classification,
        }
        if classification == "declared":
            result["published"] = {"status": "unverified"}
            if live:
                try:
                    result["published"] = published(name, entries[name], org, api)
                except (
                    EvidenceError,
                    ValueError,
                    KeyError,
                    OSError,
                    subprocess.SubprocessError,
                ) as exc:
                    result["published"] = {"status": "unavailable", "reason": str(exc)}
            root = (checkouts or {}).get(name)
            result["local"] = {"status": "unassessed"}
            if root:
                root = Path(root)
                try:
                    errors = routing.check(root, name, org)
                    result["local"] = {
                        "status": "failed" if errors else "passed",
                        "revision": revision(root),
                        "findings": errors,
                    }
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    result["local"] = {"status": "unavailable", "reason": str(exc)}
        results.append(result)
    for name in sorted(entries.keys() - present):
        results.append(
            {
                "repository": name,
                "classification": "inventory-missing",
                "published": {"status": "unavailable"},
            }
        )
    return {
        "version": 1,
        "kind": "coverage",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "canonical_revision": revision(org_root),
        "canonical_inputs": canonical_inputs(org_root),
        "inventory_source": "live-github" if live else "supplied-snapshot",
        "inventory_count": len(rows),
        "declared_count": len(entries),
        "results": results,
        "limits": [
            "Only declared active consumers receive file observations.",
            "Ruleset checks cover the observed default branch; classic branch protection, integration branches and bypass rules require separate checks.",
            "Caller references do not prove trigger eligibility, passing CI, runtime discovery or semantic suitability.",
            "Snapshot completeness and age require caller evidence; inaccessible repositories may not appear in the API inventory.",
            "Private repository results must remain private.",
        ],
    }


def impact(org_root: Path, changed: list[str]) -> dict:
    org = routing.load_org(org_root)
    manifest = routing.load_json(org_root / routing.MANIFEST_PATH)
    declared_paths = {surface["path"] for surface in manifest["surfaces"]}
    targets = {
        entry["source"]: entry["target"]
        for entry in delivery.load_entries(org_root)
    } if (org_root / delivery.MANIFEST).exists() else {}
    rows = []
    for path in sorted(set(changed)):
        if not routing._safe_relative(path):
            raise ValueError("changed paths must be safe repository-relative paths")
        consumer = targets.get(path, path)
        skill = next(
            (
                name
                for name, record in org.approved["skills"].items()
                if routing.skill_source(record) == routing.CANONICAL_REPOSITORY
                and (
                    consumer == record["path"]
                    or consumer.startswith(record["path"] + "/")
                )
            ),
            None,
        )
        shared = (
            consumer in declared_paths
            or consumer
            in (routing.MANIFEST_PATH, routing.APPROVED_PATH, "automation/agents/org-routing.py")
            or consumer.startswith(("runbooks/", "decisions/", ".github/instructions/"))
        )
        project_consumers = {
            record["repository"] for record in org.project_entries
            if record["source"] == path
        }
        candidates = (
            org.downstream
            if shared and skill is None
            else (
                [
                    entry
                    for entry in org.downstream
                    if skill in entry.get("vendored_skills", [])
                ]
                if skill
                else [
                    entry for entry in org.downstream
                    if entry["repository"] in project_consumers
                ]
            )
        )
        rows.append(
            {
                "path": path,
                "relationship": (
                    "vendors-approved-skill"
                    if skill
                    else (
                        "shared-policy-review"
                        if shared
                        else (
                            "delivers-approved-project-knowledge"
                            if project_consumers
                            else "caller-inventory-required"
                            if consumer.startswith(
                                (
                                    ".github/workflows/",
                                    "actions/",
                                    "templates/",
                                    "knowledge/domains/documentation/templates/",
                                    "workflow-templates/",
                                )
                            )
                            else "unmapped-review-required"
                        )
                    )
                ),
                "candidate_repositories": sorted(
                    entry["repository"] for entry in candidates
                ),
            }
        )
    return {
        "version": 1,
        "kind": "impact",
        "canonical_revision": revision(org_root),
        "canonical_inputs": canonical_inputs(org_root),
        "changes": rows,
        "limits": [
            "Conservative review candidates, not proof that every consumer requires an edit.",
            "Uses declared relationships, not inferred prose references; removals and renamed surfaces need manual impact review.",
            "Runtime delivery and private workspace consumers require separate checks.",
            "A skill source edit does not advance its approved revision or authorize downstream writes.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--org-root", type=Path, default=next(parent for parent in Path(__file__).resolve().parents if (parent / ".github/instruction-surfaces.json").is_file())
    )
    commands = parser.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("coverage")
    source = audit.add_mutually_exclusive_group(required=True)
    source.add_argument("--live", action="store_true")
    source.add_argument("--inventory", type=Path)
    audit.add_argument(
        "--checkouts",
        type=Path,
        help="JSON mapping repository names to local checkout paths",
    )
    changes = commands.add_parser("impact")
    changes.add_argument("--changed", action="append", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "impact":
            result = impact(args.org_root, args.changed)
        else:
            inventory = (
                github("orgs/z-shell/repos?per_page=100", paginate=True)
                if args.live
                else routing.load_json(args.inventory)
            )
            checkouts = routing.load_json(args.checkouts) if args.checkouts else {}
            if not isinstance(checkouts, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in checkouts.items()
            ):
                raise ValueError("checkouts must map repository names to paths")
            result = coverage(args.org_root, inventory, checkouts, live=args.live)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0  # Successful report production, never a compliance verdict.
    except (
        EvidenceError,
        routing.RoutingError,
        OSError,
        ValueError,
        KeyError,
        subprocess.SubprocessError,
    ) as exc:
        print(json.dumps({"error": str(exc), "status": "unavailable"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
