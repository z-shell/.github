#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
from datetime import date
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

POLICY_PATH = "lib/zsh-standard-policy.json"
INSTRUCTION_PATH = ".github/instructions/zsh-scripting.instructions.md"
MANIFEST_PATH = ".github/instruction-surfaces.json"
SHELL_DISPATCHER_PATH = ".github/instructions/shell.instructions.md"
SHELL_DISPATCHER_SHA256 = (
    "2c02e09c25047c6a16744e6b8be17afb8817ac67eb3a4a450d347bc88e8db8e3"
)
VALIDATOR_PATH = "scripts/validate-zsh-standard-policy.py"

TOP_LEVEL_KEYS = (
    "schema_version",
    "policy_id",
    "stable_release",
    "documentation_sources",
    "execution_profiles",
    "rule_model",
    "normative_rules",
    "source_classification",
)
STABLE_RELEASE_KEYS = (
    "version",
    "release_date",
    "manual_url",
    "release_notes_url",
    "semantic_review",
    "source_artifact",
)
PROFILE_IDS = (
    "standalone-executable",
    "startup-file",
    "sourced-library",
    "autoload-function",
    "test-fixture",
)
LEVELS = ("required", "recommended", "review")
BASES = ("language-semantics", "organization-policy", "mixed")
ENFORCEMENT_KINDS = (
    "native-syntax",
    "classifier",
    "lint",
    "runtime-test",
    "human-review",
)
RULE_KEYS = (
    "id",
    "level",
    "profiles",
    "minimum_zsh",
    "basis",
    "evidence",
    "enforcement",
)
NORMATIVE_RULE_IDS = (
    "zsh/authority/released-manual",
    "zsh/compatibility/respect-floor",
    "zsh/compatibility/annotate-version-sensitive",
    "zsh/context/classify",
    "zsh/context/select-profile",
    "zsh/context/no-cross-dialect-defaults",
    "zsh/review/report-without-rewrite",
    "zsh/change/conform-touched-code",
    "zsh/standalone/initialize",
    "zsh/standalone/no-startup-state",
    "zsh/sourced/preserve-caller-state",
    "zsh/autoload/initialize",
    "zsh/autoload/suppress-alias-expansion",
    "zsh/completion/preserve-trust-boundaries",
    "zsh/test/isolate-environment",
    "zsh/test/declare-negative-fixtures",
    "zsh/test/match-production-profile",
    "zsh/options/declare-correctness-state",
    "zsh/options/localize",
    "zsh/options/no-top-level-leak",
    "zsh/options/no-blanket-error-mode",
    "zsh/options/constrain-multios",
    "zsh/parameters/declare-scope",
    "zsh/parameters/account-dynamic-scope",
    "zsh/arrays/declare-kind",
    "zsh/arrays/native-indexing",
    "zsh/expansion/preserve-boundaries",
    "zsh/expansion/use-native-word-splitting",
    "zsh/quoting/quote-boundaries",
    "zsh/associative/deterministic-order",
    "zsh/patterns/declare-interpretation",
    "zsh/conditions/use-native-form",
    "zsh/conditions/declare-match-mode",
    "zsh/arithmetic/handle-zero-status",
    "zsh/arithmetic/validate-input",
    "zsh/arithmetic/declare-base",
    "zsh/status/check-critical",
    "zsh/status/check-pipeline-components",
    "zsh/status/preserve-command-substitution",
    "zsh/cleanup/scope-traps",
    "zsh/cleanup/use-always",
    "zsh/output/literal-vs-formatted",
    "zsh/input/raw-mode",
    "zsh/operands/end-options",
    "zsh/redirection/order-and-quote",
    "zsh/fd/close-allocated",
    "zsh/security/treat-strings-as-data",
    "zsh/security/no-unreviewed-reevaluation",
    "zsh/security/no-restricted-shell-sandbox",
    "zsh/security/trust-paths",
    "zsh/security/no-passive-network",
    "zsh/plugin/document-global-state",
    "zsh/plugin/restore-state",
    "zsh/documentation/comment-invariants",
    "zsh/documentation/track-deferred-work",
    "zsh/validation/native-authority",
    "zsh/validation/no-shellcheck",
    "zsh/validation/parser-gap",
    "zsh/formatting/no-unproven-rewrite",
)
RULE_ID = re.compile(r"^zsh/[a-z0-9-]+(?:/[a-z0-9-]+)+$")
VERSION = re.compile(r"^[0-9]+(?:\.[0-9]+)+$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")

DOCUMENTATION_SOURCES = {
    "manual-index": (
        "Zsh 5.9.2 Manual",
        "https://zsh.sourceforge.io/Doc/Release/index.html",
        "official-manual",
    ),
    "release-notes": (
        "Zsh Release Notes",
        "https://zsh.sourceforge.io/releases.html",
        "official-release-notes",
    ),
    "shell-grammar": (
        "Shell Grammar",
        "https://zsh.sourceforge.io/Doc/Release/Shell-Grammar.html",
        "official-manual",
    ),
    "redirection": (
        "Redirection",
        "https://zsh.sourceforge.io/Doc/Release/Redirection.html",
        "official-manual",
    ),
    "shell-builtins": (
        "Shell Builtin Commands",
        "https://zsh.sourceforge.io/Doc/Release/Shell-Builtin-Commands.html",
        "official-manual",
    ),
    "options": (
        "Options",
        "https://zsh.sourceforge.io/Doc/Release/Options.html",
        "official-manual",
    ),
    "parameters": (
        "Parameters",
        "https://zsh.sourceforge.io/Doc/Release/Parameters.html",
        "official-manual",
    ),
    "expansion": (
        "Expansion",
        "https://zsh.sourceforge.io/Doc/Release/Expansion.html",
        "official-manual",
    ),
    "conditional-expressions": (
        "Conditional Expressions",
        "https://zsh.sourceforge.io/Doc/Release/Conditional-Expressions.html",
        "official-manual",
    ),
    "arithmetic-evaluation": (
        "Arithmetic Evaluation",
        "https://zsh.sourceforge.io/Doc/Release/Arithmetic-Evaluation.html",
        "official-manual",
    ),
    "functions": (
        "Functions",
        "https://zsh.sourceforge.io/Doc/Release/Functions.html",
        "official-manual",
    ),
    "completion-system": (
        "Completion System",
        "https://zsh.sourceforge.io/Doc/Release/Completion-System.html",
        "official-manual",
    ),
    "restricted-shell": (
        "Restricted Shell",
        "https://zsh.sourceforge.io/Doc/Release/Restricted-Shell.html",
        "official-manual",
    ),
    "command-execution": (
        "Command Execution",
        "https://zsh.sourceforge.io/Doc/Release/Command-Execution.html",
        "official-manual",
    ),
}

EXPECTED_SOURCE_CLASSIFICATION = {
    "tracked_files_only": True,
    "nul_safe_output": True,
    "suffix_match": "longest",
    "suffixes": [
        {"value": ".plugin.zsh", "profile": "sourced-library"},
        {"value": ".zsh-theme", "profile": "sourced-library"},
        {"value": ".zunit", "profile": "test-fixture"},
        {"value": ".zsh", "profile": None},
    ],
    "startup_basenames": [
        {"value": ".zshenv", "profile": "startup-file"},
        {"value": ".zprofile", "profile": "startup-file"},
        {"value": ".zshrc", "profile": "startup-file"},
        {"value": ".zlogin", "profile": "startup-file"},
        {"value": ".zlogout", "profile": "startup-file"},
        {"value": "zshenv", "profile": "startup-file"},
        {"value": "zprofile", "profile": "startup-file"},
        {"value": "zshrc", "profile": "startup-file"},
        {"value": "zlogin", "profile": "startup-file"},
        {"value": "zlogout", "profile": "startup-file"},
    ],
    "directory_rules": [
        {
            "path_segment": "functions",
            "basename_prefix": None,
            "profile": "autoload-function",
        },
        {
            "path_segment": "completions",
            "basename_prefix": "_",
            "profile": "autoload-function",
        },
    ],
    "shebang": {
        "interpreter": "zsh",
        "direct": True,
        "env": True,
        "profile": "standalone-executable",
    },
    "exclusions": {
        "binary_files": True,
        "compiled_suffixes": [".zwc"],
        "generated_paths_source": "repository-config",
    },
    "resolution": {
        "explicit_override_precedence": "highest",
        "ambiguous_evidence": "error",
        "unassigned_profile": "error",
    },
    "path_globs": [
        "**/*.zsh",
        "**/*.plugin.zsh",
        "**/*.zsh-theme",
        "**/*.zunit",
        "**/.zshenv",
        "**/.zprofile",
        "**/.zshrc",
        "**/.zlogin",
        "**/.zlogout",
        "**/zshenv",
        "**/zprofile",
        "**/zshrc",
        "**/zlogin",
        "**/zlogout",
        "**/functions/**",
        "**/completions/**/_*",
    ],
    "repository_override_path": ".github/zsh-standard.json",
}
SOURCE_CLASSIFICATION_KEYS = tuple(EXPECTED_SOURCE_CLASSIFICATION)


class PolicyValidationError(ValueError):
    """A normalized policy input error suitable for a one-line diagnostic."""


def error(path: str, problem: str, fix: str) -> str:
    return f"{path}: {problem}; fix: {fix}"


def _safe_value(value: object) -> str:
    text = str(value)
    return "".join(
        character
        if 32 <= ord(character) < 127
        else f"\\x{ord(character):02x}"
        for character in text
    )


def _reject_duplicate_json_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise PolicyValidationError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_json_strict(path: Path) -> dict[str, object]:
    """Load one strict UTF-8 JSON object or raise PolicyValidationError."""

    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PolicyValidationError(f"cannot read JSON: {_safe_value(exc)}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PolicyValidationError(
            f"invalid UTF-8 at byte {exc.start}"
        ) from exc
    try:
        parsed = json.loads(text, object_pairs_hook=_reject_duplicate_json_keys)
    except PolicyValidationError:
        raise
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise PolicyValidationError(f"malformed JSON: {_safe_value(exc)}") from exc
    if not isinstance(parsed, dict):
        raise PolicyValidationError("JSON root must be an object")
    return cast(dict[str, object], parsed)


def _object(
    value: object,
    json_path: str,
    keys: tuple[str, ...],
    errors: list[str],
) -> dict[str, object] | None:
    if not isinstance(value, dict):
        errors.append(f"{json_path}: must be an object")
        return None
    actual = cast(dict[str, object], value)
    for key in actual:
        if key not in keys:
            errors.append(f"{json_path}.{_safe_value(key)}: unknown field")
    for key in keys:
        if key not in actual:
            errors.append(f"{json_path}.{key}: missing required field")
    return actual


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _official_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and hostname == "zsh.sourceforge.io"
        and not parsed.username
        and not parsed.password
    )


def _https_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and bool(hostname)
        and not parsed.username
        and not parsed.password
    )


def _valid_date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split("."))


def _string_array(
    value: object,
    json_path: str,
    errors: list[str],
) -> list[str] | None:
    if not isinstance(value, list) or not value:
        errors.append(f"{json_path}: must be a non-empty array")
        return None
    if not all(isinstance(item, str) and item for item in value):
        errors.append(f"{json_path}: every member must be a non-empty string")
        return None
    strings = cast(list[str], value)
    if len(strings) != len(set(strings)):
        errors.append(f"{json_path}: duplicate array member")
    return strings


def _validate_release(policy: dict[str, object], errors: list[str]) -> str | None:
    release = _object(
        policy.get("stable_release"),
        "$.stable_release",
        STABLE_RELEASE_KEYS,
        errors,
    )
    if release is None:
        return None

    version = release.get("version")
    if not isinstance(version, str) or VERSION.fullmatch(version) is None:
        errors.append(
            "$.stable_release.version: must be a dotted numeric released version"
        )
        valid_version = None
    else:
        valid_version = version

    if not _valid_date(release.get("release_date")):
        errors.append("$.stable_release.release_date: must be a valid ISO date")
    for field in ("manual_url", "release_notes_url"):
        if not _official_url(release.get(field)):
            errors.append(
                f"$.stable_release.{field}: must be an HTTPS official "
                "zsh.sourceforge.io URL"
            )

    review = _object(
        release.get("semantic_review"),
        "$.stable_release.semantic_review",
        ("date", "owner"),
        errors,
    )
    if review is not None:
        if not _valid_date(review.get("date")):
            errors.append(
                "$.stable_release.semantic_review.date: must be a valid ISO date"
            )
        if not _is_non_empty_string(review.get("owner")):
            errors.append(
                "$.stable_release.semantic_review.owner: must be a non-empty string"
            )

    artifact = release.get("source_artifact")
    if artifact is not None:
        artifact_object = _object(
            artifact,
            "$.stable_release.source_artifact",
            ("url", "sha256"),
            errors,
        )
        if artifact_object is not None:
            if not _https_url(artifact_object.get("url")):
                errors.append(
                    "$.stable_release.source_artifact.url: must be an HTTPS URL"
                )
            digest = artifact_object.get("sha256")
            if not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
                errors.append(
                    "$.stable_release.source_artifact.sha256: must be 64 "
                    "lowercase hexadecimal characters"
                )
    return valid_version


def _validate_documentation_sources(
    policy: dict[str, object],
    errors: list[str],
) -> set[str]:
    value = policy.get("documentation_sources")
    if not isinstance(value, dict):
        errors.append("$.documentation_sources: must be an object")
        return set()
    sources = cast(dict[str, object], value)
    expected_ids = tuple(DOCUMENTATION_SOURCES)
    if tuple(sources) != expected_ids:
        errors.append(
            "$.documentation_sources: evidence IDs must match the canonical "
            "ordered inventory"
        )
    for evidence_id in sources:
        if evidence_id not in DOCUMENTATION_SOURCES:
            errors.append(
                f"$.documentation_sources.{_safe_value(evidence_id)}: unknown field"
            )
    for evidence_id in expected_ids:
        if evidence_id not in sources:
            errors.append(
                f"$.documentation_sources.{evidence_id}: missing required field"
            )
            continue
        source = _object(
            sources[evidence_id],
            f"$.documentation_sources.{evidence_id}",
            ("title", "url", "kind"),
            errors,
        )
        if source is None:
            continue
        expected_title, expected_url, expected_kind = DOCUMENTATION_SOURCES[evidence_id]
        if source.get("title") != expected_title:
            errors.append(
                f"$.documentation_sources.{evidence_id}.title: must match the "
                "canonical evidence title"
            )
        if not _official_url(source.get("url")):
            errors.append(
                f"$.documentation_sources.{evidence_id}.url: evidence "
                f"{evidence_id} must use HTTPS under zsh.sourceforge.io"
            )
        elif source.get("url") != expected_url:
            errors.append(
                f"$.documentation_sources.{evidence_id}.url: must match the "
                "canonical official documentation URL"
            )
        if source.get("kind") != expected_kind:
            errors.append(
                f"$.documentation_sources.{evidence_id}.kind: must match the "
                "canonical evidence kind"
            )
    return set(sources).intersection(expected_ids)


def _validate_profiles(
    policy: dict[str, object],
    errors: list[str],
) -> set[str]:
    value = policy.get("execution_profiles")
    if not isinstance(value, dict):
        errors.append("$.execution_profiles: must be an object")
        return set()
    profiles = cast(dict[str, object], value)
    if tuple(profiles) != PROFILE_IDS:
        errors.append(
            "$.execution_profiles: keys must be exactly the five canonical "
            "profiles in order"
        )
    for profile_id in profiles:
        if profile_id not in PROFILE_IDS:
            errors.append(
                f"$.execution_profiles.{_safe_value(profile_id)}: unknown field"
            )
    for profile_id in PROFILE_IDS:
        if profile_id not in profiles:
            errors.append(f"$.execution_profiles.{profile_id}: missing required field")
            continue
        profile = _object(
            profiles[profile_id],
            f"$.execution_profiles.{profile_id}",
            ("title", "description"),
            errors,
        )
        if profile is not None:
            for field in ("title", "description"):
                if not _is_non_empty_string(profile.get(field)):
                    errors.append(
                        f"$.execution_profiles.{profile_id}.{field}: must be a "
                        "non-empty string"
                    )
    return set(profiles).intersection(PROFILE_IDS)


def _validate_rule_model(
    policy: dict[str, object],
    errors: list[str],
) -> None:
    model = _object(
        policy.get("rule_model"),
        "$.rule_model",
        ("levels", "bases", "enforcement_kinds"),
        errors,
    )
    if model is None:
        return
    expected = {
        "levels": list(LEVELS),
        "bases": list(BASES),
        "enforcement_kinds": list(ENFORCEMENT_KINDS),
    }
    for field, expected_value in expected.items():
        if model.get(field) != expected_value:
            errors.append(
                f"$.rule_model.{field}: must match the exact ordered enum array"
            )


def _validate_rules(
    policy: dict[str, object],
    profiles: set[str],
    evidence_ids: set[str],
    stable_version: str | None,
    errors: list[str],
) -> None:
    value = policy.get("normative_rules")
    if not isinstance(value, list) or not value:
        errors.append("$.normative_rules: must be a non-empty array")
        return
    rules = cast(list[object], value)
    rule_ids = tuple(
        rule.get("id") if isinstance(rule, dict) else None for rule in rules
    )
    if rule_ids != NORMATIVE_RULE_IDS:
        errors.append(
            "$.normative_rules: rule IDs must match the exact canonical ordered "
            "inventory"
        )
    seen_ids: set[str] = set()
    profile_order = {profile: index for index, profile in enumerate(PROFILE_IDS)}
    enforcement_order = {
        kind: index for index, kind in enumerate(ENFORCEMENT_KINDS)
    }
    for index, value_rule in enumerate(rules):
        path = f"$.normative_rules[{index}]"
        rule = _object(value_rule, path, RULE_KEYS, errors)
        if rule is None:
            continue
        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or RULE_ID.fullmatch(rule_id) is None:
            errors.append(f"{path}.id: must match the stable Zsh rule ID syntax")
        elif rule_id in seen_ids:
            errors.append(f"duplicate normative rule id {rule_id!r}")
        else:
            seen_ids.add(rule_id)

        if rule.get("level") not in LEVELS:
            errors.append(f"{path}.level: must be a declared rule level")
        if rule.get("basis") not in BASES:
            errors.append(f"{path}.basis: must be a declared rule basis")

        rule_profiles = _string_array(rule.get("profiles"), f"{path}.profiles", errors)
        if rule_profiles is not None:
            for profile in rule_profiles:
                if profile not in profiles:
                    errors.append(
                        f"{path}.profiles: unknown profile {_safe_value(profile)}"
                    )
            known_profiles = [
                profile for profile in rule_profiles if profile in profile_order
            ]
            if known_profiles != sorted(
                known_profiles, key=profile_order.__getitem__
            ):
                errors.append(
                    f"{path}.profiles: profiles must preserve canonical order"
                )

        minimum = rule.get("minimum_zsh")
        if minimum is not None:
            if not isinstance(minimum, str) or VERSION.fullmatch(minimum) is None:
                errors.append(
                    f"{path}.minimum_zsh: must be null or a dotted numeric version"
                )
            elif (
                stable_version is not None
                and _version_tuple(minimum) > _version_tuple(stable_version)
            ):
                errors.append(
                    f"{path}.minimum_zsh: cannot be newer than the stable release"
                )

        rule_evidence = _string_array(
            rule.get("evidence"),
            f"{path}.evidence",
            errors,
        )
        if rule_evidence is not None:
            for evidence_id in rule_evidence:
                if evidence_id not in evidence_ids:
                    errors.append(
                        f"{path}.evidence: unknown evidence "
                        f"{_safe_value(evidence_id)}"
                    )

        enforcement = _string_array(
            rule.get("enforcement"),
            f"{path}.enforcement",
            errors,
        )
        if enforcement is not None:
            for kind in enforcement:
                if kind not in ENFORCEMENT_KINDS:
                    errors.append(
                        f"{path}.enforcement: unknown enforcement kind "
                        f"{_safe_value(kind)}"
                    )
            known_kinds = [kind for kind in enforcement if kind in enforcement_order]
            if known_kinds != sorted(
                known_kinds, key=enforcement_order.__getitem__
            ):
                errors.append(
                    f"{path}.enforcement: kinds must preserve canonical order"
                )


def _validate_source_members(
    source: dict[str, object],
    profiles: set[str],
    errors: list[str],
) -> None:
    for field in ("tracked_files_only", "nul_safe_output"):
        if not isinstance(source.get(field), bool):
            errors.append(f"$.source_classification.{field}: must be a boolean")

    member_contracts = (
        ("suffixes", ("value", "profile")),
        ("startup_basenames", ("value", "profile")),
        ("directory_rules", ("path_segment", "basename_prefix", "profile")),
    )
    for field, keys in member_contracts:
        value = source.get(field)
        path = f"$.source_classification.{field}"
        if not isinstance(value, list):
            errors.append(f"{path}: must be an array")
            continue
        values_seen: set[str] = set()
        for index, member_value in enumerate(value):
            member = _object(member_value, f"{path}[{index}]", keys, errors)
            if member is None:
                continue
            identity_field = "value" if "value" in keys else "path_segment"
            identity = member.get(identity_field)
            if not isinstance(identity, str) or not identity:
                errors.append(
                    f"{path}[{index}].{identity_field}: must be a non-empty string"
                )
            elif identity in values_seen:
                errors.append(f"{path}: duplicate {identity_field} {identity!r}")
            else:
                values_seen.add(identity)
            profile = member.get("profile")
            if profile is not None and profile not in profiles:
                errors.append(
                    f"{path}[{index}].profile: unknown profile "
                    f"{_safe_value(profile)}"
                )
        if field == "suffixes" and ".sh" in values_seen:
            errors.append(f"{path}: .sh belongs to dialect dispatch, not Zsh suffixes")

    nested_contracts = (
        ("shebang", ("interpreter", "direct", "env", "profile")),
        (
            "exclusions",
            ("binary_files", "compiled_suffixes", "generated_paths_source"),
        ),
        (
            "resolution",
            (
                "explicit_override_precedence",
                "ambiguous_evidence",
                "unassigned_profile",
            ),
        ),
    )
    for field, keys in nested_contracts:
        _object(
            source.get(field),
            f"$.source_classification.{field}",
            keys,
            errors,
        )

    globs = source.get("path_globs")
    glob_strings = _string_array(
        globs,
        "$.source_classification.path_globs",
        errors,
    )
    if glob_strings is not None and any(
        glob == "**/*.sh" or glob.endswith("/*.sh") for glob in glob_strings
    ):
        errors.append(
            "$.source_classification.path_globs: .sh belongs to dialect dispatch"
        )


def _validate_source_classification(
    policy: dict[str, object],
    profiles: set[str],
    errors: list[str],
) -> None:
    source = _object(
        policy.get("source_classification"),
        "$.source_classification",
        SOURCE_CLASSIFICATION_KEYS,
        errors,
    )
    if source is None:
        return
    _validate_source_members(source, profiles, errors)
    for field, expected in EXPECTED_SOURCE_CLASSIFICATION.items():
        actual = source.get(field)
        if isinstance(expected, dict) and isinstance(actual, dict):
            for nested_field, nested_expected in expected.items():
                if actual.get(nested_field) != nested_expected:
                    errors.append(
                        f"$.source_classification.{field}.{nested_field}: must "
                        "match the exact ordered source-class contract"
                    )
            continue
        if actual != expected:
            suffix = (
                " and derive the canonical applyTo scalar"
                if field == "path_globs"
                else ""
            )
            errors.append(
                f"$.source_classification.{field}: must match the exact ordered "
                f"source-class contract{suffix}"
            )


def validate_policy_schema(policy: dict[str, object]) -> list[str]:
    """Return deterministic schema and cross-reference diagnostics."""

    errors: list[str] = []
    top = _object(policy, "$", TOP_LEVEL_KEYS, errors)
    if top is None:
        return sorted(errors)
    schema_version = top.get("schema_version")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != 1
    ):
        errors.append("$.schema_version: must be integer 1")
    if top.get("policy_id") != "z-shell-zsh-scripting-standard":
        errors.append(
            "$.policy_id: must be 'z-shell-zsh-scripting-standard'"
        )
    stable_version = _validate_release(top, errors)
    evidence_ids = _validate_documentation_sources(top, errors)
    profiles = _validate_profiles(top, errors)
    _validate_rule_model(top, errors)
    _validate_rules(top, profiles, evidence_ids, stable_version, errors)
    _validate_source_classification(top, profiles, errors)
    return sorted(errors)


def _contained_regular_path(
    root: Path,
    relative_path: str,
) -> tuple[Path | None, list[str]]:
    candidate = root / relative_path
    try:
        root_resolved = root.resolve(strict=True)
        status = candidate.lstat()
    except (OSError, RuntimeError, ValueError) as exc:
        return None, [
            error(
                relative_path,
                f"must exist as a contained regular file: {_safe_value(exc)}",
                f"restore a regular file at {relative_path}",
            )
        ]
    if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
        return None, [
            error(
                relative_path,
                "must be a contained regular file, not a symlink or special file",
                f"replace {relative_path} with a regular file inside the repository",
            )
        ]
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        return None, [
            error(
                relative_path,
                f"cannot resolve contained regular file: {_safe_value(exc)}",
                f"restore a regular file at {relative_path}",
            )
        ]
    if not resolved.is_relative_to(root_resolved):
        return None, [
            error(
                relative_path,
                "must be a contained regular file inside the repository",
                f"move {relative_path} inside the repository",
            )
        ]
    return resolved, []


def _read_text(root: Path, relative_path: str) -> tuple[str | None, list[str]]:
    path, errors = _contained_regular_path(root, relative_path)
    if path is None:
        return None, errors
    try:
        return path.read_text(encoding="utf-8"), []
    except UnicodeDecodeError as exc:
        return None, [
            error(
                relative_path,
                f"invalid UTF-8 at byte {exc.start}",
                f"encode {relative_path} as UTF-8",
            )
        ]
    except OSError as exc:
        return None, [
            error(
                relative_path,
                f"cannot read file: {_safe_value(exc)}",
                f"make {relative_path} readable",
            )
        ]


def _apply_to_values(text: str) -> list[str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return []
    try:
        closing = lines.index("---", 1)
    except ValueError:
        return []
    values: list[str] = []
    for line in lines[1:closing]:
        match = re.fullmatch(r'applyTo:\s*"([^"]*)"', line)
        if match:
            values.append(match.group(1))
        elif line.startswith("applyTo:"):
            values.append("")
    return values


def _visible_markdown_lines(text: str) -> list[tuple[int, str]]:
    """Return Markdown lines outside fenced code and HTML comments."""

    visible_lines: list[tuple[int, str]] = []
    in_comment = False
    fence_character: str | None = None
    fence_length = 0
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line
        visible_parts: list[str] = []
        contained_comment = False
        cursor = 0
        while cursor < len(line):
            if in_comment:
                comment_end = line.find("-->", cursor)
                contained_comment = True
                if comment_end == -1:
                    cursor = len(line)
                    break
                in_comment = False
                cursor = comment_end + len("-->")
                continue
            comment_start = line.find("<!--", cursor)
            if comment_start == -1:
                visible_parts.append(line[cursor:])
                cursor = len(line)
                break
            visible_parts.append(line[cursor:comment_start])
            contained_comment = True
            in_comment = True
            cursor = comment_start + len("<!--")

        visible_line = "".join(visible_parts)
        if contained_comment and visible_line.strip():
            visible_line = f"{visible_line} <html-comment>"
        stripped = visible_line.lstrip()
        if fence_character is not None:
            if re.fullmatch(
                rf"{re.escape(fence_character)}{{{fence_length},}}\s*",
                stripped,
            ):
                fence_character = None
                fence_length = 0
            continue
        fence_match = re.match(r"^(`{3,}|~{3,})", stripped)
        if fence_match is not None:
            fence_character = fence_match.group(1)[0]
            fence_length = len(fence_match.group(1))
            continue
        visible_lines.append((line_number, visible_line))
    return visible_lines


def _metadata_values(value: str) -> list[str] | None:
    if re.fullmatch(r"`[^`]+`(?:, `[^`]+`)*", value) is None:
        return None
    return re.findall(r"`([^`]+)`", value)


def _visible_markdown_rule_block(text: str, rule_id: str) -> str | None:
    lines = _visible_markdown_lines(text)
    heading = f"### `{rule_id}`"
    for index, (_, line) in enumerate(lines):
        if line != heading:
            continue
        block_lines = [line]
        for _, candidate in lines[index + 1 :]:
            if candidate.startswith("## ") or candidate.startswith("### "):
                break
            block_lines.append(candidate)
        return "\n".join(block_lines)
    return None


def _markdown_rules(
    text: str,
) -> tuple[list[dict[str, object]], list[str]]:
    lines = _visible_markdown_lines(text)
    heading = re.compile(r"^### `([^`]+)`$")
    h3_heading = re.compile(r"^###(?:\s|$)")
    metadata_names = (
        "Level",
        "Profiles",
        "Minimum Zsh",
        "Basis",
        "Evidence",
        "Enforcement",
    )
    parsed: list[dict[str, object]] = []
    errors: list[str] = []
    for line_number, line in lines:
        if h3_heading.match(line) and heading.fullmatch(line) is None:
            errors.append(f"malformed rule heading at line {line_number}")
    for index, (_, line) in enumerate(lines):
        match = heading.fullmatch(line)
        if match is None:
            continue
        rule_id = match.group(1)
        metadata: dict[str, list[str]] = {}
        cursor = index + 1
        while cursor < len(lines) and not lines[cursor][1].strip():
            cursor += 1
        for name in metadata_names:
            prefix = f"- {name}: "
            if cursor >= len(lines) or not lines[cursor][1].startswith(prefix):
                errors.append(f"{rule_id}: missing or reordered {name} metadata")
                break
            values = _metadata_values(lines[cursor][1][len(prefix) :])
            if values is None:
                errors.append(f"{rule_id}: noncanonical {name} metadata")
                break
            metadata[name] = values
            cursor += 1
        if len(metadata) != len(metadata_names):
            continue
        duplicate_cursor = cursor
        while duplicate_cursor < len(lines):
            candidate = lines[duplicate_cursor][1]
            if candidate.startswith("## ") or candidate.startswith("### "):
                break
            duplicate_match = re.match(
                r"- (Level|Profiles|Minimum Zsh|Basis|Evidence|Enforcement):",
                candidate,
            )
            if duplicate_match is not None:
                errors.append(
                    f"{rule_id}: duplicate {duplicate_match.group(1)} metadata"
                )
            duplicate_cursor += 1
        minimum_values = metadata["Minimum Zsh"]
        minimum: str | None | object
        if minimum_values == ["null"]:
            minimum = None
        elif len(minimum_values) == 1:
            minimum = minimum_values[0]
        else:
            minimum = object()
        parsed.append(
            {
                "id": rule_id,
                "level": metadata["Level"][0]
                if len(metadata["Level"]) == 1
                else object(),
                "profiles": metadata["Profiles"],
                "minimum_zsh": minimum,
                "basis": metadata["Basis"][0]
                if len(metadata["Basis"]) == 1
                else object(),
                "evidence": metadata["Evidence"],
                "enforcement": metadata["Enforcement"],
            }
        )
    return parsed, errors


def validate_instruction_contract(
    root: Path,
    policy: dict[str, object],
) -> list[str]:
    """Compare Zsh instruction frontmatter and rule metadata with policy."""

    text, errors = _read_text(root, INSTRUCTION_PATH)
    if text is None:
        return errors
    autoload_block = _visible_markdown_rule_block(
        text,
        "zsh/autoload/suppress-alias-expansion",
    )
    if autoload_block is not None and "`zcompile -U -z`" not in autoload_block:
        errors.append(
            error(
                INSTRUCTION_PATH,
                "missing required autoload compilation form `zcompile -U -z`",
                "compile autoload artifacts with alias suppression and Zsh "
                "file style",
            )
        )
    source = policy.get("source_classification")
    rules = policy.get("normative_rules")
    if not isinstance(source, dict) or not isinstance(source.get("path_globs"), list):
        return errors
    expected_apply_to = ",".join(
        item for item in source["path_globs"] if isinstance(item, str)
    )
    apply_to = _apply_to_values(text)
    if len(apply_to) != 1:
        errors.append(
            error(
                INSTRUCTION_PATH,
                "frontmatter must contain exactly one scalar applyTo",
                "keep one quoted applyTo scalar derived from the policy path_globs",
            )
        )
    elif apply_to[0] != expected_apply_to:
        errors.append(
            error(
                INSTRUCTION_PATH,
                "applyTo does not match policy source-classification globs",
                "copy the comma-joined policy path_globs into applyTo",
            )
        )

    parsed_rules, parsing_errors = _markdown_rules(text)
    for parsing_error in parsing_errors:
        errors.append(
            error(
                INSTRUCTION_PATH,
                parsing_error,
                "restore all six ordered metadata lines beneath the rule heading",
            )
        )
    if not isinstance(rules, list):
        return errors
    if len(parsed_rules) != len(rules):
        errors.append(
            error(
                INSTRUCTION_PATH,
                "Markdown rules must match policy normative_rules one-to-one",
                "add or remove rule blocks so the inventories have equal length",
            )
        )
    field_labels = {
        "id": "ID",
        "level": "Level",
        "profiles": "Profiles",
        "minimum_zsh": "Minimum Zsh",
        "basis": "Basis",
        "evidence": "Evidence",
        "enforcement": "Enforcement",
    }
    for index, (markdown_rule, policy_rule_value) in enumerate(
        zip(parsed_rules, rules)
    ):
        if not isinstance(policy_rule_value, dict):
            continue
        policy_rule = cast(dict[str, object], policy_rule_value)
        rule_id = str(policy_rule.get("id", f"rule[{index}]"))
        for field, label in field_labels.items():
            if markdown_rule.get(field) != policy_rule.get(field):
                errors.append(
                    error(
                        INSTRUCTION_PATH,
                        f"{label} metadata drift for {rule_id}",
                        f"make the Markdown {label} match the policy rule",
                    )
                )
    return errors


def _expected_manifest_surfaces(apply_to: str) -> dict[str, dict[str, object]]:
    return {
        "instruction-shell-dialect-dispatch": {
            "id": "instruction-shell-dialect-dispatch",
            "path": SHELL_DISPATCHER_PATH,
            "kind": "scoped-guidance",
            "authority": "canonical-detail",
            "consumers": ["codex", "claude-code", "copilot", "human"],
            "tasks": ["shell"],
            "file_patterns": ["**/*.sh"],
            "required": True,
            "review_owner": "z-shell maintainers",
            "canonical_for": ["shell-dialect-dispatch"],
        },
        "instruction-zsh-scripting": {
            "id": "instruction-zsh-scripting",
            "path": INSTRUCTION_PATH,
            "kind": "scoped-guidance",
            "authority": "canonical-detail",
            "consumers": ["codex", "claude-code", "copilot", "human"],
            "tasks": ["all"],
            "file_patterns": [apply_to],
            "required": True,
            "review_owner": "z-shell maintainers",
            "canonical_for": ["zsh-scripting"],
        },
        "zsh-standard-policy": {
            "id": "zsh-standard-policy",
            "path": POLICY_PATH,
            "kind": "enforcement",
            "authority": "canonical-detail",
            "consumers": ["codex", "claude-code", "copilot", "human", "ci"],
            "tasks": ["instruction-change", "zsh-standard"],
            "file_patterns": ["**"],
            "required": True,
            "review_owner": "z-shell maintainers",
            "canonical_for": [
                "zsh-release-metadata",
                "zsh-rule-metadata",
                "zsh-source-classification",
            ],
        },
        "zsh-standard-validator": {
            "id": "zsh-standard-validator",
            "path": VALIDATOR_PATH,
            "kind": "enforcement",
            "authority": "canonical-detail",
            "consumers": ["human", "ci"],
            "tasks": ["instruction-change", "zsh-standard-validation"],
            "file_patterns": ["**"],
            "required": True,
            "review_owner": "z-shell maintainers",
            "canonical_for": ["zsh-standard-validation"],
        },
    }


def validate_manifest_contract(
    root: Path,
    policy: dict[str, object],
) -> list[str]:
    """Compare exact routing and ownership surfaces with the policy."""

    manifest_path, errors = _contained_regular_path(root, MANIFEST_PATH)
    if manifest_path is None:
        return errors
    try:
        manifest = load_json_strict(manifest_path)
    except PolicyValidationError as exc:
        return [
            error(
                MANIFEST_PATH,
                str(exc),
                "restore a unique-key UTF-8 JSON manifest",
            )
        ]
    source = policy.get("source_classification")
    if not isinstance(source, dict) or not isinstance(source.get("path_globs"), list):
        return errors
    apply_to = ",".join(
        item for item in source["path_globs"] if isinstance(item, str)
    )
    surface_values = manifest.get("surfaces")
    if not isinstance(surface_values, list):
        return [
            error(
                MANIFEST_PATH,
                "surfaces must be an array",
                "restore the public surface inventory",
            )
        ]
    expected_surfaces = _expected_manifest_surfaces(apply_to)
    surfaces: dict[str, list[dict[str, object]]] = {}
    surface_items: list[dict[str, object]] = []
    for item in surface_values:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            surface = cast(dict[str, object], item)
            surface_items.append(surface)
            surfaces.setdefault(cast(str, surface["id"]), []).append(surface)
    canonical_paths = {
        cast(str, expected["path"]): surface_id
        for surface_id, expected in expected_surfaces.items()
    }
    canonical_owners = {
        owner: surface_id
        for surface_id, expected in expected_surfaces.items()
        for owner in cast(list[str], expected["canonical_for"])
    }
    for surface in surface_items:
        surface_id = cast(str, surface["id"])
        if surface_id == "instruction-shell":
            errors.append(
                error(
                    MANIFEST_PATH,
                    "legacy surface id 'instruction-shell' aliases the shell "
                    "dispatcher",
                    "remove the legacy alias and keep "
                    "instruction-shell-dialect-dispatch",
                )
            )
        if surface_id in expected_surfaces:
            continue
        surface_path = surface.get("path")
        if isinstance(surface_path, str) and surface_path in canonical_paths:
            errors.append(
                error(
                    MANIFEST_PATH,
                    f"extra surface {_safe_value(surface_id)!r} reuses canonical "
                    f"contract path {_safe_value(surface_path)!r}",
                    f"leave that path exclusively owned by "
                    f"{canonical_paths[surface_path]!r}",
                )
            )
        file_patterns = surface.get("file_patterns")
        if isinstance(file_patterns, list) and apply_to in file_patterns:
            errors.append(
                error(
                    MANIFEST_PATH,
                    f"extra surface {_safe_value(surface_id)!r} reuses canonical "
                    "Zsh file_patterns",
                    "leave the policy-derived Zsh pattern on instruction-zsh-scripting",
                )
            )
        owners = surface.get("canonical_for")
        if isinstance(owners, list):
            for owner in owners:
                if isinstance(owner, str) and owner in canonical_owners:
                    errors.append(
                        error(
                            MANIFEST_PATH,
                            f"extra surface {_safe_value(surface_id)!r} reuses "
                            f"canonical ownership value {_safe_value(owner)!r}",
                            f"leave that value exclusively owned by "
                            f"{canonical_owners[owner]!r}",
                        )
                    )
    for owner, expected_owner in canonical_owners.items():
        actual_owners = [
            cast(str, surface["id"])
            for surface in surface_items
            if isinstance(surface.get("canonical_for"), list)
            and owner in cast(list[object], surface["canonical_for"])
        ]
        if len(actual_owners) > 1:
            errors.append(
                error(
                    MANIFEST_PATH,
                    f"canonical ownership value {_safe_value(owner)!r} has duplicate "
                    f"owners {_safe_value(actual_owners)!r}",
                    f"leave it exclusively owned by {expected_owner!r}",
                )
            )
    for surface_id, expected in expected_surfaces.items():
        matches = surfaces.get(surface_id, [])
        if len(matches) != 1:
            errors.append(
                error(
                    MANIFEST_PATH,
                    f"surface {surface_id!r} must appear exactly once",
                    f"keep one exact {surface_id!r} surface",
                )
            )
            continue
        actual = matches[0]
        if (
            surface_id == "instruction-zsh-scripting"
            and actual.get("file_patterns") != [apply_to]
        ):
            errors.append(
                error(
                    MANIFEST_PATH,
                    "instruction-zsh-scripting applyTo file_patterns drift",
                    "use one file_patterns string equal to policy path_globs",
                )
            )
        for field, expected_value in expected.items():
            if actual.get(field) != expected_value and not (
                surface_id == "instruction-zsh-scripting"
                and field == "file_patterns"
            ):
                errors.append(
                    error(
                        MANIFEST_PATH,
                        f"{surface_id}.{field} does not match canonical ownership",
                        f"restore the exact {surface_id}.{field} value",
                    )
                )
        unknown = set(actual).difference(expected)
        for field in sorted(unknown):
            errors.append(
                error(
                    MANIFEST_PATH,
                    f"{surface_id}.{field} is not part of the scoped surface",
                    f"remove {surface_id}.{field}",
                )
            )
    return errors


def validate_shell_dispatcher(root: Path) -> list[str]:
    """Enforce the exact reviewed shell-dialect dispatcher content."""

    text, errors = _read_text(root, SHELL_DISPATCHER_PATH)
    if text is None:
        return errors
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
    actual_digest = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    if actual_digest != SHELL_DISPATCHER_SHA256:
        errors.append(
            error(
                SHELL_DISPATCHER_PATH,
                "canonical dispatcher content digest mismatch; expected "
                f"sha256:{SHELL_DISPATCHER_SHA256}, got sha256:{actual_digest}",
                "restore the approved dispatcher, or after policy review "
                "update SHELL_DISPATCHER_SHA256 for the exact reviewed text",
            )
        )
    return errors


def validate_consumer_contract(
    root: Path,
    policy: dict[str, object],
) -> list[str]:
    """Task 5 extension point for advisory consumer ownership checks."""

    del root, policy
    return []


def validate(root: Path) -> list[str]:
    """Compose active validators, sort diagnostics, and never raise on input."""

    errors: list[str] = []
    try:
        root_path = Path(root)
        policy_path, path_errors = _contained_regular_path(root_path, POLICY_PATH)
        errors.extend(path_errors)
        policy: dict[str, object] | None = None
        if policy_path is not None:
            try:
                policy = load_json_strict(policy_path)
            except PolicyValidationError as exc:
                errors.append(
                    error(
                        POLICY_PATH,
                        str(exc),
                        "restore a unique-key UTF-8 JSON policy object",
                    )
                )
        if policy is not None:
            for schema_error in validate_policy_schema(policy):
                errors.append(
                    error(
                        POLICY_PATH,
                        schema_error,
                        "restore the canonical policy schema and metadata",
                    )
                )
            errors.extend(validate_instruction_contract(root_path, policy))
            errors.extend(validate_manifest_contract(root_path, policy))
            errors.extend(validate_consumer_contract(root_path, policy))
        errors.extend(validate_shell_dispatcher(root_path))
    except Exception as exc:  # Defensive boundary for user-controlled files and roots.
        errors.append(
            error(
                POLICY_PATH,
                f"validation could not inspect repository input: {_safe_value(exc)}",
                "restore readable contained contract files and retry",
            )
        )
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the canonical Zsh policy")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="repository root to validate",
    )
    arguments = parser.parse_args()
    errors = validate(arguments.root)
    if errors:
        for message in errors:
            print(f"ERROR: {message}")
        return 1
    print("zsh standard policy validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
