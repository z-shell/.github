#!/usr/bin/env python3
"""Generate and verify the organization routing preamble (decisions/0031).

The canonical inventory is the ``downstream`` section of
``.github/instruction-surfaces.json``; approved vendored-skill revisions live in
``knowledge/domains/agents/data/approved-skills.json``; project profiles, whose
issue-reporting facts the block carries, live in
``knowledge/domains/governance/data/project-profiles.json``. This script is the
only generator of the ``org-routing`` block. Complete project instruction records live in
``knowledge/project-delivery.json``. ``apply`` edits only the explicit target
checkout's block and declared complete consumers; ``check`` only reports.

Commands:

  render   --repository OWNER/NAME           print the generated block
  check    --repository OWNER/NAME --root DIR verify a checkout (CI gate)
  apply    --repository OWNER/NAME --root DIR write the block and selected consumers
  validate                                   validate routing and delivery inventories
  verify-approved                            confirm approved digests against git
"""

from __future__ import annotations

import argparse
import datetime
import fnmatch
import hashlib
import importlib.util
import json
import os
import re
import stat
import subprocess  # nosec B404 - fixed git invocation in verify-approved only
import sys
from pathlib import Path, PurePosixPath

ORG_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".github/instruction-surfaces.json").is_file())
MANIFEST_PATH = ".github/instruction-surfaces.json"
APPROVED_PATH = "knowledge/domains/agents/data/approved-skills.json"
PROFILES_PATH = "knowledge/domains/governance/data/project-profiles.json"
DELIVERY_SPEC = importlib.util.spec_from_file_location(
    "knowledge_delivery", Path(__file__).parents[1] / "knowledge/knowledge-delivery.py"
)
assert DELIVERY_SPEC and DELIVERY_SPEC.loader
delivery = importlib.util.module_from_spec(DELIVERY_SPEC)
DELIVERY_SPEC.loader.exec_module(delivery)
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
TRIAGE_URL = (
    "https://github.com/z-shell/.github/blob/main/runbooks/triage.md#filing-a-new-issue"
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
APPROVED_SKILL_OPTIONAL_FIELDS = {"source", "tasks", "resources"}
# Repositories an approved skill may come from (decisions/0037), with the shape
# of a skill path in each. A skill without its own source comes from the
# top-level source, which stays the canonical repository.
APPROVED_SOURCES = {
    CANONICAL_REPOSITORY: re.compile(r"^\.github/skills/(?P<name>[a-z0-9][a-z0-9-]*)$"),
    "z-shell/agent-skills": re.compile(
        r"^plugins/[a-z0-9][a-z0-9-]*/skills/(?P<name>[a-z0-9][a-z0-9-]*)$"
    ),
}
APPROVED_SOURCE_PATHS = {
    CANONICAL_REPOSITORY: SKILLS_DIR + "/{name}",
    "z-shell/agent-skills": "plugins/<plugin>/skills/{name}",
}
PROFILE_FIELDS = {
    "component",
    "verified",
    "version",
    "branch",
    "zsh",
    "install",
    "verification",
    "report_fields",
}
PROFILE_VERIFIED_FIELDS = {"revision", "date"}
PROFILE_VERSION_FIELDS = {"command", "note"}
PROFILE_ZSH_FIELDS = {"minimum", "tested", "platforms"}
PROFILE_REPORT_FIELDS = {"label", "description"}
ZSH_VERSION_PATTERN = re.compile(r"^\d+\.\d+(?:\.\d+)?$")
WORKFLOWS_DIR = ".github/workflows"
# Keys through which a workflow selects the Zsh it installs: a matrix list
# (zi `zsh`, zpmod `version`), the setup-zsh `version` and Zsh CI
# `zsh-version` inputs, and the source-build `ZSH_VERSION` (F-Sy-H).
ZSH_KEY_LINE = re.compile(
    r"^(?P<indent>\s*)(?:-\s+)?(?P<key>zsh|version|zsh-version|ZSH_VERSION)\s*:\s*(?P<value>.*?)\s*(?:#.*)?$"
)
LIST_ITEM_LINE = re.compile(r"^(?P<indent>\s*)-\s+(?P<value>.*?)\s*(?:#.*)?$")
METADATA_KEYS = {
    "github-path",
    "github-pinned",
    "github-ref",
    "github-repo",
    "github-tree-sha",
}


class RoutingError(Exception):
    pass


def source_url(source: str) -> str:
    """Return the repository URL ``gh skill install`` records for a source."""
    return f"https://github.com/{source}"


def skill_source(record: dict) -> str:
    """Return the approved repository a skill comes from."""
    return record.get("source", CANONICAL_REPOSITORY)


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


_NAME = r"[A-Za-z0-9][A-Za-z0-9._-]*"
# The organization repository keeps its own Copilot adapter; a project
# repository's AGENTS.md is its only instruction entry point
# (runbooks/new-repository.md), so a downstream entry never declares it.
ADAPTER_PATH = ".github/copilot-instructions.md"
ADAPTER_FIX = (
    "remove it; AGENTS.md is the project's only instruction entry point "
    "(runbooks/new-repository.md)"
)
SURFACE_PATTERNS = (
    ("adapter", re.compile(r"^\.github/copilot-instructions\.md$")),
    (
        "scoped-guidance",
        re.compile(rf"^\.github/instructions/(?:{_NAME}/)*{_NAME}\.instructions\.md$"),
    ),
    ("agent", re.compile(rf"^\.github/agents/{_NAME}\.agent\.md$")),
    ("prompt", re.compile(rf"^\.github/prompts/{_NAME}\.prompt\.md$")),
    ("skill", re.compile(r"^\.github/skills/[a-z0-9][a-z0-9-]*/SKILL\.md$")),
)
DISCOVERY_GLOBS = (
    ".github/copilot-instructions.md",
    ".github/instructions/**/*.instructions.md",
    ".github/agents/*.agent.md",
    ".github/prompts/*.prompt.md",
    ".github/skills/*/SKILL.md",
)
# Runtime instruction carriers that a downstream repository cannot declare:
# guidance belongs in AGENTS.md or a declared surface (decisions/0014, 0031).
UNSUPPORTED_CARRIER_GLOBS = (
    "**/AGENTS.md",
    "**/CLAUDE.md",
    "**/GEMINI.md",
    ".claude/**/*",
    ".cursorrules",
    ".cursor/**/*",
    ".github/chatmodes/**/*",
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
            if path == ADAPTER_PATH:
                errors.append(
                    error(
                        where,
                        f"{repository} declares {path}, which project repositories do not carry",
                        ADAPTER_FIX,
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


def _profile_text(value: object) -> bool:
    """One printable line with balanced code spans that cannot open or close a comment."""
    return (
        isinstance(value, str)
        and bool(value)
        and value.strip() == value
        and value.isprintable()
        and "<!--" not in value
        and "-->" not in value
        and value.count("`") % 2 == 0
    )


def _iso_date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return datetime.date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _text_list(value: object) -> bool:
    """Non-empty list of unique profile lines without backticks."""
    return (
        isinstance(value, list)
        and bool(value)
        and all(_profile_text(item) and "`" not in item for item in value)
        and len(set(value)) == len(value)
    )


def _closed(value: object, fields: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == fields


def _profile_errors(repository: str, record: dict) -> list[str]:
    """Return the field errors of one complete project profile."""
    invalid: list[tuple[str, str]] = []
    if (
        not _profile_text(record["component"])
        or not _profile_text(record["branch"])
        or "`" in record["branch"]
    ):
        invalid.append(
            ("component or branch", "set a one-line name; a branch has no backticks")
        )
    verified = record["verified"]
    if (
        not _closed(verified, PROFILE_VERIFIED_FIELDS)
        or not isinstance(verified["revision"], str)
        or not SHA_PATTERN.fullmatch(verified["revision"])
        or not _iso_date(verified["date"])
    ):
        invalid.append(
            (
                "verified",
                "record the 40-hex commit and YYYY-MM-DD date the facts were read at",
            )
        )
    version = record["version"]
    if not _closed(version, PROFILE_VERSION_FIELDS):
        invalid.append(("version", "set command and note"))
    else:
        command, note = version["command"], version["note"]
        if command is None and note is None:
            invalid.append(("version", "give a command, a note, or both"))
        if command is not None and (not _profile_text(command) or "`" in command):
            invalid.append(
                ("version command", "set a command without backticks, or null")
            )
        if note is not None and not _profile_text(note):
            invalid.append(("version note", "set a one-line note, or null"))
    zsh = record["zsh"]
    if (
        not _closed(zsh, PROFILE_ZSH_FIELDS)
        or not (
            zsh["minimum"] is None
            or (
                isinstance(zsh["minimum"], str)
                and ZSH_VERSION_PATTERN.fullmatch(zsh["minimum"])
            )
        )
        or not _text_list(zsh["tested"])
        or not all(ZSH_VERSION_PATTERN.fullmatch(item) for item in zsh["tested"])
        or not _text_list(zsh["platforms"])
    ):
        invalid.append(
            ("zsh", "set minimum (a version or null), tested versions and platforms")
        )
    for field in ("install", "verification"):
        if not _text_list(record[field]):
            invalid.append(
                (field, "set a non-empty unique list of commands without backticks")
            )
    fields = record["report_fields"]
    labels: set[str] = set()
    for item in fields if isinstance(fields, list) else [None]:
        if (
            not _closed(item, PROFILE_REPORT_FIELDS)
            or not _profile_text(item["label"])  # type: ignore[index]
            or "`" in item["label"]  # type: ignore[index]
            or not _profile_text(item["description"])  # type: ignore[index]
        ):
            invalid.append(
                (
                    "report_fields",
                    "give each field a plain label and a one-line description",
                )
            )
            continue
        if item["label"] in labels:
            invalid.append(("report_fields", f"keep one {item['label']!r} field"))
        labels.add(item["label"])
    return [
        error(PROFILES_PATH, f"{repository} {field} is invalid", fix)
        for field, fix in invalid
    ]


def validate_profiles(profiles: object, downstream: list[dict]) -> list[str]:
    """Validate project profiles (decisions/0040) against the downstream inventory."""
    where = PROFILES_PATH
    if (
        not _closed(profiles, {"version", "profiles"})
        or type(profiles["version"]) is not int  # type: ignore[index]
        or profiles["version"] != 1  # type: ignore[index]
    ):
        return [
            error(where, "must hold exactly version 1 and profiles", "fix the header")
        ]
    records = profiles["profiles"]  # type: ignore[index]
    if not isinstance(records, dict):
        return [
            error(where, "profiles must be an object keyed by repository", "fix it")
        ]
    declared = {
        entry["repository"]
        for entry in downstream
        if isinstance(entry, dict) and isinstance(entry.get("repository"), str)
    }
    errors: list[str] = []
    if list(records) != sorted(records, key=str.lower):
        errors.append(
            error(where, "profiles are out of order", "sort profiles by repository")
        )
    for repository, record in records.items():
        if repository not in declared:
            errors.append(
                error(
                    where,
                    f"{repository} is not declared downstream",
                    f"declare it in {MANIFEST_PATH} or remove its profile",
                )
            )
        if not isinstance(record, dict):
            errors.append(
                error(where, f"{repository} profile must be an object", "fix it")
            )
            continue
        for field in sorted(set(record) ^ PROFILE_FIELDS):
            state = "unknown" if field in record else "missing"
            errors.append(
                error(
                    where,
                    f"{repository} has {state} field {field!r}",
                    "use exactly the profile fields",
                )
            )
        if set(record) == PROFILE_FIELDS:
            errors.extend(_profile_errors(repository, record))
    return errors


def load_profiles(org_root: Path, downstream: list[dict]) -> dict[str, dict]:
    path = org_root / PROFILES_PATH
    if not path.exists():
        return {}  # Older organization revisions have no project profiles.
    profiles = load_json(path)
    errors = validate_profiles(profiles, downstream)
    if errors:
        raise RoutingError("\n".join(errors))
    return profiles["profiles"]  # type: ignore[index]


def git_blob_id(data: bytes) -> str:
    """Git's object id for a blob, so a file can be compared with a tree entry."""
    return hashlib.sha1(  # nosec B324 - Git object identity, not a security digest
        b"blob %d\0" % len(data) + data
    ).hexdigest()


def _validate_resources(name: str, files: list[str], resources: object) -> list[str]:
    """Require a multi-file skill to pin every file besides SKILL.md by its Git blob id."""
    expected = [path for path in files if path != "SKILL.md"]
    if resources is None and not expected:
        return []
    if (
        not isinstance(resources, dict)
        or sorted(resources) != expected
        or not all(
            isinstance(value, str) and SHA_PATTERN.fullmatch(value)
            for value in resources.values()
        )
    ):
        return [
            error(
                APPROVED_PATH,
                f"skill {name} resources must map each file other than SKILL.md to its 40-hex Git blob id",
                "run verify-approved and record the blob ids it reports",
            )
        ]
    return []


def validate_approved(
    approved: object, org_root: Path, downstream: object, org_surfaces: object = None
) -> list[str]:
    """Validate ``knowledge/domains/agents/data/approved-skills.json`` and its links to the manifest."""
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
        for field in sorted(
            set(record) - APPROVED_SKILL_FIELDS - APPROVED_SKILL_OPTIONAL_FIELDS
        ):
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
        source = skill_source(record)
        if "source" in record and (
            not isinstance(source, str)
            or source not in APPROVED_SOURCES
            or source == CANONICAL_REPOSITORY
        ):
            others = sorted(set(APPROVED_SOURCES) - {CANONICAL_REPOSITORY})
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name} source must be one of {others}",
                    f"omit source for {CANONICAL_REPOSITORY} skills",
                )
            )
            continue
        path = record.get("path")
        match = (
            APPROVED_SOURCES[source].fullmatch(path) if isinstance(path, str) else None
        )
        if not match or match["name"] != name:
            expected = APPROVED_SOURCE_PATHS[source].format(name=name)
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name} path must be {expected}",
                    "fix path",
                )
            )
        elif (
            source == CANONICAL_REPOSITORY
            and not (org_root / str(path) / "SKILL.md").is_file()
        ):
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
        else:
            errors.extend(_validate_resources(name, files, record.get("resources")))
        if source != CANONICAL_REPOSITORY:
            tasks = record.get("tasks")
            if not _string_list(tasks):
                errors.append(
                    error(
                        APPROVED_PATH,
                        f"skill {name} from {source} needs tasks as a non-empty unique string list",
                        "declare the tasks that select the vendored skill",
                    )
                )
        elif "tasks" in record:
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name} takes its tasks from its organization skill surface",
                    f"remove tasks; edit the surface in {MANIFEST_PATH}",
                )
            )
        if (
            source == CANONICAL_REPOSITORY
            and isinstance(org_surfaces, list)
            and not any(
                isinstance(surface, dict)
                and surface.get("kind") == "skill"
                and surface.get("path") == f"{SKILLS_DIR}/{name}/SKILL.md"
                for surface in org_surfaces
            )
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
        self,
        downstream: list[dict],
        approved: dict,
        org_surfaces: list[dict],
        project_entries: list[dict] | None = None,
        profiles: dict[str, dict] | None = None,
    ) -> None:
        self.downstream = downstream
        self.profiles = profiles or {}
        self.approved = approved
        self.project_entries = project_entries or []
        self.skill_tasks = {
            surface["path"]: surface["tasks"]
            for surface in org_surfaces
            if isinstance(surface, dict) and surface.get("kind") == "skill"
        }

    def tasks_for_skill(self, name: str) -> list[str]:
        record = self.approved["skills"][name]
        if "tasks" in record:
            return list(record["tasks"])
        return list(self.skill_tasks.get(f"{SKILLS_DIR}/{name}/SKILL.md", []))

    def source_of(self, name: str) -> str:
        return skill_source(self.approved["skills"][name])


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
    project_entries = delivery.load_project_entries(org_root, downstream)
    profiles = load_profiles(org_root, downstream)  # type: ignore[arg-type]
    return Org(downstream, approved, org_surfaces or [], project_entries, profiles)  # type: ignore[arg-type]


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
    generated = (
        "<!-- Generated by z-shell/.github automation/agents/org-routing.py (decisions/0031). "
        + "Do not edit between these markers. -->"
    )
    policy = (
        f"Organization policy is owned by [`z-shell/.github` `AGENTS.md`]({POLICY_URL}). "
        + "Read it before non-trivial work. Repository guidance in this file and in the "
        + "surfaces below narrows implementation detail and never overrides organization policy."
    )
    selection = (
        "Before acting, select every surface below whose tasks and file patterns both "
        + "match the work, and read each one. If your runtime does not load a listed file "
        + "automatically, open it explicitly."
    )
    footer = (
        f"Organization-wide surfaces are routed by the [organization manifest]({MANIFEST_URL}). "
        + f"This block is delivered and verified under [decision 0031]({DECISION_URL})."
    )
    lines = [
        BEGIN_MARKER,
        generated,
        "",
        "## Organization instruction routing",
        "",
        policy,
        "",
        selection,
        "",
        "- `AGENTS.md` (this file): tasks `all`; files `**`",
    ]
    for surface in entry.get("surfaces", []):
        lines.append(
            f"- `{surface['path']}`: tasks {_code_list(surface['tasks'])}; "
            + f"files {_code_list(surface['file_patterns'])}"
        )
    for name in entry.get("vendored_skills", []):
        revision = org.approved["skills"][name]["revision"]
        source = org.source_of(name)
        origin = (
            "organization skill"
            if source == CANONICAL_REPOSITORY
            else f"skill from `{source}`"
        )
        lines.append(
            f"- `{SKILLS_DIR}/{name}/SKILL.md`: tasks {_code_list(org.tasks_for_skill(name))}; "
            + f"files `**`; {origin} vendored at approved revision `{revision[:12]}`"
        )
    profile = org.profiles.get(entry["repository"])
    if profile:
        lines += ["", *render_reporting(profile)]
    lines += ["", footer, "", END_MARKER]
    return "\n".join(lines) + "\n"


def render_reporting(profile: dict) -> list[str]:
    """Render the intake facts no repository-owned text states (decisions/0040).

    Branch, Zsh versions, install and verification commands stay in the
    profile: repositories state them in their own text already.
    """
    version = profile["version"]
    intake = (
        f"File an issue as [Filing a new issue]({TRIAGE_URL}) describes: one "
        + "`### ` heading per field of the effective issue form, in form order."
    )
    if version["command"] is not None:
        intake += (
            " In the version or environment field, give the output of "
            + f"`{version['command']}`."
        )
    if version["note"] is not None:
        intake += f" {version['note']}"
    lines = ["## Reporting issues", "", intake]
    if profile["report_fields"]:
        lines += [
            "",
            "After the form's fields, add these headings, writing `Not applicable` "
            + "and the reason when one does not apply:",
            "",
        ]
        lines += [
            f"- `### {item['label']}`: {item['description']}"
            for item in profile["report_fields"]
        ]
    return lines


def splice(text: str | None, block: str, repository: str) -> str:
    """Return AGENTS.md text with the generated block at its required place.

    The block begins the file, after an optional first ``# `` title line
    (decision 0031, point 1). An existing block is removed and reinserted
    there, so a block moved later in the file, or wrapped in a fence, is
    regenerated in place and fails ``check``.
    """
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
        text = text[:start] + text[stop:]
    first, _newline, rest = text.partition("\n")
    if first.startswith("# "):
        body = rest.lstrip("\n")
        return f"{first}\n\n{block}" + (f"\n{body}" if body else "")
    body = text.lstrip("\n")
    return block + ("\n" + body if body else "")


# --------------------------------------------------------------------------
# Skill parsing
# --------------------------------------------------------------------------


def parse_skill(
    text: str, strict_metadata: bool = False
) -> tuple[dict[str, str], dict[str, str], str]:
    """Split SKILL.md into scalar frontmatter, installer metadata and body.

    Top-level keys must be scalars, except ``metadata``, whose direct children
    are read as scalars. Other nested top-level values are kept verbatim as
    part of their key. With ``strict_metadata`` (a vendored organization
    skill, whose digest excludes metadata), only the installer's keys are
    accepted and nothing may nest below them, so no content can hide there;
    otherwise deeper values are ignored.
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
                if strict_metadata:
                    raise ValueError(f"nested installer metadata {line.strip()!r}")
                continue
            if indent < child_indent:
                raise ValueError(f"inconsistent metadata indentation {line!r}")
            key, sep, value = line.strip().partition(":")
            if not sep:
                raise ValueError(f"invalid metadata line {line!r}")
            key = key.strip()
            if strict_metadata and key not in METADATA_KEYS:
                raise ValueError(f"unexpected installer metadata key {key!r}")
            if key in metadata:
                raise ValueError(f"duplicate installer metadata key {key!r}")
            metadata[key] = value.strip()
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


def check_project_selector(text: str, record: dict, org: Org) -> None:
    surface = next(
        surface
        for entry in org.downstream if entry["repository"] == record["repository"]
        for surface in entry.get("surfaces", []) if surface["path"] == record["target"]
    )
    scalars, _, _ = parse_skill(text)
    selector = scalars.get("applyTo", "")
    if selector.startswith('"'):
        selector = json.loads(selector)
    elif selector.startswith("'") and selector.endswith("'"):
        selector = selector[1:-1].replace("''", "'")
    else:
        raise ValueError(f"{record['target']}: applyTo must be a quoted scalar")
    if selector != ",".join(surface["file_patterns"]):
        raise ValueError(f"{record['target']}: applyTo differs from declared project routing")


def skill_digest(text: str, strict_metadata: bool = False) -> str:
    """Digest of a skill with the installer's metadata block excluded.

    Frontmatter keys are sorted and blank lines between the frontmatter and the
    body are dropped, so an installer's key order or a formatter's spacing does
    not count as drift. Every other byte of the body is significant.
    """
    scalars, _metadata, body = parse_skill(text, strict_metadata)
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


def _zsh_literals(value: str) -> list[str]:
    """Return the literal Zsh versions in one YAML scalar or flow list."""
    if value.startswith("[") and value.endswith("]"):
        items = value[1:-1].split(",")
    else:
        items = [value]
    versions = []
    for item in items:
        item = item.strip().strip("'\"")
        if ZSH_VERSION_PATTERN.fullmatch(item):
            versions.append(item)
    return versions


def workflow_zsh_versions(root: Path) -> dict[str, set[str]]:
    """Map each literal Zsh version a checkout's workflows install to its files.

    Only literal values under the keys in ``ZSH_KEY_LINE`` count; an
    expression such as ``${{ matrix.zsh }}`` names a list found elsewhere,
    and a runner's own Zsh has no version to compare (decisions/0040).
    """
    directory = root / WORKFLOWS_DIR
    if directory.is_symlink() or not directory.is_dir():
        return {}
    found: dict[str, set[str]] = {}
    for path in sorted(directory.iterdir()):
        if path.suffix not in (".yml", ".yaml"):
            continue
        relative = f"{WORKFLOWS_DIR}/{path.name}"
        text = _read_regular(root, relative)
        if text is None:
            continue
        block_indent: int | None = None
        for line in text.splitlines():
            if block_indent is not None:
                item = LIST_ITEM_LINE.match(line)
                if item and len(item.group("indent")) >= block_indent:
                    for version in _zsh_literals(item.group("value")):
                        found.setdefault(version, set()).add(relative)
                    continue
                if line.strip():
                    block_indent = None
            match = ZSH_KEY_LINE.match(line)
            if not match:
                continue
            if match.group("value"):
                for version in _zsh_literals(match.group("value")):
                    found.setdefault(version, set()).add(relative)
            else:
                block_indent = len(match.group("indent"))
    return found


def check_profile_versions(root: Path, repository: str, profile: dict) -> list[str]:
    """Compare a profile's tested Zsh versions with the checkout's workflows."""
    found = workflow_zsh_versions(root)
    stated = set(profile["zsh"]["tested"])
    errors = []
    fix = (
        f"make zsh.tested for {repository} in the {CANONICAL_REPOSITORY} "
        + f"{PROFILES_PATH} match the versions CI installs"
    )
    for version in sorted(stated - set(found)):
        errors.append(
            error(
                WORKFLOWS_DIR,
                f"project profile states Zsh {version} as tested, but no workflow installs it",
                fix,
            )
        )
    for version in sorted(set(found) - stated):
        errors.append(
            error(
                ", ".join(sorted(found[version])),
                f"workflow installs Zsh {version}, which the project profile does not state as tested",
                fix,
            )
        )
    return errors


def _skill_entries(directory: Path) -> list[str]:
    """Every non-directory entry below a skill directory, symlinks included.

    Symbolic links are listed with a ``@`` suffix, so a link can never match an
    approved file name and always fails the file comparison.
    """
    entries: list[str] = []
    for current, directories, files in os.walk(directory, followlinks=False):
        base = Path(current)
        for name in list(directories):
            if (base / name).is_symlink():
                directories.remove(name)
                files.append(name)
        for name in files:
            path = base / name
            relative = path.relative_to(directory).as_posix()
            mode = path.lstat().st_mode
            entries.append(relative if stat.S_ISREG(mode) else relative + "@")
    return sorted(entries)


def _is_agents_alias(root: Path, path: Path) -> bool:
    """Report whether a path is a symlink adapter resolving to the root AGENTS.md."""
    return path.is_symlink() and path.resolve() == (root / AGENTS_PATH).resolve()


def _display(path: str) -> str:
    """Render a checkout path so it cannot inject a workflow command."""
    return path if path.isprintable() else repr(path)


def _project_files(root: Path) -> list[Path] | None:
    """Use Git's project boundary, including tracked ignored files and new files.

    Exported trees have no Git inventory and retain filesystem discovery. Never
    use an enclosing repository's index for an export or fixture nested in it.
    """
    if not (root / ".git").exists():
        return None
    result = subprocess.run(  # nosec B603 B607 - fixed read-only git command
        [
            "git",
            "-C",
            str(root),
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
        ],
        capture_output=True,
        check=True,
        timeout=30,
    )
    return [
        root / os.fsdecode(name) for name in set(result.stdout.split(b"\0")) if name
    ]


def _matches_glob(relative: str, pattern: str) -> bool:
    # fnmatch permits multiple path components; the surface schema below rejects
    # unsupported nesting instead of silently accepting an unrouted carrier.
    return fnmatch.fnmatchcase(relative, pattern) or fnmatch.fnmatchcase(
        relative, pattern.replace("**/", "")
    )


def _discovered_surfaces(root: Path) -> tuple[list[str], list[str]]:
    """Return (routable surfaces, unroutable instruction files) in a checkout.

    Aliases of AGENTS.md are neither. A file that a discovery glob or a
    runtime carrier glob finds but no surface pattern accepts is unroutable:
    a runtime may still load it, so it cannot pass silently.
    """
    found: set[str] = set()
    unroutable: set[str] = set()
    project_files = _project_files(root)

    def candidates(pattern: str):
        if project_files is None:
            return root.glob(pattern)
        return (
            path
            for path in project_files
            if _matches_glob(path.relative_to(root).as_posix(), pattern)
        )

    for pattern in DISCOVERY_GLOBS:
        for path in candidates(pattern):
            if (
                (not path.exists() and not path.is_symlink())
                or path.is_dir()
                or _is_agents_alias(root, path)
            ):
                continue
            relative = path.relative_to(root).as_posix()
            if _surface_path_kind(relative) is not None:
                found.add(relative)
            else:
                unroutable.add(relative)
    for pattern in UNSUPPORTED_CARRIER_GLOBS:
        for path in candidates(pattern):
            relative = path.relative_to(root).as_posix()
            if (
                path.is_dir()
                or (not path.exists() and not path.is_symlink())
                or relative == AGENTS_PATH
                or relative.startswith(".git/")
                or _is_agents_alias(root, path)
            ):
                continue
            unroutable.add(relative)
    return sorted(found), sorted(unroutable)


def check(root: Path, repository: str, org: Org) -> list[str]:
    entry = downstream_entry(org.downstream, repository)
    block = render(entry, org)
    errors: list[str] = []
    fix_apply = (
        f"run python3 automation/agents/org-routing.py apply --repository {entry['repository']} --root <checkout> "
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
    surfaces, unroutable = _discovered_surfaces(root)
    for relative in unroutable:
        errors.append(
            error(
                _display(relative),
                "instruction file is not a routable surface",
                "move its guidance into AGENTS.md or a declared surface "
                "(decisions/0031); runtimes may load it unrouted",
            )
        )
    adapter = root / ADAPTER_PATH
    if adapter.exists() or adapter.is_symlink():
        # A symbolic link to AGENTS.md is an adapter too: report every form.
        errors.append(
            error(
                ADAPTER_PATH,
                "project repositories carry no Copilot adapter",
                ADAPTER_FIX,
            )
        )
    for relative in surfaces:
        if (
            relative in declared
            or relative in vendored_paths
            or relative == ADAPTER_PATH
        ):
            continue
        text = _read_regular(root, relative)
        metadata: dict[str, str] = {}
        if text is not None and relative.startswith(SKILLS_DIR + "/"):
            try:
                _scalars, metadata, _body = parse_skill(text)
            except ValueError:
                metadata = {}
        if metadata.get("github-repo") in {
            source_url(source) for source in APPROVED_SOURCES
        }:
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
                    _display(relative),
                    "instruction surface is not declared downstream",
                    fix_manifest,
                )
            )
    for name in vendored:
        errors.extend(_check_skill(root, name, org.approved["skills"][name]))
    profile = org.profiles.get(entry["repository"])
    if profile:
        errors.extend(check_profile_versions(root, entry["repository"], profile))
    errors.extend(delivery.check_project(root, repository, org.project_entries))
    for record in org.project_entries:
        if record["repository"] != repository:
            continue
        content = _read_regular(root, record["target"])
        if content is not None:
            try:
                check_project_selector(content, record, org)
            except ValueError as exc:
                errors.append(str(exc))
    return errors


def _check_skill(root: Path, name: str, record: dict) -> list[str]:
    # gh skill install --dir .github/skills places every skill at
    # .github/skills/<name>, whatever its path in the source repository.
    local = f"{SKILLS_DIR}/{name}"
    relative = f"{local}/SKILL.md"
    revision = record["revision"]
    source = skill_source(record)
    reinstall = (
        f"gh skill install {source} {record['path']} --pin {revision} --dir {SKILLS_DIR} "
        "(authorized installation, runbooks/org-review.md)"
    )
    text = _read_regular(root, relative)
    if text is None:
        return [error(relative, "vendored skill is missing", reinstall)]
    try:
        _scalars, metadata, _body = parse_skill(text, strict_metadata=True)
        digest = skill_digest(text, strict_metadata=True)
    except ValueError as exc:
        return [error(relative, f"invalid skill frontmatter: {exc}", reinstall)]
    errors: list[str] = []
    if (
        metadata.get("github-repo") != source_url(source)
        or metadata.get("github-path") != record["path"]
    ):
        errors.append(
            error(
                relative,
                "installer metadata does not name the approved source",
                reinstall,
            )
        )
    pinned = metadata.get("github-pinned")
    if metadata.get("github-ref", pinned) != pinned:
        errors.append(
            error(
                relative,
                "installer metadata github-ref differs from github-pinned",
                reinstall,
            )
        )
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
                relative, "content differs from the approved skill", reinstall
            )
        )
    files = _skill_entries(root / local)
    if files != record["files"]:
        errors.append(
            error(
                local,
                f"files {files} differ from approved {record['files']}",
                reinstall,
            )
        )
    for path, blob in sorted(record.get("resources", {}).items()):
        if path not in files:
            continue  # The file comparison above already reports it.
        if git_blob_id((root / local / path).read_bytes()) != blob:
            errors.append(
                error(
                    f"{local}/{path}",
                    "content differs from the approved skill resource",
                    reinstall,
                )
            )
    return errors


# --------------------------------------------------------------------------
# Approved-revision verification (canonical repository only)
# --------------------------------------------------------------------------


def verify_approved(
    org_root: Path, approved: dict, source_roots: dict[str, Path] | None = None
) -> list[str]:
    """Verify each approved revision against a full-history checkout of its source.

    Canonical skills are read from ``org_root``. A skill from another approved
    source needs that repository's checkout in ``source_roots``; without one it
    fails rather than passing unverified.
    """
    errors: list[str] = []
    for name, record in sorted(approved["skills"].items()):
        revision = record["revision"]
        source = skill_source(record)
        source_root = (
            org_root
            if source == CANONICAL_REPOSITORY
            else (source_roots or {}).get(source)
        )
        if source_root is None:
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name} comes from {source}, and no checkout of it was given",
                    f"pass --source-root {source}=PATH with full history",
                )
            )
            continue
        try:
            text = subprocess.run(  # nosec B603 B607 - fixed git arguments
                [
                    "git",
                    "-C",
                    str(source_root),
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
                    str(source_root),
                    "ls-tree",
                    "-r",
                    "-z",
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
        reachable = subprocess.run(  # nosec B603 B607 - fixed git arguments
            [
                "git",
                "-C",
                str(source_root),
                "merge-base",
                "--is-ancestor",
                revision,
                "HEAD",
            ],
            check=False,
            capture_output=True,
        )
        if reachable.returncode != 0:
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name} revision {revision} is not an ancestor of HEAD",
                    "approve a commit already on the default branch",
                )
            )
        if skill_digest(text) != record["digest"]:
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name} digest does not match its content at {revision}",
                    "recompute the digest",
                )
            )
        blobs = {}
        for line in listing.split("\0"):
            if not line:
                continue
            meta, _, entry = line.partition("\t")
            blobs[entry[len(record["path"]) + 1 :]] = meta.split()[-1]
        files = sorted(blobs)
        if files != record["files"]:
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name} files {record['files']} differ from {files} at {revision}",
                    "fix files",
                )
            )
        actual = {path: blob for path, blob in blobs.items() if path != "SKILL.md"}
        if actual != record.get("resources", {}):
            errors.append(
                error(
                    APPROVED_PATH,
                    f"skill {name} resources {record.get('resources', {})} differ from {actual} at {revision}",
                    "record the Git blob ids of the approved revision",
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
    verify = commands.add_parser("verify-approved")
    verify.add_argument(
        "--source-root",
        action="append",
        default=[],
        metavar="OWNER/REPO=PATH",
        help="full-history checkout of an approved source other than "
        + CANONICAL_REPOSITORY,
    )
    arguments = parser.parse_args(argv)

    try:
        org = load_org(arguments.org_root)
        if arguments.command == "validate":
            print("org routing inventory is valid")
            return 0
        if arguments.command == "verify-approved":
            source_roots: dict[str, Path] = {}
            for item in arguments.source_root:
                source, separator, path = item.partition("=")
                if (
                    not separator
                    or not path
                    or source not in APPROVED_SOURCES
                    or source == CANONICAL_REPOSITORY
                    or source in source_roots
                ):
                    raise RoutingError(
                        error(
                            "--source-root",
                            f"{item!r} must be OWNER/REPO=PATH for one approved source "
                            + "other than the canonical repository",
                            "name each approved source once",
                        )
                    )
                source_roots[source] = Path(path)
            errors = verify_approved(arguments.org_root, org.approved, source_roots)
            for record in org.project_entries:
                try:
                    content = delivery.approved_project_content(arguments.org_root, record)
                    check_project_selector(content, record, org)
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    errors.append(f"{delivery.PROJECT_MANIFEST}: {exc}")
            for message in errors:
                print(f"ERROR: {message}")
            if not errors:
                print("approved skill and project knowledge revisions verified")
            return 1 if errors else 0
        entry = downstream_entry(org.downstream, arguments.repository)
        if arguments.command == "render":
            sys.stdout.write(render(entry, org))
            return 0
        root = arguments.root.resolve()
        if arguments.command == "apply":
            agents_path = delivery.local_path(root, AGENTS_PATH)
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
            outputs = delivery.project_outputs(arguments.org_root, root, entry["repository"], org.project_entries)
            records = [record for record in org.project_entries if record["repository"] == entry["repository"]]
            for record, (_, expected) in zip(records, outputs):
                check_project_selector(expected, record, org)
            # All approved sources and target ancestors are checked before writes.
            if updated != current:
                agents_path.write_text(updated, encoding="utf-8")
                print(f"updated {AGENTS_PATH}")
            else:
                print(f"{AGENTS_PATH} is current")
            for target, expected in outputs:
                if not target.is_file() or target.read_bytes() != expected.encode("utf-8"):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(expected, encoding="utf-8")
                    print(f"updated {target.relative_to(root)}")
            return 0
        errors = check(root, arguments.repository, org)
    except RoutingError as exc:
        for message in str(exc).splitlines():
            print(f"ERROR: {message}")
        return 1
    except (OSError, UnicodeError, ValueError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}")
        return 1
    for message in errors:
        print(f"ERROR: {message}")
    if not errors:
        print(f"org routing for {arguments.repository} is current")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
