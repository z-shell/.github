#!/usr/bin/env python3

import argparse
import json
import os
import re
import stat
from pathlib import Path
from typing import cast

ALLOWED_KINDS = {
    "shared-policy",
    "scoped-guidance",
    "runbook",
    "decision",
    "agent",
    "skill",
    "adapter",
    "enforcement",
}
ALLOWED_AUTHORITIES = {
    "canonical",
    "canonical-detail",
    "adapter-only",
    "advisory",
}
ALLOWED_CONSUMERS = {
    "codex",
    "claude-code",
    "copilot",
    "gemini-cli",
    "human",
    "ci",
}
COPILOT_ADAPTER = "@../AGENTS.md\n"
FORBIDDEN_PUBLIC_TOKENS = (
    "repos/org/z-shell-dot-github",
    "workspace/repos.yml",
    "root meta-workspace",
    "meta-workspace root",
    "private meta-workspace",
    "memory/",
    "ZSHELL_MEMORY_GIST_ID",
    "scripts/memory-sync.sh",
    "user-profile.md",
    "/mnt/workspace",
    "~/Codespace",
    ".gitmodules",
)
FORBIDDEN_PUBLIC_PATH = re.compile(
    r"(?<![A-Za-z0-9_{])repos/" r"(?:annexes|core|docs|env|org|packages|plugins|tools)/"
)

MANIFEST_PATH = ".github/instruction-surfaces.json"
PUBLIC_POLICY_BYTE_LIMIT = 32_768
REQUIRED_SURFACE_FIELDS = (
    "id",
    "path",
    "kind",
    "authority",
    "consumers",
    "tasks",
    "file_patterns",
    "required",
    "review_owner",
    "canonical_for",
)
BASE_INVENTORY = {
    "AGENTS.md": "shared-policy",
    "PATTERNS.md": "shared-policy",
    ".github/AGENT_MEMORY.md": "runbook",
    ".github/README.md": "runbook",
    ".github/copilot-instructions.md": "adapter",
}
FLAT_INVENTORY = (
    (".github/instructions", ".instructions.md", "scoped-guidance"),
    (".github/agents", ".agent.md", "agent"),
    ("runbooks", ".md", "runbook"),
    ("decisions", ".md", "decision"),
)
ENFORCEMENT_INVENTORY = {
    ".github/workflows/agent-instructions.yml": "enforcement",
    "scripts/validate-agent-policy.py": "enforcement",
}
PUBLIC_SCAN_EXEMPTIONS = {"scripts/validate-agent-policy.py"}


def error(path: str, rule: str, fix: str) -> str:
    return f"{path}: {rule}; fix: {fix}"


def _invalid_single_line_character(character: str) -> bool:
    codepoint = ord(character)
    return codepoint < 32 or 127 <= codepoint <= 159 or codepoint in {0x2028, 0x2029}


def _one_line_path(path: str) -> str:
    return "".join(
        (
            "\\\\"
            if character == "\\"
            else (
                f"\\x{ord(character):02x}"
                if _invalid_single_line_character(character)
                else character
            )
        )
        for character in path
    )


def _invalid_discovered_path_error(path: str) -> str:
    display_path = _one_line_path(path)
    return error(
        display_path,
        "discovered path cannot be represented safely in one-line diagnostics",
        f"rename or remove the invalid path {display_path}",
    )


def _validated_manifest_path(root: Path) -> tuple[Path | None, list[str]]:
    manifest_path = root / MANIFEST_PATH
    try:
        file_status = manifest_path.lstat()
    except OSError as exc:
        return None, [
            error(
                MANIFEST_PATH,
                f"manifest must exist as a contained regular file: {exc}",
                f"restore a regular file at {MANIFEST_PATH}",
            )
        ]

    if stat.S_ISLNK(file_status.st_mode):
        return None, [
            error(
                MANIFEST_PATH,
                "manifest must be a contained regular file, not a symlink",
                f"replace {MANIFEST_PATH} with a regular file inside the repository",
            )
        ]
    if not stat.S_ISREG(file_status.st_mode):
        return None, [
            error(
                MANIFEST_PATH,
                "manifest must be a contained regular file",
                f"replace {MANIFEST_PATH} with a regular file inside the repository",
            )
        ]

    try:
        resolved = manifest_path.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        return None, [
            error(
                MANIFEST_PATH,
                f"cannot resolve manifest path: {exc}",
                f"restore a regular file at {MANIFEST_PATH}",
            )
        ]
    if not resolved.is_relative_to(root):
        return None, [
            error(
                MANIFEST_PATH,
                "manifest path escapes repository",
                f"move {MANIFEST_PATH} inside the repository",
            )
        ]
    return resolved, []


def _load_manifest(manifest_path: Path) -> dict[str, object]:
    with manifest_path.open(encoding="utf-8") as manifest_file:
        try:
            return cast(dict[str, object], json.load(manifest_file))
        except json.JSONDecodeError:
            raise
        except (ValueError, RecursionError) as exc:
            raise json.JSONDecodeError(str(exc), "", 0) from exc


def _declared_surfaces(manifest: object) -> list[dict[str, object]]:
    if not isinstance(manifest, dict):
        return []
    surfaces = manifest.get("surfaces")
    if not isinstance(surfaces, list):
        return []
    return [surface for surface in surfaces if isinstance(surface, dict)]


def _non_empty_string(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and not any(_invalid_single_line_character(character) for character in value)
    )


def _string_list(value: object, *, allow_empty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(_non_empty_string(item) for item in value)
    )


def _surface_name(surface: dict[str, object], index: int) -> str:
    surface_id = surface.get("id")
    if _non_empty_string(surface_id):
        return cast(str, surface_id)
    return f"surfaces[{index}]"


def _surface_path(surface: dict[str, object]) -> str | None:
    path = surface.get("path")
    if _non_empty_string(path):
        return cast(str, path)
    return None


def _inventory_path(relative_path: str) -> str:
    return Path(os.path.normpath(relative_path)).as_posix()


def _expected_inventory_kind(relative_path: str) -> str | None:
    inventory_path = _inventory_path(relative_path)
    exact_kind = BASE_INVENTORY.get(inventory_path) or ENFORCEMENT_INVENTORY.get(
        inventory_path
    )
    if exact_kind is not None:
        return exact_kind

    path = Path(inventory_path)
    for relative_directory, suffix, kind in FLAT_INVENTORY:
        if path.parent.as_posix() == relative_directory and path.name.endswith(suffix):
            return kind
    if re.fullmatch(r"\.github/skills/[^/]+/SKILL\.md", inventory_path):
        return "skill"
    return None


def _resolve_declared_path(root: Path, relative_path: str) -> Path | None:
    try:
        resolved = (root / relative_path).resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return None
    if not resolved.is_relative_to(root.resolve()):
        return None
    return resolved


def _read_utf8(path: Path, display_path: str) -> tuple[str | None, list[str]]:
    try:
        return path.read_text(encoding="utf-8"), []
    except UnicodeError as exc:
        return None, [
            error(
                display_path,
                f"invalid UTF-8 text: {exc}",
                f"rewrite {display_path} as valid UTF-8",
            )
        ]
    except OSError as exc:
        return None, [
            error(
                display_path,
                f"cannot read declared surface: {exc}",
                f"restore a readable regular file at {display_path}",
            )
        ]


def _inventory_scan_error(relative_path: str, exc: OSError) -> str:
    display_path = _one_line_path(relative_path)
    if display_path != relative_path:
        return _invalid_discovered_path_error(relative_path)
    return error(
        display_path,
        f"cannot scan inventory directory: {exc}",
        f"restore readable directory permissions for {display_path}",
    )


def _scan_flat_inventory(
    root: Path, relative_directory: str, suffix: str
) -> tuple[set[str], list[str]]:
    directory = root / relative_directory
    if not os.path.lexists(directory):
        return set(), []
    paths: set[str] = set()
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.name.endswith(suffix):
                    paths.add(f"{relative_directory}/{entry.name}")
    except OSError as exc:
        return set(), [_inventory_scan_error(relative_directory, exc)]
    return paths, []


def _scan_skill_inventory(root: Path) -> tuple[set[str], list[str]]:
    relative_directory = ".github/skills"
    directory = root / relative_directory
    if not os.path.lexists(directory):
        return set(), []
    paths: set[str] = set()
    errors: list[str] = []
    try:
        with os.scandir(directory) as skill_entries:
            for skill_entry in skill_entries:
                try:
                    is_directory = skill_entry.is_dir(follow_symlinks=True)
                except OSError as exc:
                    errors.append(
                        _inventory_scan_error(
                            f"{relative_directory}/{skill_entry.name}", exc
                        )
                    )
                    continue
                if not is_directory:
                    continue
                skill_directory = f"{relative_directory}/{skill_entry.name}"
                try:
                    with os.scandir(root / skill_directory) as files:
                        if any(entry.name == "SKILL.md" for entry in files):
                            paths.add(f"{skill_directory}/SKILL.md")
                except OSError as exc:
                    errors.append(_inventory_scan_error(skill_directory, exc))
    except OSError as exc:
        errors.append(_inventory_scan_error(relative_directory, exc))
    return paths, errors


def _required_inventory(root: Path) -> tuple[set[str], list[str]]:
    paths = set(BASE_INVENTORY)
    errors: list[str] = []
    for relative_directory, suffix, _kind in FLAT_INVENTORY:
        discovered, scan_errors = _scan_flat_inventory(root, relative_directory, suffix)
        paths.update(discovered)
        errors.extend(scan_errors)
    discovered_skills, skill_errors = _scan_skill_inventory(root)
    paths.update(discovered_skills)
    errors.extend(skill_errors)
    paths.update(
        relative_path
        for relative_path in ENFORCEMENT_INVENTORY
        if os.path.lexists(root / relative_path)
    )
    return paths, errors


def validate_manifest(root: Path, manifest: dict[str, object]) -> list[str]:
    errors: list[str] = []
    root = root.resolve()
    if not isinstance(manifest, dict):
        return [
            error(
                MANIFEST_PATH,
                "top-level JSON value must be an object",
                f"edit {MANIFEST_PATH} so its top-level value is an object",
            )
        ]

    if type(manifest.get("version")) is not int or manifest.get("version") != 1:
        errors.append(
            error(
                MANIFEST_PATH,
                f"unsupported version {manifest.get('version')!r}; expected version 1",
                f"set version to 1 in {MANIFEST_PATH}",
            )
        )

    if not _non_empty_string(manifest.get("repository")):
        errors.append(
            error(
                MANIFEST_PATH,
                "repository must be a non-empty string",
                f'set repository to "z-shell/.github" in {MANIFEST_PATH}',
            )
        )

    surfaces_value = manifest.get("surfaces")
    if not isinstance(surfaces_value, list):
        errors.append(
            error(
                MANIFEST_PATH,
                "surfaces must be a list",
                f"set surfaces to a JSON list in {MANIFEST_PATH}",
            )
        )
        surfaces_value = []

    seen_ids: dict[str, int] = {}
    seen_paths: dict[Path, str] = {}
    seen_canonical_domains: dict[str, str] = {}
    declared_inventory: set[str] = set()

    for index, surface_value in enumerate(surfaces_value):
        if not isinstance(surface_value, dict):
            errors.append(
                error(
                    MANIFEST_PATH,
                    f"surfaces[{index}] must be an object",
                    f"replace surfaces[{index}] with a surface object in {MANIFEST_PATH}",
                )
            )
            continue

        surface = surface_value
        name = _surface_name(surface, index)
        for field in REQUIRED_SURFACE_FIELDS:
            if field not in surface:
                errors.append(
                    error(
                        MANIFEST_PATH,
                        f"surface {name!r} is missing required field {field!r}",
                        f"add {field} to surface {name!r} in {MANIFEST_PATH}",
                    )
                )

        for field in ("id", "path", "review_owner"):
            if field in surface and not _non_empty_string(surface.get(field)):
                errors.append(
                    error(
                        MANIFEST_PATH,
                        f"surface {name!r} field {field!r} must be a non-empty string",
                        f"set {field} to a non-empty string for surface {name!r}",
                    )
                )

        kind = surface.get("kind")
        if not isinstance(kind, str) or kind not in ALLOWED_KINDS:
            errors.append(
                error(
                    MANIFEST_PATH,
                    f"surface {name!r} has unknown kind {kind!r}",
                    f"set kind for surface {name!r} to one of {sorted(ALLOWED_KINDS)!r}",
                )
            )

        authority = surface.get("authority")
        if not isinstance(authority, str) or authority not in ALLOWED_AUTHORITIES:
            errors.append(
                error(
                    MANIFEST_PATH,
                    f"surface {name!r} has unknown authority {authority!r}",
                    "set authority for surface "
                    f"{name!r} to one of {sorted(ALLOWED_AUTHORITIES)!r}",
                )
            )

        for field in ("consumers", "tasks", "file_patterns"):
            if field in surface and not _string_list(surface.get(field)):
                errors.append(
                    error(
                        MANIFEST_PATH,
                        f"surface {name!r} field {field!r} must be a non-empty list "
                        "of non-empty strings",
                        f"set {field} to a non-empty string list for surface {name!r}",
                    )
                )

        canonical_for = surface.get("canonical_for")
        if "canonical_for" in surface and not _string_list(
            canonical_for, allow_empty=True
        ):
            errors.append(
                error(
                    MANIFEST_PATH,
                    f"surface {name!r} field 'canonical_for' must be a list of "
                    "non-empty strings",
                    f"set canonical_for to a string list for surface {name!r}",
                )
            )

        required = surface.get("required")
        if "required" in surface and type(required) is not bool:
            errors.append(
                error(
                    MANIFEST_PATH,
                    f"surface {name!r} field 'required' must be a Boolean",
                    f"set required to true or false for surface {name!r}",
                )
            )

        consumers = surface.get("consumers")
        if isinstance(consumers, list):
            for consumer in consumers:
                if isinstance(consumer, str) and consumer not in ALLOWED_CONSUMERS:
                    errors.append(
                        error(
                            MANIFEST_PATH,
                            f"surface {name!r} has unknown consumer {consumer!r}",
                            "set consumers for surface "
                            f"{name!r} to values from {sorted(ALLOWED_CONSUMERS)!r}",
                        )
                    )

        surface_id = surface.get("id")
        if _non_empty_string(surface_id):
            surface_id = cast(str, surface_id)
            if surface_id in seen_ids:
                errors.append(
                    error(
                        MANIFEST_PATH,
                        f"duplicate surface id {surface_id!r}",
                        f"give every surface in {MANIFEST_PATH} a unique id",
                    )
                )
            else:
                seen_ids[surface_id] = index

        if isinstance(canonical_for, list):
            for domain in canonical_for:
                if not _non_empty_string(domain):
                    continue
                domain = cast(str, domain)
                if domain in seen_canonical_domains:
                    errors.append(
                        error(
                            MANIFEST_PATH,
                            f"duplicate canonical owner for domain {domain!r}",
                            f"leave exactly one canonical_for owner for {domain!r}",
                        )
                    )
                else:
                    seen_canonical_domains[domain] = name
                if required is not True:
                    errors.append(
                        error(
                            MANIFEST_PATH,
                            f"canonical owner for {domain!r} must be required",
                            f"set required to true for surface {name!r}",
                        )
                    )
                if isinstance(kind, str) and kind in {"agent", "skill"}:
                    errors.append(
                        error(
                            MANIFEST_PATH,
                            f"{kind} surface {name!r} cannot own canonical_for "
                            f"domain {domain!r}",
                            f"move {domain!r} ownership to a policy surface and set "
                            f"canonical_for to [] for {name!r}",
                        )
                    )
                if not isinstance(authority, str) or authority not in {
                    "canonical",
                    "canonical-detail",
                }:
                    errors.append(
                        error(
                            MANIFEST_PATH,
                            f"canonical owner for {domain!r} must use canonical or "
                            "canonical-detail authority",
                            f"set a canonical authority for surface {name!r}",
                        )
                    )

        if kind == "adapter" and (authority != "adapter-only" or canonical_for != []):
            errors.append(
                error(
                    MANIFEST_PATH,
                    f"adapter surface {name!r} cannot be canonical and must use "
                    "adapter-only authority with an empty canonical_for list",
                    f"set authority to adapter-only and canonical_for to [] for {name!r}",
                )
            )

        relative_path = _surface_path(surface)
        if relative_path is None:
            continue
        try:
            resolved = (root / relative_path).resolve(strict=False)
        except (OSError, RuntimeError, ValueError) as exc:
            errors.append(
                error(
                    relative_path,
                    f"cannot resolve declared path: {exc}",
                    f"replace {relative_path!r} with a valid repository-relative path",
                )
            )
            continue
        if not resolved.is_relative_to(root):
            errors.append(
                error(
                    relative_path,
                    "declared path escapes repository",
                    f"replace {relative_path!r} with a path below the repository root",
                )
            )
            continue

        inventory_path = _inventory_path(relative_path)
        declared_inventory.add(inventory_path)
        expected_kind = _expected_inventory_kind(relative_path)
        if expected_kind is not None and kind != expected_kind:
            errors.append(
                error(
                    relative_path,
                    f"declared kind {kind!r} does not match inventory kind "
                    f"{expected_kind!r}",
                    f"set kind to {expected_kind!r} for surface {name!r}",
                )
            )
        if resolved in seen_paths:
            errors.append(
                error(
                    relative_path,
                    f"duplicate declared path also used by {seen_paths[resolved]!r}",
                    f"give every surface in {MANIFEST_PATH} a unique path",
                )
            )
        else:
            seen_paths[resolved] = name

        try:
            is_regular_file = resolved.is_file()
        except OSError as exc:
            errors.append(
                error(
                    relative_path,
                    f"cannot inspect declared path: {exc}",
                    f"restore a readable regular file at {relative_path}",
                )
            )
        else:
            if not is_regular_file:
                errors.append(
                    error(
                        relative_path,
                        "declared path must exist as a regular file",
                        f"create the regular file {relative_path} or remove its manifest entry",
                    )
                )

    required_inventory, inventory_errors = _required_inventory(root)
    errors.extend(inventory_errors)

    for missing_path in sorted(required_inventory - declared_inventory):
        display_path = _one_line_path(missing_path)
        if display_path != missing_path:
            errors.append(_invalid_discovered_path_error(missing_path))
            continue
        errors.append(
            error(
                display_path,
                "surface is missing from manifest inventory",
                f"declare {display_path} in {MANIFEST_PATH}",
            )
        )

    canonical_policy = manifest.get("canonical_policy")
    if canonical_policy != "AGENTS.md":
        errors.append(
            error(
                MANIFEST_PATH,
                "canonical_policy must be exactly 'AGENTS.md'",
                f"set canonical_policy to 'AGENTS.md' in {MANIFEST_PATH}",
            )
        )
    canonical_surface: dict[str, object] | None = None
    if _non_empty_string(canonical_policy):
        canonical_path = _resolve_declared_path(root, cast(str, canonical_policy))
        if canonical_path is not None:
            for surface in _declared_surfaces(manifest):
                relative_path = _surface_path(surface)
                if relative_path is None:
                    continue
                if _resolve_declared_path(root, relative_path) == canonical_path:
                    canonical_surface = surface
                    break

    if canonical_surface is None or not (
        canonical_surface.get("kind") == "shared-policy"
        and canonical_surface.get("authority") == "canonical"
        and canonical_surface.get("required") is True
        and isinstance(canonical_surface.get("canonical_for"), list)
        and "organization-policy" in canonical_surface.get("canonical_for", [])
    ):
        errors.append(
            error(
                MANIFEST_PATH,
                "canonical_policy must resolve to the required canonical shared-policy "
                "surface that owns 'organization-policy'",
                f"set canonical_policy to the organization-policy path in {MANIFEST_PATH}",
            )
        )

    return errors


def _walk_skill_resources(
    root: Path, skill_directory: Path
) -> tuple[dict[str, Path], list[str]]:
    files: dict[str, Path] = {}
    errors: list[str] = []
    directories = [skill_directory]
    while directories:
        directory = directories.pop()
        raw_display_directory = directory.relative_to(root).as_posix()
        display_directory = _one_line_path(raw_display_directory)
        if display_directory != raw_display_directory:
            errors.append(_invalid_discovered_path_error(raw_display_directory))
            continue
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    path = Path(entry.path)
                    raw_display_path = path.relative_to(root).as_posix()
                    display_path = _one_line_path(raw_display_path)
                    if display_path != raw_display_path:
                        errors.append(_invalid_discovered_path_error(raw_display_path))
                        continue
                    try:
                        if entry.is_symlink() and entry.is_dir(follow_symlinks=True):
                            errors.append(
                                error(
                                    display_path,
                                    "skill resource directory symlink is not allowed",
                                    f"replace {display_path} with a regular directory "
                                    "below the repository root",
                                )
                            )
                            continue
                        if entry.is_file(follow_symlinks=True):
                            resolved = path.resolve(strict=False)
                            if not resolved.is_relative_to(root):
                                errors.append(
                                    error(
                                        display_path,
                                        "skill resource escapes repository",
                                        f"replace {display_path} with a regular file below "
                                        "the repository root",
                                    )
                                )
                            else:
                                files[display_path] = resolved
                        elif entry.is_dir(follow_symlinks=False):
                            directories.append(path)
                    except (OSError, RuntimeError, ValueError) as exc:
                        errors.append(
                            error(
                                display_path,
                                f"cannot inspect skill resource: {exc}",
                                f"repair or remove unreadable skill resource {display_path}",
                            )
                        )
        except OSError as exc:
            errors.append(
                error(
                    display_directory,
                    f"cannot scan skill resources: {exc}",
                    f"restore readable directory permissions for {display_directory}",
                )
            )
    return files, errors


def _files_for_public_scan(
    root: Path, manifest: dict[str, object]
) -> tuple[dict[str, Path], list[str]]:
    files: dict[str, Path] = {}
    errors: list[str] = []
    root = root.resolve()
    for surface in _declared_surfaces(manifest):
        relative_path = _surface_path(surface)
        if relative_path is None:
            continue
        inventory_path = _inventory_path(relative_path)
        expected_kind = _expected_inventory_kind(relative_path)
        if expected_kind == "decision":
            continue
        if inventory_path in PUBLIC_SCAN_EXEMPTIONS:
            continue
        resolved = _resolve_declared_path(root, relative_path)
        if resolved is None:
            continue
        try:
            if not resolved.is_file():
                continue
        except OSError:
            continue
        files[relative_path] = resolved

        if expected_kind != "skill":
            continue
        skill_files, skill_errors = _walk_skill_resources(root, resolved.parent)
        files.update(skill_files)
        errors.extend(skill_errors)
    return files, errors


def _manifest_string_values(manifest: object) -> list[str]:
    strings: list[str] = []
    pending = [manifest]
    while pending:
        value = pending.pop()
        if isinstance(value, str):
            strings.append(value)
        elif isinstance(value, dict):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    return strings


def _public_reference_errors(relative_path: str, text: str) -> list[str]:
    errors: list[str] = []
    casefolded_text = text.casefold()
    for token in FORBIDDEN_PUBLIC_TOKENS:
        if token.casefold() in casefolded_text:
            errors.append(
                error(
                    relative_path,
                    f"forbidden public token {token!r}",
                    f"remove {token!r} from {relative_path}",
                )
            )
    for match in FORBIDDEN_PUBLIC_PATH.finditer(text):
        forbidden_path = match.group(0)
        errors.append(
            error(
                relative_path,
                f"forbidden workspace path {forbidden_path!r}",
                f"replace {forbidden_path!r} with a public repository reference",
            )
        )
    return errors


def validate_public_references(root: Path, manifest: dict[str, object]) -> list[str]:
    files, errors = _files_for_public_scan(root, manifest)
    for value in _manifest_string_values(manifest):
        errors.extend(_public_reference_errors(MANIFEST_PATH, value))
    for relative_path, path in files.items():
        text, read_errors = _read_utf8(path, relative_path)
        errors.extend(read_errors)
        if text is None:
            continue
        errors.extend(_public_reference_errors(relative_path, text))
    return errors


def validate_public_policy_size(root: Path, _manifest: dict[str, object]) -> list[str]:
    policy_path = _resolve_declared_path(root, "AGENTS.md")
    if policy_path is None:
        return []
    try:
        if not policy_path.is_file():
            return []
        byte_size = policy_path.stat().st_size
    except OSError:
        return []
    if byte_size <= PUBLIC_POLICY_BYTE_LIMIT:
        return []
    return [
        error(
            "AGENTS.md",
            f"public policy is {byte_size:,} bytes; maximum is "
            f"{PUBLIC_POLICY_BYTE_LIMIT:,} bytes",
            f"reduce AGENTS.md to at most {PUBLIC_POLICY_BYTE_LIMIT:,} bytes",
        )
    ]


def _parse_apply_to_scalar(value: str) -> str | None:
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return parsed if _non_empty_string(parsed) else None
    if value.startswith("'"):
        if re.fullmatch(r"'(?:[^']|'')*'", value) is None:
            return None
        parsed = value[1:-1].replace("''", "'")
        return parsed if _non_empty_string(parsed) else None
    return None


def _frontmatter_apply_to(text: str) -> list[str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    closing_index = next(
        (
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == "---"
        ),
        None,
    )
    if closing_index is None:
        return []

    values: list[str] = []
    for line in lines[1:closing_index]:
        match = re.match(r"^applyTo\s*:\s*(.*?)\s*$", line)
        if match is None:
            continue
        parsed = _parse_apply_to_scalar(match.group(1))
        values.append(parsed or "")
    return values


def validate_scoped_instructions(root: Path, manifest: dict[str, object]) -> list[str]:
    errors: list[str] = []
    root = root.resolve()
    for surface in _declared_surfaces(manifest):
        if surface.get("kind") != "scoped-guidance":
            continue
        relative_path = _surface_path(surface)
        if relative_path is None:
            continue
        resolved = _resolve_declared_path(root, relative_path)
        if resolved is None:
            continue
        try:
            if not resolved.is_file():
                continue
        except OSError:
            continue

        text, read_errors = _read_utf8(resolved, relative_path)
        errors.extend(read_errors)
        if text is None:
            continue
        apply_to_values = _frontmatter_apply_to(text)
        file_patterns = surface.get("file_patterns")
        expected_pattern = (
            file_patterns[0]
            if isinstance(file_patterns, list)
            and len(file_patterns) == 1
            and isinstance(file_patterns[0], str)
            else None
        )
        if len(apply_to_values) != 1 or not apply_to_values[0]:
            expected = expected_pattern or "<single manifest file pattern>"
            errors.append(
                error(
                    relative_path,
                    "frontmatter must contain exactly one scalar applyTo value",
                    f"set frontmatter applyTo to {expected!r} in {relative_path}",
                )
            )
            continue
        apply_to = apply_to_values[0]
        if expected_pattern is None:
            errors.append(
                error(
                    relative_path,
                    f"frontmatter applyTo {apply_to!r} requires exactly one manifest "
                    "file_patterns value",
                    f"set file_patterns to [{apply_to!r}] for {relative_path}",
                )
            )
        elif apply_to != expected_pattern:
            errors.append(
                error(
                    relative_path,
                    f"frontmatter applyTo {apply_to!r} does not match manifest "
                    f"file_patterns value {expected_pattern!r}",
                    f"make applyTo and file_patterns both {expected_pattern!r}",
                )
            )
    return errors


def validate_adapters(root: Path, manifest: dict[str, object]) -> list[str]:
    errors: list[str] = []
    root = root.resolve()
    for filename in ("CLAUDE.md", "GEMINI.md"):
        path = root / filename
        try:
            present = os.path.lexists(path)
        except OSError as exc:
            errors.append(
                error(
                    filename,
                    f"cannot inspect public vendor root file: {exc}",
                    f"inspect and remove {filename}",
                )
            )
            continue
        if present:
            errors.append(
                error(
                    filename,
                    "public vendor root file is forbidden",
                    f"remove {filename} and route vendor tools through AGENTS.md",
                )
            )

    copilot_surface = next(
        (
            surface
            for surface in _declared_surfaces(manifest)
            if surface.get("id") == "copilot-adapter"
        ),
        None,
    )
    if copilot_surface is None:
        errors.append(
            error(
                ".github/copilot-instructions.md",
                "copilot-adapter surface is not declared",
                f"declare copilot-adapter in {MANIFEST_PATH}",
            )
        )
        return errors

    if not (
        copilot_surface.get("kind") == "adapter"
        and copilot_surface.get("authority") == "adapter-only"
        and copilot_surface.get("canonical_for") == []
    ):
        errors.append(
            error(
                MANIFEST_PATH,
                "copilot-adapter must be an adapter with adapter-only authority "
                "and an empty canonical_for list",
                "set copilot-adapter kind to adapter, authority to adapter-only, "
                "and canonical_for to []",
            )
        )

    relative_path = _surface_path(copilot_surface)
    if relative_path != ".github/copilot-instructions.md":
        errors.append(
            error(
                relative_path or MANIFEST_PATH,
                "copilot-adapter must use .github/copilot-instructions.md",
                "set the copilot-adapter path to .github/copilot-instructions.md",
            )
        )
        return errors

    path = root / relative_path
    try:
        if path.is_symlink() or not path.is_file():
            errors.append(
                error(
                    relative_path,
                    "copilot adapter must be a regular file, not a symlink",
                    f"replace {relative_path} with a regular file containing "
                    f"{COPILOT_ADAPTER!r}",
                )
            )
            return errors
        content = path.read_bytes()
    except OSError as exc:
        errors.append(
            error(
                relative_path,
                f"cannot read copilot adapter: {exc}",
                f"restore {relative_path} as a readable regular file",
            )
        )
        return errors

    if content != COPILOT_ADAPTER.encode("utf-8"):
        errors.append(
            error(
                relative_path,
                "content does not match exact template",
                f"replace the entire file with {COPILOT_ADAPTER!r}",
            )
        )
    return errors


def validate(root: Path) -> list[str]:
    root = root.resolve()
    manifest_path, manifest_path_errors = _validated_manifest_path(root)
    if manifest_path is None:
        return manifest_path_errors
    try:
        manifest = _load_manifest(manifest_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [
            error(
                ".github/instruction-surfaces.json",
                f"invalid JSON: {exc}",
                "repair .github/instruction-surfaces.json and rerun "
                "python3 scripts/validate-agent-policy.py",
            )
        ]

    errors: list[str] = []
    for validator in (
        validate_manifest,
        validate_public_references,
        validate_public_policy_size,
        validate_scoped_instructions,
        validate_adapters,
    ):
        errors.extend(validator(root, manifest))
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate public agent policy surfaces"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to the validator's repository)",
    )
    arguments = parser.parse_args()

    errors = validate(arguments.root)
    if errors:
        for message in errors:
            print(f"ERROR: {message}")
        return 1

    print("agent policy validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
