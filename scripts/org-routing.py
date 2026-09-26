#!/usr/bin/env python3
"""Generate and verify the organization routing preamble (decisions/0031).

The canonical inventory is the ``downstream`` section of
``.github/instruction-surfaces.json``; approved vendored-skill revisions live in
``lib/approved-skills.json``. This script is the only generator of the
``org-routing`` block. It never writes to another repository: ``apply`` edits
the checkout it is pointed at, and ``check`` only reports.

Commands:

  render   --repository OWNER/NAME           print the generated block
  check    --repository OWNER/NAME --root DIR verify a checkout (CI gate)
  apply    --repository OWNER/NAME --root DIR write the block into DIR/AGENTS.md
  validate                                   validate the manifest and lib file
  verify-approved                            confirm approved digests against git
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import subprocess  # nosec B404 - fixed git invocation in verify-approved only
import sys
from pathlib import Path, PurePosixPath

ORG_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ".github/instruction-surfaces.json"
APPROVED_PATH = "lib/approved-skills.json"
CANONICAL_REPOSITORY = "z-shell/.github"
CANONICAL_REPO_URL = "https://github.com/z-shell/.github"
POLICY_URL = "https://github.com/z-shell/.github/blob/main/AGENTS.md"
MANIFEST_URL = (
    "https://github.com/z-shell/.github/blob/main/.github/instruction-surfaces.json"
)
DECISION_URL = (
    "https://github.com/z-shell/.github/blob/main/decisions/"
    "0031-per-repository-instruction-routing-delivery.md"
)
BEGIN_MARKER = "<!-- BEGIN org-routing -->"
END_MARKER = "<!-- END org-routing -->"
AGENTS_PATH = "AGENTS.md"
SKILLS_DIR = ".github/skills"
REPOSITORY_PATTERN = re.compile(r"^z-shell/[A-Za-z0-9_.-]+$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DOWNSTREAM_FIELDS = {"repository", "surfaces", "vendored_skills"}
SURFACE_FIELDS = {"path", "tasks", "file_patterns"}
APPROVED_FIELDS = {"version", "source", "skills"}
APPROVED_SKILL_FIELDS = {"path", "revision", "digest", "files"}
METADATA_KEYS = {
    "github-path",
    "github-pinned",
    "github-ref",
    "github-repo",
    "github-tree-sha",
}


class RoutingError(Exception):
    pass


def error(path: str, rule: str, fix: str) -> str:
    return f"{path}: {rule}; fix: {fix}"


# --------------------------------------------------------------------------
# Loading and schema validation
# --------------------------------------------------------------------------


def _reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    parsed: dict[str, object] = {}
    for key, value in pairs:
        if key in parsed:
            raise ValueError(f"duplicate JSON key {key!r}")
        parsed[key] = value
    return parsed


def load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=_reject_duplicates)


def _string_list(value: object) -> bool:
    """Non-empty list of unique, trimmed strings that render safely in a code span."""
    return (
        isinstance(value, list)
        and bool(value)
        and all(
            isinstance(item, str)
            and item.strip() == item
            and item
            and "`" not in item
            and item.isprintable()
            for item in value
        )
        and len(set(value)) == len(value)
    )


def _safe_relative(path: object) -> bool:
    if not isinstance(path, str) or not path or path != path.strip():
        return False
    pure = PurePosixPath(path)
    return (
        not pure.is_absolute()
        and ".." not in pure.parts
        and "\\" not in path
        and str(pure) == path
    )


SURFACE_PATTERNS = (
    ("adapter", re.compile(r"^\.github/copilot-instructions\.md$")),
    ("scoped-guidance", re.compile(r"^\.github/instructions/[^/]+\.instructions\.md$")),
    ("agent", re.compile(r"^\.github/agents/[^/]+\.agent\.md$")),
    ("prompt", re.compile(r"^\.github/prompts/[^/]+\.prompt\.md$")),
    ("skill", re.compile(r"^\.github/skills/[a-z0-9][a-z0-9-]*/SKILL\.md$")),
)
DISCOVERY_GLOBS = (
    ".github/copilot-instructions.md",
    ".github/instructions/*.instructions.md",
    ".github/agents/*.agent.md",
    ".github/prompts/*.prompt.md",
    ".github/skills/*/SKILL.md",
)


def _surface_path_kind(path: str) -> str | None:
    for kind, pattern in SURFACE_PATTERNS:
        if pattern.fullmatch(path):
            return kind
    return None


def validate_downstream(downstream: object) -> list[str]:
    """Validate the manifest's ``downstream`` section."""
    where = f"{MANIFEST_PATH} downstream"
    if not isinstance(downstream, list) or not downstream:
        return [
            error(
                MANIFEST_PATH,
                "downstream must be a non-empty list",
                "declare each consuming repository",
            )
        ]
    errors: list[str] = []
    seen: set[str] = set()
    previous = ""
    for index, entry in enumerate(downstream):
        if not isinstance(entry, dict):
            errors.append(
                error(
                    where,
                    f"entry {index} must be an object",
                    "replace it with a repository object",
                )
            )
            continue
        repository = entry.get("repository")
        label = repository if isinstance(repository, str) else f"entry {index}"
        for field in sorted(set(entry) - DOWNSTREAM_FIELDS):
            errors.append(
                error(
                    where, f"{label} has unknown field {field!r}", f"remove {field!r}"
                )
            )
        if not isinstance(repository, str) or not REPOSITORY_PATTERN.fullmatch(
            repository
        ):
            errors.append(
                error(
                    where,
                    f"{label} repository must match z-shell/<name>",
                    "set repository",
                )
            )
            continue
        if repository == CANONICAL_REPOSITORY:
            errors.append(
                error(
                    where,
                    "the canonical repository is not downstream",
                    f"remove {repository}",
                )
            )
        if repository in seen:
            errors.append(
                error(where, f"duplicate repository {repository}", "keep one entry")
            )
        seen.add(repository)
        if repository.lower() < previous:
            errors.append(
                error(
                    where, f"{repository} is out of order", "sort entries by repository"
                )
            )
        previous = repository.lower()

        surfaces = entry.get("surfaces", [])
        if not isinstance(surfaces, list):
            errors.append(
                error(
                    where,
                    f"{repository} surfaces must be a list",
                    "set surfaces to a list",
                )
            )
            surfaces = []
        paths: set[str] = set()
        for surface in surfaces:
            if not isinstance(surface, dict):
                errors.append(
                    error(
                        where,
                        f"{repository} surface must be an object",
                        "fix the surface",
                    )
                )
                continue
            path = surface.get("path")
            for field in sorted(set(surface) - SURFACE_FIELDS):
                errors.append(
                    error(
                        where,
                        f"{repository} surface {path!r} has unknown field {field!r}",
                        f"remove {field!r}",
                    )
                )
            if not _safe_relative(path) or _surface_path_kind(str(path)) is None:
                errors.append(
                    error(
                        where,
                        f"{repository} surface path {path!r} is not a routable instruction surface",
                        "declare one of: " + ", ".join(DISCOVERY_GLOBS),
                    )
                )
                continue
            if path in paths:
                errors.append(
                    error(
                        where, f"{repository} declares {path} twice", "keep one surface"
                    )
                )
            paths.add(str(path))
            for field in ("tasks", "file_patterns"):
                if not _string_list(surface.get(field)):
                    errors.append(
                        error(
                            where,
                            f"{repository} surface {path} {field} must be a non-empty unique string list",
                            f"set {field}",
                        )
                    )
        skills = entry.get("vendored_skills", [])
        if (
            not isinstance(skills, list)
            or not all(
                isinstance(name, str) and SKILL_NAME_PATTERN.fullmatch(name)
                for name in skills
            )
            or len(set(skills)) != len(skills)
        ):
            errors.append(
                error(
                    where,
                    f"{repository} vendored_skills must be unique skill names",
                    "fix vendored_skills",
                )
            )
        elif skills != sorted(skills):
            errors.append(
                error(
                    where,
                    f"{repository} vendored_skills must be sorted",
                    "sort vendored_skills",
                )
            )
        else:
            for name in skills:
                if f"{SKILLS_DIR}/{name}/SKILL.md" in paths:
                    errors.append(
                        error(
                            where,
                            f"{repository} declares vendored skill {name} as a local surface too",
                            "keep it in vendored_skills only",
                        )
                    )
        ordered = [
            surface.get("path") for surface in surfaces if isinstance(surface, dict)
        ]
        if all(isinstance(path, str) for path in ordered) and ordered != sorted(
            ordered
        ):
            errors.append(
                error(
                    where,
                    f"{repository} surfaces must be sorted by path",
                    "sort surfaces",
                )
            )
    return errors


def validate_approved(
    approved: object, org_root: Path, downstream: object, org_surfaces: object = None
) -> list[str]:
    """Validate ``lib/approved-skills.json`` and its links to the manifest."""
    if not isinstance(approved, dict):
        return [
            error(
                APPROVED_PATH, "top-level value must be an object", "restore the object"
            )
        ]
    errors: list[str] = []
    for field in sorted(set(approved) - APPROVED_FIELDS):
        errors.append(
            error(APPROVED_PATH, f"unknown field {field!r}", f"remove {field!r}")
        )
    if type(approved.get("version")) is not int or approved.get("version") != 1:
        errors.append(error(APPROVED_PATH, "version must be 1", "set version to 1"))
    if approved.get("source") != CANONICAL_REPOSITORY:
        errors.append(
            error(
                APPROVED_PATH, f"source must be {CANONICAL_REPOSITORY!r}", "set source"
            )
        )
    skills = approved.get("skills")
    if not isinstance(skills, dict) or not skills:
        errors.append(
            error(
                APPROVED_PATH,
                "skills must be a non-empty object",
                "declare approved skills",
            )
        )
        skills = {}
    for name, record in skills.items():
        if not SKILL_NAME_PATTERN.fullmatch(name) or not isinstance(record, dict):
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name!r} must be a named object",
                    "fix the entry",
                )
            )
            continue
        for field in sorted(set(record) - APPROVED_SKILL_FIELDS):
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name} has unknown field {field!r}",
                    f"remove {field!r}",
                )
            )
        for field in sorted(APPROVED_SKILL_FIELDS - set(record)):
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name} is missing {field!r}",
                    f"add {field!r}",
                )
            )
        if record.get("path") != f"{SKILLS_DIR}/{name}":
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name} path must be {SKILLS_DIR}/{name}",
                    "fix path",
                )
            )
        elif not (org_root / record["path"] / "SKILL.md").is_file():
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name} has no canonical SKILL.md",
                    "approve an existing skill",
                )
            )
        if not isinstance(record.get("revision"), str) or not SHA_PATTERN.fullmatch(
            record["revision"]
        ):
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name} revision must be a full commit SHA",
                    "pin a 40-hex commit",
                )
            )
        if not isinstance(record.get("digest"), str) or not DIGEST_PATTERN.fullmatch(
            record["digest"]
        ):
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name} digest must be a sha256 hex digest",
                    "run verify-approved",
                )
            )
        files = record.get("files")
        if (
            not _string_list(files)
            or "SKILL.md" not in files
            or not all(_safe_relative(f) for f in files)
        ):
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name} files must list SKILL.md and contained paths",
                    "fix files",
                )
            )
        elif files != sorted(files):
            errors.append(
                error(APPROVED_PATH, f"skill {name} files must be sorted", "sort files")
            )
        if isinstance(org_surfaces, list) and not any(
            isinstance(surface, dict)
            and surface.get("kind") == "skill"
            and surface.get("path") == f"{SKILLS_DIR}/{name}/SKILL.md"
            for surface in org_surfaces
        ):
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name} is not an organization skill surface",
                    f"declare {SKILLS_DIR}/{name}/SKILL.md in {MANIFEST_PATH}",
                )
            )
    if isinstance(downstream, list):
        for entry in downstream:
            if not isinstance(entry, dict) or not isinstance(
                entry.get("vendored_skills"), list
            ):
                continue
            for name in entry["vendored_skills"]:
                if isinstance(name, str) and name not in skills:
                    errors.append(
                        error(
                            MANIFEST_PATH,
                            f"{entry.get('repository')} vendors {name}, which has no approved revision",
                            f"add {name} to {APPROVED_PATH}",
                        )
                    )
    return errors


class Org:
    """The loaded, validated canonical inventory."""

    def __init__(
        self, downstream: list[dict], approved: dict, org_surfaces: list[dict]
    ) -> None:
        self.downstream = downstream
        self.approved = approved
        self.skill_tasks = {
            surface["path"]: surface["tasks"]
            for surface in org_surfaces
            if isinstance(surface, dict) and surface.get("kind") == "skill"
        }

    def tasks_for_skill(self, name: str) -> list[str]:
        return list(self.skill_tasks.get(f"{SKILLS_DIR}/{name}/SKILL.md", []))


def load_org(org_root: Path) -> Org:
    manifest = load_json(org_root / MANIFEST_PATH)
    approved = load_json(org_root / APPROVED_PATH)
    downstream = manifest.get("downstream") if isinstance(manifest, dict) else None
    org_surfaces = manifest.get("surfaces") if isinstance(manifest, dict) else None
    errors = validate_downstream(downstream) + validate_approved(
        approved, org_root, downstream, org_surfaces
    )
    if errors:
        raise RoutingError("\n".join(errors))
    return Org(downstream, approved, org_surfaces or [])  # type: ignore[arg-type]


def downstream_entry(downstream: list[dict], repository: str) -> dict:
    for entry in downstream:
        if entry["repository"].lower() == repository.lower():
            return entry
    raise RoutingError(
        error(
            MANIFEST_PATH,
            f"{repository} is not declared downstream",
            f"add {repository} to the downstream section in {CANONICAL_REPOSITORY}",
        )
    )


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def _code_list(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values)


def render(entry: dict, org: Org) -> str:
    lines = [
        BEGIN_MARKER,
        "<!-- Generated by z-shell/.github scripts/org-routing.py (decisions/0031). "
        "Do not edit between these markers. -->",
        "",
        "## Organization instruction routing",
        "",
        f"Organization policy is owned by [`z-shell/.github` `AGENTS.md`]({POLICY_URL}). "
        "Read it before non-trivial work. Repository guidance in this file and in the "
        "surfaces below narrows implementation detail and never overrides organization policy.",
        "",
        "Before acting, select every surface below whose tasks and file patterns both "
        "match the work, and read each one. If your runtime does not load a listed file "
        "automatically, open it explicitly.",
        "",
        "- `AGENTS.md` (this file): tasks `all`; files `**`",
    ]
    for surface in entry.get("surfaces", []):
        lines.append(
            f"- `{surface['path']}`: tasks {_code_list(surface['tasks'])}; "
            f"files {_code_list(surface['file_patterns'])}"
        )
    for name in entry.get("vendored_skills", []):
        revision = org.approved["skills"][name]["revision"]
        lines.append(
            f"- `{SKILLS_DIR}/{name}/SKILL.md`: tasks {_code_list(org.tasks_for_skill(name))}; "
            f"files `**`; organization skill vendored at approved revision `{revision[:12]}`"
        )
    lines += [
        "",
        f"Organization-wide surfaces are routed by the [organization manifest]({MANIFEST_URL}). "
        f"This block is delivered and verified under [decision 0031]({DECISION_URL}).",
        "",
        END_MARKER,
    ]
    return "\n".join(lines) + "\n"


def splice(text: str | None, block: str, repository: str) -> str:
    """Return AGENTS.md text with the generated block inserted or replaced."""
    if text is None:
        name = repository.split("/", 1)[1]
        return (
            f"# Agent instructions: {name}\n\n{block}\n"
            "## Repository guidance\n\n"
            "This repository has no repository-specific agent guidance yet. Add it in "
            "this section; the generated block above is replaced on regeneration.\n"
        )
    begin = text.count(BEGIN_MARKER)
    end = text.count(END_MARKER)
    if begin or end:
        if begin != 1 or end != 1 or text.index(BEGIN_MARKER) > text.index(END_MARKER):
            raise RoutingError(
                error(
                    AGENTS_PATH,
                    "org-routing markers are unbalanced",
                    "leave exactly one BEGIN and one END marker",
                )
            )
        start = text.index(BEGIN_MARKER)
        stop = text.index(END_MARKER) + len(END_MARKER)
        if text[stop : stop + 1] == "\n":
            stop += 1
        return text[:start] + block + text[stop:]
    first, newline, rest = text.partition("\n")
    if first.startswith("# "):
        body = rest.lstrip("\n")
        return f"{first}\n\n{block}" + (f"\n{body}" if body else "")
    return block + ("\n" + text if text else "")


# --------------------------------------------------------------------------
# Skill parsing
# --------------------------------------------------------------------------


def parse_skill(text: str) -> tuple[dict[str, str], dict[str, str], str]:
    """Split SKILL.md into scalar frontmatter, installer metadata and body.

    Top-level keys must be scalars, except ``metadata``, whose direct children
    are read as scalars; values nested deeper than those children are ignored.
    Other nested top-level values are kept verbatim as part of their key.
    """
    match = re.fullmatch(r"---\n((?:[^\n]*\n)*?)---\n([\s\S]*)", text)
    if match is None:
        raise ValueError("missing --- frontmatter")
    scalars: dict[str, str] = {}
    metadata: dict[str, str] = {}
    current: str | None = None
    child_indent: int | None = None
    seen: set[str] = set()
    for line in match[1].splitlines():
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent:
            if current is None:
                raise ValueError(f"unexpected indented line {line!r}")
            if current != "metadata":
                scalars[current] += "\n" + line.rstrip()
                continue
            if child_indent is None:
                child_indent = indent
            if indent > child_indent:
                continue
            if indent < child_indent:
                raise ValueError(f"inconsistent metadata indentation {line!r}")
            key, sep, value = line.strip().partition(":")
            if not sep:
                raise ValueError(f"invalid metadata line {line!r}")
            metadata[key.strip()] = value.strip()
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"unsupported frontmatter line {line!r}")
        key = key.strip()
        if key in seen:
            raise ValueError(f"duplicate frontmatter key {key!r}")
        seen.add(key)
        current = key
        child_indent = None
        if key == "metadata":
            if value.strip():
                raise ValueError("metadata must be a mapping")
            continue
        scalars[key] = value.strip()
    return scalars, metadata, match[2]


def skill_digest(text: str) -> str:
    """Digest of a skill with the installer's metadata block excluded.

    Frontmatter keys are sorted and blank lines between the frontmatter and the
    body are dropped, so an installer's key order or a formatter's spacing does
    not count as drift. Every other byte of the body is significant.
    """
    scalars, _metadata, body = parse_skill(text)
    normalized = (
        "".join(f"{key}: {scalars[key]}\n" for key in sorted(scalars))
        + "---\n"
        + body.lstrip("\n")
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Checking a downstream checkout
# --------------------------------------------------------------------------


def _read_regular(root: Path, relative: str) -> str | None:
    path = root / relative
    try:
        mode = path.lstat().st_mode
    except OSError:
        return None
    if not stat.S_ISREG(mode) or not path.resolve().is_relative_to(root.resolve()):
        return None
    return path.read_text(encoding="utf-8")


def _regular_files(directory: Path) -> list[str]:
    return sorted(
        str(path.relative_to(directory).as_posix())
        for path in directory.rglob("*")
        if path.is_file() and not path.is_symlink()
    )


def _is_agents_alias(root: Path, path: Path) -> bool:
    """Report whether a path is a symlink adapter resolving to the root AGENTS.md."""
    return path.is_symlink() and path.resolve() == (root / AGENTS_PATH).resolve()


def _discovered_surfaces(root: Path) -> list[str]:
    """Routable surfaces present in a checkout, minus aliases of AGENTS.md."""
    found: set[str] = set()
    for pattern in DISCOVERY_GLOBS:
        for path in root.glob(pattern):
            relative = path.relative_to(root).as_posix()
            if _surface_path_kind(relative) is not None and not _is_agents_alias(
                root, path
            ):
                found.add(relative)
    return sorted(found)


def check(root: Path, repository: str, org: Org) -> list[str]:
    entry = downstream_entry(org.downstream, repository)
    block = render(entry, org)
    errors: list[str] = []
    fix_apply = (
        f"run python3 scripts/org-routing.py apply --repository {entry['repository']} --root <checkout> "
        f"from a {CANONICAL_REPOSITORY} clone"
    )
    fix_manifest = f"declare it for {entry['repository']} in the {CANONICAL_REPOSITORY} downstream manifest"

    agents = _read_regular(root, AGENTS_PATH)
    if agents is None:
        errors.append(error(AGENTS_PATH, "missing or not a regular file", fix_apply))
    elif BEGIN_MARKER not in agents and END_MARKER not in agents:
        errors.append(error(AGENTS_PATH, "org-routing block is missing", fix_apply))
    else:
        try:
            expected = splice(agents, block, entry["repository"])
        except RoutingError as exc:
            errors.append(str(exc))
        else:
            if expected != agents:
                errors.append(
                    error(
                        AGENTS_PATH,
                        "org-routing block differs from the generated block",
                        fix_apply,
                    )
                )

    declared = {surface["path"] for surface in entry.get("surfaces", [])}
    vendored = entry.get("vendored_skills", [])
    vendored_paths = {f"{SKILLS_DIR}/{name}/SKILL.md" for name in vendored}
    for path in sorted(declared):
        if _read_regular(root, path) is None:
            errors.append(
                error(
                    path,
                    "declared surface is missing or not a regular file",
                    f"restore it or remove it from the {CANONICAL_REPOSITORY} manifest",
                )
            )
    for relative in _discovered_surfaces(root):
        if relative in declared or relative in vendored_paths:
            continue
        text = _read_regular(root, relative)
        metadata: dict[str, str] = {}
        if text is not None and relative.startswith(SKILLS_DIR + "/"):
            try:
                _scalars, metadata, _body = parse_skill(text)
            except ValueError:
                metadata = {}
        if metadata.get("github-repo") == CANONICAL_REPO_URL:
            name = relative.split("/")[2]
            errors.append(
                error(
                    relative,
                    "skill is installed from the organization but not declared",
                    f"add {name} to vendored_skills for {entry['repository']}",
                )
            )
        else:
            errors.append(
                error(
                    relative,
                    "instruction surface is not declared downstream",
                    fix_manifest,
                )
            )
    for name in vendored:
        errors.extend(_check_skill(root, name, org.approved["skills"][name]))
    return errors


def _check_skill(root: Path, name: str, record: dict) -> list[str]:
    relative = f"{record['path']}/SKILL.md"
    revision = record["revision"]
    reinstall = (
        f"gh skill install {CANONICAL_REPOSITORY} {record['path']} --pin {revision} --dir {SKILLS_DIR} "
        "(authorized installation, runbooks/org-review.md)"
    )
    text = _read_regular(root, relative)
    if text is None:
        return [error(relative, "vendored skill is missing", reinstall)]
    try:
        _scalars, metadata, _body = parse_skill(text)
        digest = skill_digest(text)
    except ValueError as exc:
        return [error(relative, f"invalid skill frontmatter: {exc}", reinstall)]
    errors: list[str] = []
    if (
        metadata.get("github-repo") != CANONICAL_REPO_URL
        or metadata.get("github-path") != record["path"]
    ):
        errors.append(
            error(
                relative,
                "installer metadata does not name the canonical source",
                reinstall,
            )
        )
    pinned = metadata.get("github-pinned")
    if pinned != revision:
        errors.append(
            error(
                relative,
                f"pinned revision {pinned!r} is not the approved revision {revision}",
                reinstall,
            )
        )
    if digest != record["digest"]:
        errors.append(
            error(
                relative, "content differs from the approved canonical skill", reinstall
            )
        )
    files = _regular_files(root / record["path"])
    if files != record["files"]:
        errors.append(
            error(
                record["path"],
                f"files {files} differ from approved {record['files']}",
                reinstall,
            )
        )
    return errors


# --------------------------------------------------------------------------
# Approved-revision verification (canonical repository only)
# --------------------------------------------------------------------------


def verify_approved(org_root: Path, approved: dict) -> list[str]:
    errors: list[str] = []
    for name, record in sorted(approved["skills"].items()):
        revision = record["revision"]
        try:
            text = subprocess.run(  # nosec B603 B607 - fixed git arguments
                [
                    "git",
                    "-C",
                    str(org_root),
                    "show",
                    f"{revision}:{record['path']}/SKILL.md",
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            listing = subprocess.run(  # nosec B603 B607 - fixed git arguments
                [
                    "git",
                    "-C",
                    str(org_root),
                    "ls-tree",
                    "-r",
                    "--name-only",
                    revision,
                    "--",
                    record["path"] + "/",
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            errors.append(
                error(
                    APPROVED_PATH,
                    f"cannot read {name} at {revision}: {exc}",
                    "fetch full history or fix the revision",
                )
            )
            continue
        if skill_digest(text) != record["digest"]:
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name} digest does not match its content at {revision}",
                    "recompute the digest",
                )
            )
        files = sorted(
            line[len(record["path"]) + 1 :] for line in listing.splitlines() if line
        )
        if files != record["files"]:
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name} files {record['files']} differ from {files} at {revision}",
                    "fix files",
                )
            )
    return errors


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--org-root", type=Path, default=ORG_ROOT, help="z-shell/.github checkout"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("render", "check", "apply"):
        command = commands.add_parser(name)
        command.add_argument("--repository", required=True)
        if name != "render":
            command.add_argument("--root", type=Path, required=True)
    commands.add_parser("validate")
    commands.add_parser("verify-approved")
    arguments = parser.parse_args(argv)

    try:
        org = load_org(arguments.org_root)
        if arguments.command == "validate":
            print("org routing inventory is valid")
            return 0
        if arguments.command == "verify-approved":
            errors = verify_approved(arguments.org_root, org.approved)
            for message in errors:
                print(f"ERROR: {message}")
            if not errors:
                print("approved skill revisions verified")
            return 1 if errors else 0
        entry = downstream_entry(org.downstream, arguments.repository)
        if arguments.command == "render":
            sys.stdout.write(render(entry, org))
            return 0
        root = arguments.root.resolve()
        if arguments.command == "apply":
            current = _read_regular(root, AGENTS_PATH)
            if current is None and (root / AGENTS_PATH).exists():
                raise RoutingError(
                    error(
                        AGENTS_PATH,
                        "exists but is not a regular file",
                        "replace it with a regular file",
                    )
                )
            updated = splice(current, render(entry, org), entry["repository"])
            if updated != current:
                (root / AGENTS_PATH).write_text(updated, encoding="utf-8")
                print(f"updated {AGENTS_PATH}")
            else:
                print(f"{AGENTS_PATH} is current")
            return 0
        errors = check(root, arguments.repository, org)
    except RoutingError as exc:
        for message in str(exc).splitlines():
            print(f"ERROR: {message}")
        return 1
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    for message in errors:
        print(f"ERROR: {message}")
    if not errors:
        print(f"org routing for {arguments.repository} is current")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
