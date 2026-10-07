#!/usr/bin/env python3
"""Render native knowledge consumers from the central editable domain sources."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
import sys
from urllib.parse import urlsplit

MANIFEST = "knowledge/delivery.json"
PROJECT_MANIFEST = "knowledge/project-delivery.json"
LINK = re.compile(r"(?P<prefix>\]\()(?P<url>[^\s)]+)(?P<suffix>\))")
DEFINITION = re.compile(r"^(?P<prefix> {0,3}\[[^\]]+\]:\s*)(?P<url>\S+)", re.MULTILINE)
SKILL_RESOURCE = re.compile(r"(?P<skill>\.github/skills/[a-z0-9][a-z0-9-]*)/(?!SKILL\.md$)[^/]+(?:/[^/]+)*\.md")
CANONICAL_BLOB = "https://github.com/z-shell/.github/blob/main"


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def local_path(root, name):
    path = PurePosixPath(name)
    if not name or path.is_absolute() or str(path) != name or ".." in path.parts:
        raise ValueError(f"invalid repository-relative path: {name}")
    candidate = root
    for part in path.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError(f"symlink is not a knowledge delivery path: {name}")
    if candidate.exists() and not candidate.is_file():
        raise ValueError(f"knowledge delivery path is not a regular file: {name}")
    return candidate


def _mask_code(text):
    placeholders = []

    def mask(match):
        placeholders.append(match.group(0))
        return f"\x00CODE_{len(placeholders) - 1}\x00"

    masked = re.sub(r"(?s)(```.*?```|~~~.*?~~~|`+[^`\n]+?`+)", mask, text)

    def unmask(content):
        if not placeholders:
            return content
        return re.sub(r"\x00CODE_(\d+)\x00", lambda match: placeholders[int(match.group(1))], content)

    return masked, unmask


def rebase_links(text, origin, destination):
    """Keep relative Markdown link destinations stable across a source move."""
    masked, unmask = _mask_code(text)

    def replace(match):
        raw = match.group("url")
        angled = raw.startswith("<") and raw.endswith(">")
        url = raw[1:-1] if angled else raw
        parts = urlsplit(url)
        if parts.scheme or parts.netloc or not parts.path or parts.path.startswith("/"):
            return match.group(0)
        resolved = os.path.normpath(str(origin.parent / parts.path))
        moved = os.path.relpath(resolved, destination.parent).replace(os.sep, "/")
        if parts.path.startswith("./"):
            moved = "./" + moved
        if parts.path.endswith("/"):
            moved += "/"
        if parts.query:
            moved += "?" + parts.query
        if parts.fragment:
            moved += "#" + parts.fragment
        if angled:
            moved = "<" + moved + ">"
        return match.group("prefix") + moved + match.groupdict().get("suffix", "")

    rebased = DEFINITION.sub(replace, LINK.sub(replace, masked))
    return unmask(rebased)


def load_entries(root):
    manifest = json.loads(local_path(root, MANIFEST).read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    if set(manifest) != {"version", "entries"} or type(manifest["version"]) is not int or manifest["version"] != 1:
        raise ValueError("unsupported knowledge delivery manifest")
    entries = manifest["entries"]
    if not isinstance(entries, list) or not entries:
        raise ValueError("knowledge delivery entries must be a nonempty list")
    targets = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"source", "target"}:
            raise ValueError("each delivery entry needs exactly source and target")
        source, target = entry["source"], entry["target"]
        if not isinstance(source, str) or not isinstance(target, str):
            raise ValueError("delivery paths must be strings")
        if not source.startswith("knowledge/domains/") or not source.endswith(".md"):
            raise ValueError(f"source is outside the domain knowledge store: {source}")
        if target.startswith("knowledge/") or not target.endswith(".md"):
            raise ValueError(f"target must be a Markdown consumer outside knowledge/: {target}")
        # A source may feed several consumers, such as a scoped instruction and
        # the reference bundled with a skill; each consumer has one source.
        if target in targets:
            raise ValueError(f"duplicate knowledge target: {target}")
        local_path(root, source)
        local_path(root, target)
        targets.add(target)
    return entries


def skill_directory(target):
    """Return the skill directory owning a bundled resource target, if any."""
    match = SKILL_RESOURCE.fullmatch(target)
    return match.group("skill") if match else None


def strip_frontmatter(text, source):
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError(f"unterminated frontmatter: {source}")
    return text[end + len("\n---\n"):].lstrip("\n")


def render_skill_resource(text, origin, destination, skill):
    """Rebase links for a skill resource that is vendored without this repository.

    Links that stay inside the skill directory remain relative, because the
    installer copies the whole directory. Links that leave it become absolute
    links to the canonical default branch, so no vendored link breaks.
    """
    masked, unmask = _mask_code(text)

    def replace(match):
        raw = match.group("url")
        angled = raw.startswith("<") and raw.endswith(">")
        url = raw[1:-1] if angled else raw
        parts = urlsplit(url)
        if parts.scheme or parts.netloc or not parts.path or parts.path.startswith("/"):
            return match.group(0)
        resolved = posixpath.normpath(str(PurePosixPath(origin).parent / parts.path))
        if resolved == ".." or resolved.startswith("../"):
            raise ValueError(f"knowledge link escapes the repository: {url}")
        if resolved == skill or resolved.startswith(skill + "/"):
            moved = posixpath.relpath(resolved, str(PurePosixPath(destination).parent))
        else:
            moved = f"{CANONICAL_BLOB}/{resolved}"
        if parts.path.endswith("/"):
            moved = moved.rstrip("/") + "/"
        if parts.query:
            moved += "?" + parts.query
        if parts.fragment:
            moved += "#" + parts.fragment
        if angled:
            moved = "<" + moved + ">"
        return match.group("prefix") + moved + match.groupdict().get("suffix", "")

    return unmask(DEFINITION.sub(replace, LINK.sub(replace, masked)))


def render(root, entry):
    source = local_path(root, entry["source"])
    target = local_path(root, entry["target"])
    header = (
        f"<!-- GENERATED from {entry['source']}. Do not edit this delivery copy.\n"
        "Regenerate: python3 automation/knowledge/knowledge-delivery.py\n"
        "Check: python3 automation/knowledge/knowledge-delivery.py --check -->\n\n"
    )
    skill = skill_directory(entry["target"])
    if skill:
        # Native instruction frontmatter (applyTo, excludeAgent) has no meaning
        # inside a skill, and a reference must resolve without this repository.
        text = strip_frontmatter(source.read_text(encoding="utf-8"), entry["source"])
        return header + render_skill_resource(text, entry["source"], entry["target"], skill)
    text = rebase_links(source.read_text(encoding="utf-8"), source, target)
    return with_provenance(text, header, entry["source"])


def with_provenance(text, header, source):
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end < 0:
            raise ValueError(f"unterminated frontmatter: {source}")
        boundary = end + len("\n---\n")
        return text[:boundary] + "\n" + header + text[boundary:].lstrip("\n")
    return header + text


def load_project_entries(root, downstream):
    path = local_path(root, PROJECT_MANIFEST)
    if not path.exists():
        return []  # Older organization revisions have no project deliveries.
    manifest = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    if not isinstance(manifest, dict) or set(manifest) != {"version", "consumers"} or type(manifest["version"]) is not int or manifest["version"] != 1 or not isinstance(manifest["consumers"], list):
        raise ValueError("unsupported project knowledge delivery manifest")
    fields = {"repository", "source", "target", "revision", "source_blob", "content_sha256", "project_revision", "project_source_blob"}
    surfaces = {item["repository"]: {surface["path"] for surface in item.get("surfaces", [])} for item in downstream}
    seen = set()
    for entry in manifest["consumers"]:
        if not isinstance(entry, dict) or set(entry) != fields or not all(isinstance(value, str) and value for value in entry.values()):
            raise ValueError("project delivery needs exactly the declared provenance fields")
        repository, source, target = entry["repository"], entry["source"], entry["target"]
        if repository not in surfaces or target not in surfaces[repository]:
            raise ValueError(f"undeclared project knowledge consumer: {repository}:{target}")
        if not source.startswith("knowledge/domains/") or not source.endswith(".md"):
            raise ValueError(f"project knowledge source is outside domains: {source}")
        if not target.startswith(".github/instructions/") or not target.endswith(".instructions.md"):
            raise ValueError(f"project knowledge target must be a scoped instruction: {target}")
        local_path(root, source)
        local_path(root, target)
        for field in ("revision", "source_blob", "project_revision", "project_source_blob", "content_sha256"):
            length = 64 if field == "content_sha256" else 40
            if not re.fullmatch(r"[0-9a-f]{%d}" % length, entry[field]):
                raise ValueError(f"project knowledge {field} must be {length} lowercase hex characters")
        key = (repository, target)
        if key in seen:
            raise ValueError(f"duplicate project knowledge consumer: {repository}:{target}")
        seen.add(key)
    return manifest["consumers"]


def render_project(text, entry):
    """Keep org links immutable and tested-project links local to the consumer."""
    masked, unmask = _mask_code(text)

    def replace(match):
        raw = match.group("url")
        angled = raw.startswith("<") and raw.endswith(">")
        parts = urlsplit(raw[1:-1] if angled else raw)
        prefix = f"/{entry['repository']}/blob/{entry['project_revision']}/"
        if parts.scheme == "https" and parts.netloc == "github.com" and parts.path.startswith(prefix):
            project_path = parts.path[len(prefix):]
            if ".." in PurePosixPath(project_path).parts:
                raise ValueError("escaping project reference")
            moved = posixpath.relpath(project_path, str(PurePosixPath(entry["target"]).parent))
        elif parts.scheme or parts.netloc or not parts.path or parts.path.startswith("/"):
            return match.group(0)
        else:
            org_path = posixpath.normpath(str(PurePosixPath(entry["source"]).parent / parts.path))
            if org_path == ".." or org_path.startswith("../"):
                raise ValueError("escaping organization knowledge reference")
            moved = f"https://github.com/z-shell/.github/blob/{entry['revision']}/{org_path}"
        if parts.path.endswith("/"):
            moved = moved.rstrip("/") + "/"
        if parts.query:
            moved += "?" + parts.query
        if parts.fragment:
            moved += "#" + parts.fragment
        if angled:
            moved = "<" + moved + ">"
        return match.group("prefix") + moved + match.groupdict().get("suffix", "")

    rebased = unmask(DEFINITION.sub(replace, LINK.sub(replace, masked)))
    provenance = {key: entry[key] for key in sorted(entry) if key != "content_sha256"}
    header = "<!-- PROJECT KNOWLEDGE " + json.dumps(provenance, sort_keys=True, separators=(",", ":")) + " -->\n\n"
    return with_provenance(rebased, header, entry["source"])


def approved_project_content(org_root, entry):
    """Resolve the approved Git blob, rather than rendering dirty authoring files."""
    def git(*args):
        return subprocess.run(["git", "-C", str(org_root), *args], check=True, capture_output=True, timeout=30).stdout

    git("merge-base", "--is-ancestor", entry["revision"], "HEAD")
    tree = git("ls-tree", entry["revision"], "--", entry["source"]).decode().split()
    if len(tree) != 4 or tree[:2] != ["100644", "blob"] or tree[2] != entry["source_blob"]:
        raise ValueError(f"approved project source blob differs: {entry['source']}")
    text = git("show", f"{entry['revision']}:{entry['source']}").decode("utf-8")
    expected = render_project(text, entry)
    if hashlib.sha256(expected.encode("utf-8")).hexdigest() != entry["content_sha256"]:
        raise ValueError(f"approved project consumer digest differs: {entry['repository']}:{entry['target']}")
    return expected


def project_outputs(org_root, project_root, repository, entries):
    return [
        (local_path(project_root, entry["target"]), approved_project_content(org_root, entry))
        for entry in entries if entry["repository"] == repository
    ]


def check_project(project_root, repository, entries):
    errors = []
    for entry in entries:
        if entry["repository"] != repository:
            continue
        target = local_path(project_root, entry["target"])
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != entry["content_sha256"]:
            errors.append(f"{entry['target']}: project knowledge content or provenance differs from approved revision {entry['revision']}")
    return errors


def run(root, check):
    entries = load_entries(root)
    # Validate and render every input before writing any delivery copy.
    outputs = [(local_path(root, item["target"]), render(root, item)) for item in entries]
    stale = []
    for target, expected in outputs:
        if target.exists() and target.read_bytes() == expected.encode():
            continue
        stale.append(str(target.relative_to(root)))
        if not check:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(expected, encoding="utf-8")
    if check and stale:
        for name in stale:
            print(f"stale knowledge delivery: {name}", file=sys.stderr)
        return 1
    print(f"knowledge delivery {'checked' if check else 'generated'}: {len(outputs)} consumers")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=next(parent for parent in Path(__file__).resolve().parents if (parent / ".github/instruction-surfaces.json").is_file()))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        return run(args.root.resolve(), args.check)
    except (OSError, ValueError, TypeError) as exc:
        print(f"knowledge delivery failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
