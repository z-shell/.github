#!/usr/bin/env python3
"""Check repository file dispositions and render domain resource references."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

spec = importlib.util.spec_from_file_location("knowledge_delivery", Path(__file__).with_name("knowledge-delivery.py"))
delivery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)
MANIFEST = "knowledge/repository-files.json"
DOMAINS = {"agents", "ci", "documentation", "governance", "modules", "plugins", "quality", "tooling", "zi", "zsh"}


def repository_files(root):
    if (root / ".git").exists():
        result = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"], check=True, capture_output=True)
        names = result.stdout.decode().split("\0")
    else:
        names = [str(path.relative_to(root)) for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"]
    return {name for name in names if name and not name.startswith("knowledge/") and (root / name).is_file()}


def load_records(root):
    value = json.loads(delivery.local_path(root, MANIFEST).read_text(encoding="utf-8"), object_pairs_hook=delivery.unique_object)
    if set(value) != {"version", "files"} or type(value["version"]) is not int or value["version"] != 1 or not isinstance(value["files"], list):
        raise ValueError("unsupported repository knowledge inventory")
    records = value["files"]
    seen = set()
    imports = {entry["target"]: entry["source"] for entry in delivery.load_entries(root)}
    for record in records:
        if not isinstance(record, dict) or set(record) != {"path", "domain", "disposition", "knowledge", "reason"}:
            raise ValueError("each file needs path, domain, disposition, knowledge and reason")
        if not all(isinstance(item, str) and item for item in record.values()):
            raise ValueError("file disposition values must be nonempty strings")
        path, domain, disposition = record["path"], record["domain"], record["disposition"]
        if path.startswith(("scripts/", "lib/", "templates/readme/")):
            raise ValueError(f"retired allocation directory: {path}; use automation or domain knowledge")
        if path.startswith("automation/") and path.split("/")[1] not in {"agents", "knowledge", "governance", "ci"}:
            raise ValueError(f"undeclared automation domain: {path}")
        if path.startswith("knowledge/") or path in seen or domain not in DOMAINS or disposition not in {"imported", "referenced", "deletion-decision"}:
            raise ValueError(f"invalid or duplicate file disposition: {path}")
        seen.add(path)
        if not delivery.local_path(root, path).is_file():
            raise ValueError(f"missing inventoried file: {path}")
        knowledge = record["knowledge"]
        if not knowledge.startswith(f"knowledge/domains/{domain}/") or not knowledge.endswith(".md"):
            raise ValueError(f"knowledge reference is outside its domain: {path}")
        if disposition == "imported":
            if imports.get(path) != knowledge or not delivery.local_path(root, knowledge).is_file():
                raise ValueError(f"imported file has no matching delivery owner: {path}")
        elif knowledge != f"knowledge/domains/{domain}/repository-resources.md":
            raise ValueError(f"referenced file needs its domain resource page: {path}")
    actual = repository_files(root)
    if seen != actual:
        raise ValueError(f"file coverage drift; unclassified={sorted(actual - seen)}, missing={sorted(seen - actual)}")
    if not set(imports).issubset(seen):
        raise ValueError("delivery consumers are missing from the file inventory")
    return sorted(records, key=lambda item: item["path"])


def resource_pages(root, records):
    for domain in sorted({item["domain"] for item in records}):
        target = root / f"knowledge/domains/{domain}/repository-resources.md"
        rows = [f"# {domain.capitalize()} repository resources", "", "<!-- GENERATED from knowledge/repository-files.json. Regenerate: python3 automation/knowledge/knowledge-coverage.py --write -->", "", "Select a file for the task described below. Imported files have an editable knowledge owner and a complete native delivery. Referenced files retain their current owner because they are executable contracts, historical records, native capability packages, configuration or supporting assets. This inventory establishes coverage, not semantic accuracy or runtime discovery.", "", "| File | Disposition | Purpose and reading context |", "| --- | --- | --- |"]
        for item in records:
            if item["domain"] != domain:
                continue
            relative = os.path.relpath(root / item["path"], target.parent).replace(os.sep, "/")
            disposition = item["disposition"]
            if disposition == "imported":
                owner = os.path.relpath(root / item["knowledge"], target.parent).replace(os.sep, "/")
                disposition = f"[Imported source]({owner})"
            rows.append(f"| [{item['path']}]({relative}) | {disposition} | {item['reason'].replace('|', '&#124;')} |")
        yield target, "\n".join(rows) + "\n"


def run(root, write):
    records = load_records(root)
    stale = []
    for target, expected in resource_pages(root, records):
        delivery.local_path(root, str(target.relative_to(root)))
        if target.is_file() and target.read_text(encoding="utf-8") == expected:
            continue
        stale.append(str(target.relative_to(root)))
        if write:
            target.write_text(expected, encoding="utf-8")
    if stale and not write:
        raise ValueError(f"stale domain resource references: {stale}")
    counts = {kind: sum(item["disposition"] == kind for item in records) for kind in ("imported", "referenced", "deletion-decision")}
    print(f"repository knowledge coverage checked: {len(records)} files, {counts}")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=next(parent for parent in Path(__file__).resolve().parents if (parent / ".github/instruction-surfaces.json").is_file()))
    parser.add_argument("--write", action="store_true", help="regenerate domain references after inventory validation")
    args = parser.parse_args()
    try:
        return run(args.root.resolve(), args.write)
    except (OSError, ValueError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"knowledge coverage failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
