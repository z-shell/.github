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
from typing import NamedTuple, cast
from urllib.parse import urlparse

POLICY_PATH = "lib/zsh-standard-policy.json"
INSTRUCTION_PATH = ".github/instructions/zsh-scripting.instructions.md"
MANIFEST_PATH = ".github/instruction-surfaces.json"
SHELL_DISPATCHER_PATH = ".github/instructions/shell.instructions.md"
SHELL_DISPATCHER_SHA256 = (
    "2c02e09c25047c6a16744e6b8be17afb8817ac67eb3a4a450d347bc88e8db8e3"
)
VALIDATOR_PATH = "scripts/validate-zsh-standard-policy.py"
ADVISORY_CONSUMER_PATHS = (
    ".github/agents/zsh-plugin-standard-reviewer.agent.md",
    ".github/skills/new-zsh-plugin/SKILL.md",
    ".github/skills/zunit-test/SKILL.md",
)
REFERENCE_CONSUMER_PATHS = ADVISORY_CONSUMER_PATHS + (
    "PATTERNS.md",
    ".github/README.md",
)
PLUGIN_TEMPLATE_PATH = (
    ".github/skills/new-zsh-plugin/templates/plugin.plugin.zsh"
)
RETIRED_PATTERN_SECTIONS = {
    "Plugin entry-point skeleton": {
        "evidence": (
            "z-shell/zsh-eza:zsh-eza.plugin.zsh",
            "z-shell/zsh-fancy-completions:zsh-fancy-completions.plugin.zsh",
            "z-shell/z-a-meta-plugins:z-a-meta-plugins.plugin.zsh",
        ),
        "rules": (
            "zsh/context/select-profile",
            "zsh/sourced/preserve-caller-state",
        ),
    },
    "Register the repository directory in `Plugins`": {
        "evidence": (
            "z-shell/zsh-eza:zsh-eza.plugin.zsh",
            "z-shell/zsh-fancy-completions:zsh-fancy-completions.plugin.zsh",
            "z-shell/z-a-meta-plugins:z-a-meta-plugins.plugin.zsh",
        ),
        "rules": (
            "zsh/plugin/document-global-state",
            "zsh/plugin/restore-state",
        ),
    },
    "Guard `fpath` additions": {
        "evidence": (
            "z-shell/zsh-fancy-completions:zsh-fancy-completions.plugin.zsh",
            "z-shell/z-a-meta-plugins:z-a-meta-plugins.plugin.zsh",
            "z-shell/zsh-eza:zsh-eza.plugin.zsh",
        ),
        "rules": (
            "zsh/security/trust-paths",
            "zsh/plugin/restore-state",
        ),
    },
}

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
EXECUTION_PROFILE_METADATA = {
    "standalone-executable": (
        "Standalone executable",
        "A directly invoked Zsh program that owns its initial shell state.",
    ),
    "startup-file": (
        "Startup file",
        "A Zsh startup or shutdown file read for a defined shell lifecycle "
        "phase that may make phase-owned effects.",
    ),
    "sourced-library": (
        "Sourced library",
        "A plugin or library loaded into and required to preserve caller state.",
    ),
    "autoload-function": (
        "Autoload function",
        "A function body loaded through Zsh autoload, including completions.",
    ),
    "test-fixture": (
        "Test fixture",
        "A Zsh test or fixture evaluated under an explicit production profile.",
    ),
}
PROFILE_IDS = tuple(EXECUTION_PROFILE_METADATA)
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
STARTUP_PROFILE_RULE_IDS = (
    "zsh/authority/released-manual",
    "zsh/compatibility/respect-floor",
    "zsh/compatibility/annotate-version-sensitive",
    "zsh/context/classify",
    "zsh/context/select-profile",
    "zsh/context/no-cross-dialect-defaults",
    "zsh/review/report-without-rewrite",
    "zsh/change/conform-touched-code",
    "zsh/completion/preserve-trust-boundaries",
    "zsh/options/declare-correctness-state",
    "zsh/options/localize",
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
    "zsh/documentation/comment-invariants",
    "zsh/documentation/track-deferred-work",
    "zsh/validation/native-authority",
    "zsh/validation/no-shellcheck",
    "zsh/validation/parser-gap",
    "zsh/formatting/no-unproven-rewrite",
)
TRUST_PATH_EVIDENCE = (
    "command-execution",
    "shell-builtins",
    "functions",
    "completion-system",
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
            expected_title, expected_description = EXECUTION_PROFILE_METADATA[
                profile_id
            ]
            if profile.get("title") != expected_title:
                errors.append(
                    f"$.execution_profiles.{profile_id}.title: must match the "
                    "canonical profile title"
                )
            if profile.get("description") != expected_description:
                errors.append(
                    f"$.execution_profiles.{profile_id}.description: must "
                    "match the canonical profile description"
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
    startup_memberships = tuple(
        rule.get("id")
        for rule in rules
        if isinstance(rule, dict)
        and isinstance(rule.get("profiles"), list)
        and "startup-file" in rule["profiles"]
    )
    if startup_memberships != STARTUP_PROFILE_RULE_IDS:
        errors.append(
            "$.normative_rules: startup-file memberships must match the exact "
            "canonical ordered rule inventory"
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
        if rule_id == "zsh/security/trust-paths" and tuple(
            rule_evidence or ()
        ) != TRUST_PATH_EVIDENCE:
            errors.append(
                f"{path}.evidence for zsh/security/trust-paths: must match "
                "the exact canonical trust-path evidence"
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


def _markdown_container_view(
    line: str,
    *,
    work: list[int] | None = None,
    include_lists: bool = True,
) -> tuple[str, tuple[tuple[str, int], ...]]:
    """Return content after supported containers using linear cursor work."""

    expanded = line.expandtabs(4)
    if work is not None:
        work[0] += len(line) + len(expanded)
    return _markdown_container_view_from_expanded(
        expanded,
        0,
        work=work,
        include_lists=include_lists,
    )


def _markdown_container_view_from_expanded(
    expanded: str,
    start: int,
    *,
    work: list[int] | None = None,
    include_lists: bool = True,
) -> tuple[str, tuple[tuple[str, int], ...]]:
    """Parse containers from one shared tab-expanded source buffer."""

    cursor = start
    containers: list[tuple[str, int]] = []

    def advance(amount: int = 1) -> None:
        nonlocal cursor
        cursor += amount
        if work is not None:
            work[0] += amount

    while cursor < len(expanded):
        container_start = cursor
        indentation = 0
        while indentation < 4 and cursor < len(expanded) and expanded[cursor] == " ":
            advance()
            indentation += 1
        if indentation == 4:
            cursor = container_start
            break
        if cursor >= len(expanded):
            break

        if cursor < len(expanded) and expanded[cursor] == ">":
            advance()
            if cursor < len(expanded) and expanded[cursor] == " ":
                advance()
            containers.append(("blockquote", 0))
            continue

        if not include_lists:
            cursor = container_start
            break

        marker_end = cursor
        if expanded[cursor] in "-+*":
            marker_end += 1
        elif expanded[cursor].isdigit():
            digit_start = cursor
            while (
                marker_end < len(expanded)
                and marker_end - digit_start < 10
                and expanded[marker_end].isdigit()
            ):
                marker_end += 1
            if (
                not 1 <= marker_end - digit_start <= 9
                or marker_end >= len(expanded)
                or expanded[marker_end] not in ".)"
            ):
                cursor = container_start
                break
            marker_end += 1
        else:
            cursor = container_start
            break

        if marker_end == len(expanded):
            advance(marker_end - cursor)
            containers.append(("list", marker_end - container_start + 1))
            continue

        spacing_end = marker_end
        while (
            spacing_end < len(expanded)
            and expanded[spacing_end] == " "
            and spacing_end - marker_end < 5
        ):
            spacing_end += 1
        spacing = spacing_end - marker_end
        if not 1 <= spacing <= 4 or (
            spacing_end < len(expanded) and expanded[spacing_end] == " "
        ):
            cursor = container_start
            break
        advance(spacing_end - cursor)
        containers.append(("list", cursor - container_start))

    content = expanded[cursor:]
    if work is not None:
        work[0] += len(content)
    return content, tuple(containers)


def _replayed_markdown_prefixes(
    line: str,
    containers: tuple[tuple[str, int], ...],
    *,
    work: list[int] | None = None,
) -> tuple[str, tuple[int, ...]]:
    """Replay recorded containers once and return each matched cursor."""

    expanded = line.expandtabs(4)
    if work is not None:
        work[0] += len(line) + len(expanded)
    cursor = 0
    matched_cursors: list[int] = []
    for kind, width in containers:
        if kind == "list":
            if not expanded.startswith(" " * width, cursor):
                break
            cursor += width
            if work is not None:
                work[0] += width
        else:
            indentation = 0
            while (
                indentation < 4 and cursor < len(expanded) and expanded[cursor] == " "
            ):
                cursor += 1
                indentation += 1
                if work is not None:
                    work[0] += 1
            if indentation == 4 or cursor >= len(expanded) or expanded[cursor] != ">":
                break
            cursor += 1
            if work is not None:
                work[0] += 1
            if cursor < len(expanded) and expanded[cursor] == " ":
                cursor += 1
                if work is not None:
                    work[0] += 1
        matched_cursors.append(cursor)
    return expanded, tuple(matched_cursors)


def _replay_markdown_containers(
    line: str,
    containers: tuple[tuple[str, int], ...],
    *,
    work: list[int] | None = None,
) -> str | None:
    """Return a continuation view for an exact recorded container stack."""

    expanded, matched_cursors = _replayed_markdown_prefixes(
        line,
        containers,
        work=work,
    )
    if len(matched_cursors) != len(containers):
        return None
    cursor = matched_cursors[-1] if matched_cursors else 0
    content = expanded[cursor:]
    if work is not None:
        work[0] += len(content)
    return content


def _resolve_markdown_container_view(
    line: str,
    active_containers: tuple[tuple[str, int], ...] = (),
    *,
    work: list[int] | None = None,
) -> tuple[str, tuple[tuple[str, int], ...]]:
    """Resolve active list continuations, then any explicit nested containers."""

    if not active_containers:
        return _markdown_container_view(line, work=work)
    expanded, matched_cursors = _replayed_markdown_prefixes(
        line,
        active_containers,
        work=work,
    )
    prefix_length = len(matched_cursors)
    prefix = active_containers[:prefix_length]
    if prefix and any(kind == "list" for kind, _ in prefix):
        content, nested = _markdown_container_view_from_expanded(
            expanded,
            matched_cursors[-1],
            work=work,
        )
        return content, prefix + nested
    return _markdown_container_view(line, work=work)


def _fence_container_content(
    line: str,
    containers: tuple[tuple[str, int], ...],
    *,
    work: list[int] | None = None,
) -> str | None:
    """Strip the container prefixes recorded by a fenced block opener."""

    return _replay_markdown_containers(line, containers, work=work)


def _fence_opener(content: str) -> tuple[str, int] | None:
    match = re.match(
        r"^ {0,3}(?P<marker>`{3,}|~{3,})(?P<info>.*)$",
        content,
    )
    if match is None:
        return None
    marker = match.group("marker")
    info = match.group("info")
    if marker[0] == "`" and "`" in info:
        return None
    return marker[0], len(marker)


def _fence_closer(content: str, marker: str, minimum: int) -> bool:
    return (
        re.fullmatch(
            rf" {{0,3}}{re.escape(marker)}{{{minimum},}}[ \t]*",
            content,
        )
        is not None
    )


class _MarkdownLineContext(NamedTuple):
    line_number: int
    raw_line: str
    content: str
    containers: tuple[tuple[str, int], ...]
    source_gap: bool


def _scan_visible_markdown(
    text: str,
) -> tuple[list[tuple[int, str]], list[_MarkdownLineContext]]:
    """Scan visibility and container ownership in one source-order pass."""

    visible_lines: list[tuple[int, str]] = []
    contextual: list[_MarkdownLineContext] = []
    in_comment = False
    fence_character: str | None = None
    fence_length = 0
    fence_containers: tuple[tuple[str, int], ...] = ()
    html_active = False
    html_blank_terminated = False
    html_end_pattern: re.Pattern[str] | None = None
    html_containers: tuple[tuple[str, int], ...] = ()
    active_containers: tuple[tuple[str, int], ...] = ()
    paragraph_context: tuple[tuple[str, int], ...] | None = None
    blank_lines = 0
    previous_visible_line_number: int | None = None
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if fence_character is not None:
            candidate = _fence_container_content(
                raw_line,
                fence_containers,
            )
            if (
                candidate is None
                and fence_containers
                and (
                    raw_line.strip()
                    or any(kind == "blockquote" for kind, _ in fence_containers)
                )
            ):
                fence_character = None
                fence_length = 0
                fence_containers = ()
            else:
                if candidate is not None and _fence_closer(
                    candidate,
                    fence_character,
                    fence_length,
                ):
                    fence_character = None
                    fence_length = 0
                    fence_containers = ()
                continue

        raw_view, _ = _resolve_markdown_container_view(
            raw_line,
            active_containers,
        )
        starts_html_comment = (
            not html_active
            and not in_comment
            and _leading_indentation_columns(raw_view) <= 3
            and raw_view.lstrip(" \t").startswith("<!--")
        )
        line = raw_line
        visible_parts: list[str] = []
        contained_comment = False
        cursor = 0
        while (
            cursor < len(line)
            and not html_active
            and not starts_html_comment
        ):
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

        visible_line = (
            raw_line
            if html_active or starts_html_comment
            else "".join(visible_parts)
        )
        if contained_comment and visible_line.strip():
            visible_line = f"{visible_line} <html-comment>"
        fence_view, containers = _resolve_markdown_container_view(
            visible_line,
            active_containers,
        )
        if html_active:
            html_content = _fence_container_content(
                raw_line,
                html_containers,
            )
            if html_content is not None:
                fence_view = html_content
                containers = html_containers
        html_line = False
        if html_active:
            if containers != html_containers:
                html_active = False
                html_blank_terminated = False
                html_end_pattern = None
                html_containers = ()
            elif html_blank_terminated:
                if fence_view.strip():
                    html_line = True
                else:
                    html_active = False
                    html_blank_terminated = False
                    html_containers = ()
            else:
                html_line = True
                if (
                    html_end_pattern is not None
                    and html_end_pattern.search(fence_view)
                ):
                    html_active = False
                    html_end_pattern = None
                    html_containers = ()

        if not html_line:
            html_end = _html_block_end_pattern(
                fence_view,
                allow_type_7=paragraph_context is None,
            )
            if html_end is not None:
                html_line = True
                html_containers = containers
                if html_end is False:
                    html_active = True
                    html_blank_terminated = True
                elif not html_end.search(fence_view):
                    html_active = True
                    html_end_pattern = html_end

        if not html_line:
            opener = _fence_opener(fence_view)
            if opener is not None:
                fence_character, fence_length = opener
                fence_containers = containers
                paragraph_context = None
                if any(kind == "list" for kind, _ in containers):
                    active_containers = containers
                else:
                    active_containers = ()
                blank_lines = 0
                continue
        visible_lines.append((line_number, visible_line))
        source_gap = (
            previous_visible_line_number is not None
            and line_number != previous_visible_line_number + 1
        )
        contextual.append(
            _MarkdownLineContext(
                line_number,
                visible_line,
                fence_view,
                containers,
                source_gap,
            )
        )
        previous_visible_line_number = line_number
        if source_gap:
            paragraph_context = None
        if not fence_view.strip():
            paragraph_context = None
            if visible_line.strip() and any(
                kind == "list" for kind, _ in containers
            ):
                blank_lines = 0
                active_containers = containers
            else:
                blank_lines += 1
                if blank_lines >= 2:
                    active_containers = ()
            continue
        blank_lines = 0
        if html_line:
            paragraph_context = None
        else:
            indentation = _leading_indentation_columns(fence_view)
            if indentation >= 4 and paragraph_context != containers:
                paragraph_context = None
            elif _starts_markdown_paragraph(fence_view[indentation:]):
                paragraph_context = containers
            else:
                paragraph_context = None
        if any(kind == "list" for kind, _ in containers):
            active_containers = containers
        else:
            active_containers = ()
    return visible_lines, contextual


def _visible_markdown_lines(text: str) -> list[tuple[int, str]]:
    """Return Markdown lines outside fenced code and HTML comments."""

    return _scan_visible_markdown(text)[0]


def _visible_markdown_contexts(text: str) -> list[_MarkdownLineContext]:
    """Return visible lines with source-accurate container ownership."""

    return _scan_visible_markdown(text)[1]


def _strip_blockquote_prefixes(line: str) -> tuple[int, str]:
    """Return blockquote depth and content for one visible Markdown line."""

    content, containers = _markdown_container_view(
        line,
        include_lists=False,
    )
    return len(containers), content


def _leading_indentation_columns(line: str) -> int:
    """Count leading Markdown indentation columns with four-column tabs."""

    columns = 0
    for character in line:
        if character == " ":
            columns += 1
        elif character == "\t":
            columns += 4 - (columns % 4)
        else:
            break
    return columns


def _contextual_markdown_lines(
    lines: list[tuple[int, str]],
) -> list[_MarkdownLineContext]:
    """Resolve containers without changing the compatible visible-line API."""

    contextual: list[_MarkdownLineContext] = []
    active_containers: tuple[tuple[str, int], ...] = ()
    previous_line_number: int | None = None
    blank_lines = 0
    for line_number, raw_line in lines:
        source_gap = (
            previous_line_number is not None
            and line_number != previous_line_number + 1
        )
        if source_gap:
            active_containers = ()
        visible_line = raw_line.removesuffix(" <html-comment>")
        content, containers = _resolve_markdown_container_view(
            visible_line,
            active_containers,
        )
        contextual.append(
            _MarkdownLineContext(
                line_number,
                raw_line,
                content,
                containers,
                source_gap,
            )
        )
        previous_line_number = line_number
        if not content.strip():
            if visible_line.strip() and any(
                kind == "list" for kind, _ in containers
            ):
                blank_lines = 0
                active_containers = containers
            else:
                blank_lines += 1
                if blank_lines >= 2:
                    active_containers = ()
            continue
        blank_lines = 0
        if any(kind == "list" for kind, _ in containers):
            active_containers = containers
        else:
            active_containers = ()
    return contextual


def _starts_markdown_paragraph(content: str) -> bool:
    """Return whether visible container content can open a paragraph."""

    stripped = content.strip()
    if not stripped or re.match(r"^#{1,6}(?:[ \t]+|$)", stripped):
        return False
    if re.fullmatch(
        r"(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,}",
        stripped,
    ):
        return False
    if re.fullmatch(r"(?:=+|-+)[ \t]*", stripped):
        return False
    if re.match(r"^\[[^\]\r\n]+\]:[ \t]*(?:\S|$)", stripped):
        return False
    return True


HTML_RAW_END = re.compile(
    r"</(?:pre|script|style|textarea)>",
    re.IGNORECASE,
)
HTML_COMMENT_END = re.compile(r"-->")
HTML_TYPE_6_START = re.compile(
    r"^</?(?:address|article|aside|base|basefont|blockquote|body|caption|center|"
    r"col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|"
    r"footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|"
    r"link|main|menu|menuitem|nav|noframes|ol|optgroup|option|p|param|search|"
    r"section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul)"
    r"(?:[ \t]|/?>|$)",
    re.IGNORECASE,
)
HTML_ATTRIBUTE = (
    r"[A-Za-z_:][A-Za-z0-9_.:-]*"
    r"(?:[ \t]*=[ \t]*(?:[^ \t\"'=<>`]+|'[^']*'|\"[^\"]*\"))?"
)
HTML_TYPE_7_START = re.compile(
    rf"(?:<[A-Za-z][A-Za-z0-9-]*(?:[ \t]+{HTML_ATTRIBUTE})*[ \t]*/?>"
    r"|</[A-Za-z][A-Za-z0-9-]*[ \t]*>)[ \t]*$"
)
ASCII_PUNCTUATION = frozenset(
    "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
)


class _HtmlBlockState(NamedTuple):
    end_pattern: re.Pattern[str] | None
    containers: tuple[tuple[str, int], ...]


class _ReferenceDefinitionState:
    __slots__ = (
        "phase",
        "closer",
        "pending",
        "containers",
        "label_characters",
        "label_has_nonspace",
    )

    def __init__(
        self,
        phase: str,
        closer: str | None,
        pending: list[_MarkdownLineContext],
        containers: tuple[tuple[str, int], ...],
        label_characters: int = 0,
        label_has_nonspace: bool = False,
    ) -> None:
        self.phase = phase
        self.closer = closer
        self.pending = pending
        self.containers = containers
        self.label_characters = label_characters
        self.label_has_nonspace = label_has_nonspace


def _html_block_end_pattern(
    content: str,
    *,
    allow_type_7: bool,
) -> re.Pattern[str] | None | bool:
    """Return an HTML-block terminator, False for blank, or None."""

    if _leading_indentation_columns(content) > 3:
        return None
    candidate = content.lstrip(" \t")
    if re.match(
        r"^<(?:pre|script|style|textarea)(?:[ \t]|>|$)",
        candidate,
        re.IGNORECASE,
    ):
        return HTML_RAW_END
    if candidate.startswith("<?"):
        return re.compile(r"\?>")
    if candidate.startswith("<!--"):
        return HTML_COMMENT_END
    if re.match(r"^<![A-Za-z]", candidate):
        return re.compile(r">")
    if candidate.startswith("<![CDATA["):
        return re.compile(r"\]\]>")
    if HTML_TYPE_6_START.match(candidate):
        return False
    if allow_type_7 and HTML_TYPE_7_START.fullmatch(candidate):
        return False
    return None


def _reference_destination_remainder(text: str) -> str | None:
    """Return text after one CommonMark link destination, if valid."""

    if not text:
        return None
    if text.startswith("<"):
        escaped = False
        for index, character in enumerate(text[1:], start=1):
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == ">":
                return text[index + 1 :]
            elif character in "<>\n\r":
                return None
        return None

    depth = 0
    escaped = False
    for index, character in enumerate(text):
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character in " \t\r\n":
            return text[index:]
        if ord(character) < 32:
            return None
        if character == "(":
            depth += 1
        elif character == ")":
            if depth == 0:
                return None
            depth -= 1
    return "" if depth == 0 else None


def _reference_title_phase(
    text: str,
    closer: str | None = None,
) -> tuple[str, str | None] | None:
    """Return complete or continuing title state, or None when invalid."""

    if closer is None:
        if not text or text[0] not in "\"'(":
            return None
        closer = {
            "\"": "\"",
            "'": "'",
            "(": ")",
        }[text[0]]
        text = text[1:]
    escaped = False
    for index, character in enumerate(text):
        if escaped:
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == closer:
            if text[index + 1 :].strip(" \t"):
                return None
            return "complete", None
    return "title", closer


def _reference_destination_phase(
    text: str,
) -> tuple[str, str | None] | None:
    """Return the state after a destination, or None when malformed."""

    remainder = _reference_destination_remainder(text)
    if remainder is None:
        return None
    if not remainder:
        return "maybe_title", None
    if remainder[0] not in " \t":
        return None
    title = remainder.lstrip(" \t")
    if not title:
        return "maybe_title", None
    return _reference_title_phase(title)


def _reference_label_line(
    text: str,
    characters: int = 0,
    has_nonspace: bool = False,
) -> tuple[str | None, int, bool] | None:
    """Scan one physical line of a bounded CommonMark link label."""

    index = 0
    while index < len(text):
        character = text[index]
        if (
            character == "\\"
            and index + 1 < len(text)
            and text[index + 1] in ASCII_PUNCTUATION
        ):
            characters += 2
            has_nonspace = True
            index += 2
            continue
        if character == "[":
            return None
        if character == "]":
            if text[index + 1 : index + 2] != ":":
                return None
            if not has_nonspace or characters > 999:
                return None
            return text[index + 2 :].lstrip(" \t"), characters, has_nonspace
        characters += 1
        has_nonspace = has_nonspace or character not in " \t\r\n"
        if characters > 999:
            return None
        index += 1
    return None, characters, has_nonspace


def _reference_definition_start(
    content: str,
) -> tuple[str, str | None, int, bool] | None:
    """Return the continuation state for one possible definition line."""

    if _leading_indentation_columns(content) > 3:
        return None
    candidate = content.lstrip(" \t")
    if not candidate.startswith("["):
        return None
    label = _reference_label_line(candidate[1:])
    if label is None:
        return None
    remainder, characters, has_nonspace = label
    if remainder is None:
        return "label", None, characters, has_nonspace
    if not remainder:
        return "destination", None, characters, has_nonspace
    destination = _reference_destination_phase(remainder)
    if destination is None:
        return None
    phase, closer = destination
    return phase, closer, characters, has_nonspace


def _interrupts_reference_definition(content: str) -> bool:
    """Return whether a CommonMark block start interrupts a definition."""

    stripped = content.strip()
    if not stripped:
        return True
    if re.match(r"^ {0,3}#{1,6}(?:[ \t]+|$)", content):
        return True
    if re.fullmatch(r" {0,3}(?:=+|-+)[ \t]*", content):
        return True
    if re.fullmatch(
        r" {0,3}(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})",
        content,
    ):
        return True
    return _html_block_end_pattern(content, allow_type_7=False) is not None


def _positive_markdown_lines(
    lines: list[tuple[int, str]],
    contexts: list[_MarkdownLineContext] | None = None,
) -> list[tuple[int, str]]:
    """Exclude code while retaining paragraphs and list continuations."""

    positive: list[tuple[int, str]] = []
    paragraph_context: tuple[tuple[str, int], ...] | None = None
    empty_list_context: tuple[tuple[str, int], ...] | None = None
    html_block: _HtmlBlockState | None = None
    reference: _ReferenceDefinitionState | None = None
    contextual = (
        _contextual_markdown_lines(lines) if contexts is None else contexts
    )
    for context in contextual:
        if context.source_gap:
            paragraph_context = None
            empty_list_context = None
            if reference is not None:
                if reference.phase != "maybe_title":
                    positive.extend(
                        (item.line_number, item.raw_line)
                        for item in reference.pending
                    )
                reference = None
        if html_block is not None:
            if context.containers != html_block.containers:
                html_block = None
            elif html_block.end_pattern is None:
                if context.content.strip():
                    continue
                html_block = None
            else:
                if html_block.end_pattern.search(context.content):
                    html_block = None
                continue

        if reference is not None:
            if context.containers != reference.containers:
                if reference.phase != "maybe_title":
                    positive.extend(
                        (item.line_number, item.raw_line)
                        for item in reference.pending
                    )
                reference = None
            elif (
                reference.phase != "maybe_title"
                and _interrupts_reference_definition(context.content)
            ):
                positive.extend(
                    (item.line_number, item.raw_line)
                    for item in reference.pending
                )
                reference = None
                paragraph_context = context.containers
            elif reference.phase == "label":
                label = _reference_label_line(
                    context.content,
                    reference.label_characters + 1,
                    reference.label_has_nonspace,
                )
                if label is not None:
                    remainder, characters, has_nonspace = label
                    if remainder is None:
                        reference.pending.append(context)
                        reference.label_characters = characters
                        reference.label_has_nonspace = has_nonspace
                        continue
                    destination = (
                        ("destination", None)
                        if not remainder
                        else _reference_destination_phase(remainder)
                    )
                    if destination is not None:
                        phase, closer = destination
                        if phase != "complete":
                            reference.phase = phase
                            reference.closer = closer
                            reference.pending.append(context)
                        else:
                            reference = None
                        continue
                positive.extend(
                    (item.line_number, item.raw_line)
                    for item in reference.pending
                )
                reference = None
                paragraph_context = context.containers
            elif reference.phase == "destination":
                destination = _reference_destination_phase(
                    context.content.lstrip(" \t")
                )
                if destination is not None:
                    phase, closer = destination
                    if phase != "complete":
                        reference.phase = phase
                        reference.closer = closer
                        reference.pending.append(context)
                    else:
                        reference = None
                    continue
                positive.extend(
                    (item.line_number, item.raw_line)
                    for item in reference.pending
                )
                reference = None
                paragraph_context = context.containers
            elif reference.phase == "title":
                if context.content.strip():
                    title = _reference_title_phase(
                        context.content,
                        reference.closer,
                    )
                    if title is not None:
                        phase, closer = title
                        if phase == "title":
                            reference.closer = closer
                            reference.pending.append(context)
                        else:
                            reference = None
                        continue
                positive.extend(
                    (item.line_number, item.raw_line)
                    for item in reference.pending
                )
                reference = None
                paragraph_context = context.containers
            else:
                title_text = context.content.lstrip(" \t")
                if title_text.startswith(("\"", "'", "(")):
                    title = _reference_title_phase(title_text)
                    if title is not None:
                        phase, closer = title
                        if phase == "title":
                            reference.phase = phase
                            reference.closer = closer
                            reference.pending.append(context)
                        else:
                            reference = None
                        continue
                reference = None

        if not context.content.strip():
            positive.append((context.line_number, context.raw_line))
            paragraph_context = None
            visible_line = context.raw_line.removesuffix(" <html-comment>")
            empty_list_context = (
                context.containers
                if visible_line.strip()
                and any(kind == "list" for kind, _ in context.containers)
                else None
            )
            continue
        html_end = _html_block_end_pattern(
            context.content,
            allow_type_7=paragraph_context is None,
        )
        if html_end is not None:
            paragraph_context = None
            empty_list_context = None
            if html_end is not False and not html_end.search(context.content):
                html_block = _HtmlBlockState(html_end, context.containers)
            elif html_end is False:
                html_block = _HtmlBlockState(None, context.containers)
            continue

        indentation = _leading_indentation_columns(context.content)
        visible_line = context.raw_line.removesuffix(" <html-comment>")
        _, unquoted_line = _strip_blockquote_prefixes(visible_line)
        if (
            empty_list_context is not None
            and context.containers == empty_list_context
            and _leading_indentation_columns(unquoted_line) >= 4
        ):
            empty_list_context = None
            paragraph_context = None
            continue
        empty_list_context = None
        if indentation >= 4 and paragraph_context != context.containers:
            paragraph_context = None
            continue

        if paragraph_context is None:
            definition = _reference_definition_start(context.content)
            if definition is not None:
                phase, closer, characters, has_nonspace = definition
                if phase != "complete":
                    reference = _ReferenceDefinitionState(
                        phase,
                        closer,
                        [context],
                        context.containers,
                        characters,
                        has_nonspace,
                    )
                continue

        positive.append((context.line_number, context.raw_line))
        paragraph_content = context.content[indentation:]
        if _starts_markdown_paragraph(paragraph_content):
            paragraph_context = context.containers
        else:
            paragraph_context = None
    if reference is not None and reference.phase != "maybe_title":
        positive.extend(
            (item.line_number, item.raw_line) for item in reference.pending
        )
    return positive


def _positive_markdown_contexts(
    lines: list[tuple[int, str]],
    contexts: list[_MarkdownLineContext] | None = None,
) -> list[_MarkdownLineContext]:
    """Return contextual records retained by the positive-line filter."""

    contextual = (
        _contextual_markdown_lines(lines) if contexts is None else contexts
    )
    positive_line_numbers = {
        line_number
        for line_number, _ in _positive_markdown_lines(lines, contextual)
    }
    return [
        context
        for context in contextual
        if context.line_number in positive_line_numbers
    ]


def _atx_heading_content(line: str, level: int) -> str | None:
    """Return normalized visible ATX heading content for one exact level."""

    visible_line = line.removesuffix(" <html-comment>")
    match = re.fullmatch(
        rf" {{0,3}}#{{{level}}}[ \t]+"
        r"(.*?)(?:[ \t]+#+[ \t]*)?",
        visible_line,
    )
    if match is None:
        return None
    return match.group(1).strip()


def _consumer_h3_content(content: str) -> str | None:
    """Return one consumer H3 from resolved container content."""

    return _atx_heading_content(content, 3)


def _single_code_span_content(content: str) -> str:
    """Unwrap content only when the whole heading is one code span."""

    match = re.fullmatch(
        r"(?P<ticks>`+)(?P<body>[^\r\n]+?)(?P=ticks)",
        content,
    )
    if match is None or match.group("ticks") in match.group("body"):
        return content
    body = match.group("body")
    if body.startswith(" ") and body.endswith(" ") and body.strip(" "):
        return body[1:-1]
    return body


def _listed_code_span_content(line: str) -> str | None:
    """Return an exact code span owned by any supported list marker."""

    content, containers = _markdown_container_view(line)
    if not any(kind == "list" for kind, _ in containers):
        return None
    match = re.fullmatch(
        r"(?P<ticks>`+)(?P<body>[^`\r\n]+)(?P=ticks)",
        content,
    )
    return None if match is None else match.group("body")


def _visible_h2_section(
    lines: list[tuple[int, str]],
    title: str,
    contexts: list[_MarkdownLineContext] | None = None,
) -> list[tuple[int, str]] | None:
    """Return one exact visible H2 section, excluding its heading."""

    contextual = (
        _contextual_markdown_lines(lines) if contexts is None else contexts
    )
    heading_indexes = [
        index
        for index, context in enumerate(contextual)
        if not context.containers
        and _atx_heading_content(context.content, 2) == title
    ]
    if len(heading_indexes) != 1:
        return None
    section: list[tuple[int, str]] = []
    for context in contextual[heading_indexes[0] + 1 :]:
        if (
            not context.containers
            and _atx_heading_content(context.content, 2) is not None
        ):
            break
        section.append((context.line_number, context.raw_line))
    return section


def _visible_h2_source_section(text: str, title: str) -> str | None:
    """Return raw source owned by one exact visible top-level H2."""

    raw_lines = text.splitlines()
    visible, contextual = _scan_visible_markdown(text)
    contextual = _positive_markdown_contexts(visible, contextual)
    headings = [
        context.line_number
        for context in contextual
        if not context.containers
        and _atx_heading_content(context.content, 2) == title
    ]
    if len(headings) != 1:
        return None
    start = headings[0] - 1
    end = len(raw_lines)
    for context in contextual:
        if context.line_number <= headings[0]:
            continue
        if (
            not context.containers
            and _atx_heading_content(context.content, 2) is not None
        ):
            end = context.line_number - 1
            break
    return "\n".join(raw_lines[start:end])


def _section_has_fenced_code(section: str) -> bool:
    """Return whether a raw Markdown section opens any supported fence."""

    active_containers: tuple[tuple[str, int], ...] = ()
    for line in section.splitlines():
        content, containers = _resolve_markdown_container_view(
            line,
            active_containers,
        )
        if _fence_opener(content) is not None:
            return True
        if not line.strip():
            continue
        if any(kind == "list" for kind, _ in containers):
            active_containers = containers
        else:
            active_containers = ()
    return False


def _section_has_indented_code(section: str) -> bool:
    """Return whether visible section content contains indented code."""

    visible, contexts = _scan_visible_markdown(section)
    positive_line_numbers = {
        line_number
        for line_number, _ in _positive_markdown_lines(visible, contexts)
    }
    return any(
        line.strip() and line_number not in positive_line_numbers
        for line_number, line in visible
    )


def _retired_patterns_contract_errors(text: str) -> list[str]:
    """Validate exact evidence and no-code contracts for retired patterns."""

    errors: list[str] = []
    for title, contract in RETIRED_PATTERN_SECTIONS.items():
        section = _visible_h2_source_section(text, title)
        if section is None:
            errors.append(
                error(
                    "PATTERNS.md",
                    f"{title} retired section contract is missing or ambiguous",
                    f"restore the exact top-level {title!r} retired section",
                )
            )
            continue

        visible, contexts = _scan_visible_markdown(section)
        positive_lines = _positive_markdown_lines(visible, contexts)
        evidence = tuple(
            evidence_item
            for _, line in positive_lines
            if (evidence_item := _listed_code_span_content(line)) is not None
        )
        positive_contexts = _positive_markdown_contexts(visible, contexts)
        status_lines = [
            context.content
            for context in positive_contexts
            if not context.containers and context.content.startswith("Status:")
        ]
        exact_status = (
            len(status_lines) == 1
            and re.match(
                r"^Status: retired\.(?:[ \t]|$)",
                status_lines[0],
            )
            is not None
        )
        expected_evidence = cast(tuple[str, ...], contract["evidence"])
        expected_rules = cast(tuple[str, ...], contract["rules"])
        required_tokens = (
            INSTRUCTION_PATH,
            PLUGIN_TEMPLATE_PATH,
            *expected_rules,
        )
        inline_code_tokens = tuple(
            match.group(1)
            for _, line in positive_lines
            for match in re.finditer(r"(?<!`)`([^`\r\n]+)`(?!`)", line)
        )
        if (
            len(evidence) != len(expected_evidence)
            or set(evidence) != set(expected_evidence)
            or not exact_status
            or any(
                inline_code_tokens.count(token) != 1
                for token in required_tokens
            )
        ):
            errors.append(
                error(
                    "PATTERNS.md",
                    f"{title} retired section contract does not match exact "
                    "evidence, status, routing, and rule citations",
                    f"restore the reviewed retired section contract for {title}",
                )
            )
        if _section_has_fenced_code(section) or _section_has_indented_code(section):
            errors.append(
                error(
                    "PATTERNS.md",
                    f"{title} must not publish replacement code",
                    "remove fenced or indented code and route new work to the "
                    "canonical Zsh standard and plugin template",
                )
            )
    return errors


def _normalized_visible_text(
    lines: list[tuple[int, str]],
    contexts: list[_MarkdownLineContext] | None = None,
) -> str:
    return " ".join(
        line.strip()
        for _, line in _positive_markdown_lines(lines, contexts)
        if line.strip()
    )


def _positive_visible_text(
    lines: list[tuple[int, str]],
    contexts: list[_MarkdownLineContext] | None = None,
) -> str:
    """Join visible non-code lines for positive ownership checks."""

    return "\n".join(
        line
        for _, line in _positive_markdown_lines(lines, contexts)
    )


def _visible_markdown_segments(
    lines: list[tuple[int, str]],
    contexts: list[_MarkdownLineContext] | None = None,
) -> list[str]:
    """Join wrapped visible Markdown into narrow prose/list segments."""

    segments: list[str] = []
    current: list[str] = []
    current_context: tuple[str, int] | None = None

    def flush() -> None:
        if current:
            segments.append(" ".join(current))
            current.clear()

    for _, raw_line in _positive_markdown_lines(lines, contexts):
        visible_line = raw_line.removesuffix(" <html-comment>")
        quote_depth, content = _strip_blockquote_prefixes(visible_line)
        line = content.strip()
        if not line:
            flush()
            current_context = None
            continue
        context = (
            ("blockquote", quote_depth)
            if quote_depth
            else ("document", 0)
        )
        if context != current_context:
            flush()
            current_context = context
        boundary = (
            re.match(r"^#{1,6}[ \t]+", line) is not None
            or re.match(r"^(?:[-+*]|\d+[.)])[ \t]+", line) is not None
            or line.startswith("|")
        )
        if boundary:
            flush()
        current.append(line)
    flush()
    return segments


README_ZSH_VALIDATION_SUBJECT = (
    r"(?:"
    r"zsh\s+standard\s+(?:validation|enforcement)"
    r"|(?:validation|enforcement)\s+of\s+the\s+zsh\s+standard"
    r"|(?:the\s+)?zsh\s+standard\s+validator"
    r")"
)
README_ZSH_VALIDATION_CONTRADICTION = re.compile(
    rf"""
    \b{README_ZSH_VALIDATION_SUBJECT}
    (?:
      \s+(?:is|remains)\s+(?:currently\s+)?inactive
      (?=\s*(?:[.;,:)]|$))
      |
      \s+(?:is|remains|has)\s+not\s+(?:yet\s+)?
      (?:been\s+)?(?:implemented|active)
      (?=\s*(?:[.;,:)]|$))
      |
      \s+(?:is|remains)\s+planned\s+for\s+(?:a\s+)?
      (?:later|future)\s+phase
      (?=\s*(?:[.;,:)]|$))
      |
      \s+will\s+(?:begin|start)\s+in\s+(?:a\s+)?
      (?:later|future)\s+phase
      (?=\s*(?:[.;,:)]|$))
      |
      \s+(?:is|remains)\s+deferred\s+(?:to|until)\s+
      (?:a\s+)?(?:later|future)\s+phase
      (?=\s*(?:[.;,:)]|$))
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _readme_has_zsh_validation_contradiction(
    lines: list[tuple[int, str]],
    contexts: list[_MarkdownLineContext] | None = None,
) -> bool:
    for segment in _visible_markdown_segments(lines, contexts):
        simplified = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", segment)
        simplified = re.sub(r"[`*_]", "", simplified)
        simplified = " ".join(simplified.split())
        if README_ZSH_VALIDATION_CONTRADICTION.search(simplified):
            return True
    return False


def _metadata_values(value: str) -> list[str] | None:
    if re.fullmatch(r"`[^`]+`(?:, `[^`]+`)*", value) is None:
        return None
    return re.findall(r"`([^`]+)`", value)


def _documentation_reference_index_errors(text: str) -> list[str]:
    """Validate the exact visible Markdown documentation-source registry."""

    lines, contexts = _scan_visible_markdown(text)
    lines = _positive_markdown_lines(lines, contexts)
    heading = "## Official documentation reference index"
    heading_indexes = [
        index for index, (_, line) in enumerate(lines) if line == heading
    ]
    problem = (
        "official documentation reference index must match the exact ordered "
        "registry"
    )
    if len(heading_indexes) != 1:
        return [problem]

    actual_lines: list[str] = []
    for _, line in lines[heading_indexes[0] + 1 :]:
        if line.startswith("## "):
            break
        if line.strip():
            actual_lines.append(line)
    expected_lines = tuple(
        f"- `{evidence_id}`: [{title}]({url})"
        for evidence_id, (title, url, _) in DOCUMENTATION_SOURCES.items()
    )
    if tuple(actual_lines) != expected_lines:
        return [problem]
    return []


def _visible_markdown_rule_block(text: str, rule_id: str) -> str | None:
    lines, contexts = _scan_visible_markdown(text)
    lines = _positive_markdown_lines(lines, contexts)
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
    lines, contexts = _scan_visible_markdown(text)
    lines = _positive_markdown_lines(lines, contexts)
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
    for reference_error in _documentation_reference_index_errors(text):
        errors.append(
            error(
                INSTRUCTION_PATH,
                reference_error,
                "restore one visible entry for every canonical documentation "
                "source in exact order",
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
    """Validate advisory ownership and canonical references without rewriting."""

    errors: list[str] = []
    texts: dict[str, str] = {}
    for relative_path in REFERENCE_CONSUMER_PATHS + (PLUGIN_TEMPLATE_PATH,):
        text, read_errors = _read_text(root, relative_path)
        errors.extend(read_errors)
        if text is not None:
            texts[relative_path] = text

    scans = {
        relative_path: _scan_visible_markdown(text)
        for relative_path, text in texts.items()
    }
    visible_lines = {
        relative_path: scan[0] for relative_path, scan in scans.items()
    }
    visible_contexts = {
        relative_path: scan[1] for relative_path, scan in scans.items()
    }
    visible_texts = {
        relative_path: _positive_visible_text(
            lines,
            visible_contexts[relative_path],
        )
        for relative_path, lines in visible_lines.items()
    }
    positive_contexts = {
        relative_path: _positive_markdown_contexts(
            lines,
            visible_contexts[relative_path],
        )
        for relative_path, lines in visible_lines.items()
    }

    for relative_path in REFERENCE_CONSUMER_PATHS:
        visible_text = visible_texts.get(relative_path)
        if visible_text is None:
            continue
        for canonical_path in (INSTRUCTION_PATH, POLICY_PATH):
            if canonical_path not in visible_text:
                errors.append(
                    error(
                        relative_path,
                        "missing visible canonical Zsh reference "
                        f"{canonical_path!r}",
                        f"link to {canonical_path} without copying its rule catalog",
                    )
                )

    rule_values = policy.get("normative_rules")
    rule_ids: tuple[str, ...] = ()
    if isinstance(rule_values, list):
        candidate_ids = tuple(
            item.get("id")
            for item in rule_values
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        )
        if (
            len(candidate_ids) == len(rule_values)
            and candidate_ids == NORMATIVE_RULE_IDS
        ):
            rule_ids = cast(tuple[str, ...], candidate_ids)

    if rule_ids:
        rule_id_set = set(rule_ids)
        for relative_path in REFERENCE_CONSUMER_PATHS:
            text = texts.get(relative_path)
            if text is None:
                continue
            for context in positive_contexts[relative_path]:
                heading = _consumer_h3_content(context.content)
                if heading is None:
                    continue
                normalized_heading = _single_code_span_content(heading)
                if normalized_heading in rule_id_set:
                    errors.append(
                        error(
                            relative_path,
                            "normative rule heading "
                            f"{normalized_heading!r} at line "
                            f"{context.line_number}; "
                            "rules belong in canonical instruction",
                            "replace the heading with an inline rule-ID citation",
                        )
                    )
            if all(rule_id in text for rule_id in rule_ids):
                errors.append(
                    error(
                        relative_path,
                        "complete catalog duplication of all canonical Zsh rule IDs",
                        "keep only the small rule-ID subset relevant to this consumer",
                    )
                )

    patterns_text = texts.get("PATTERNS.md")
    if patterns_text is not None:
        patterns_lines = visible_lines["PATTERNS.md"]
        first_h2_line = next(
            (
                context.line_number
                for context in positive_contexts["PATTERNS.md"]
                if not context.containers
                and _atx_heading_content(context.content, 2) is not None
            ),
            len(patterns_text.splitlines()) + 1,
        )
        intro_lines = [
            line for line in patterns_lines if line[0] < first_h2_line
        ]
        intro_contexts = [
            context
            for context in positive_contexts["PATTERNS.md"]
            if context.line_number < first_h2_line
        ]
        normalized_patterns = _normalized_visible_text(
            intro_lines,
            intro_contexts,
        )
        patterns_contract = (
            "Patterns below are observed examples, not a second policy source.",
            "the canonical standard wins and the pattern must be corrected.",
        )
        if any(
            fragment not in normalized_patterns for fragment in patterns_contract
        ):
            errors.append(
                error(
                    "PATTERNS.md",
                    "observed patterns are non-normative and must defer on conflict",
                    "state that patterns are observed examples and the canonical "
                    "standard wins conflicts",
                )
            )
        errors.extend(_retired_patterns_contract_errors(patterns_text))

    readme_text = texts.get(".github/README.md")
    if readme_text is not None:
        readme_lines = visible_lines[".github/README.md"]
        readme_sections = {
            "Repository Structure": (
                INSTRUCTION_PATH,
                POLICY_PATH,
            ),
            "Instruction Architecture": (
                INSTRUCTION_PATH,
                POLICY_PATH,
                VALIDATOR_PATH,
            ),
        }
        for section_title, required_paths in readme_sections.items():
            section_lines = _visible_h2_section(
                readme_lines,
                section_title,
                positive_contexts[".github/README.md"],
            )
            section_line_numbers = {
                line_number for line_number, _ in section_lines or []
            }
            section_text = (
                ""
                if section_lines is None
                else _positive_visible_text(
                    section_lines,
                    [
                        context
                        for context in positive_contexts[".github/README.md"]
                        if context.line_number in section_line_numbers
                    ],
                )
            )
            for required_path in required_paths:
                if required_path in section_text:
                    continue
                errors.append(
                    error(
                        ".github/README.md",
                        f"{section_title} must visibly catalog "
                        f"{required_path!r}",
                        f"catalog {required_path} in the {section_title} section",
                    )
                )
        if _readme_has_zsh_validation_contradiction(
            readme_lines,
            positive_contexts[".github/README.md"],
        ):
            errors.append(
                error(
                    ".github/README.md",
                    "claims active Phase 1 Zsh validation is deferred",
                    "describe only the instruction, policy, and validator behavior "
                    "implemented in Phase 1",
                )
            )

    template_text = texts.get(PLUGIN_TEMPLATE_PATH)
    if template_text is not None:
        for marker, fix in (
            ("TODO", "replace TODO markers with direct authoring instructions"),
            (
                "#funtions-directory",
                "use the correct #functions-directory anchor",
            ),
        ):
            if marker in template_text:
                errors.append(
                    error(
                        PLUGIN_TEMPLATE_PATH,
                        f"nonconforming scaffold marker {marker!r}",
                        fix,
                    )
                )

    manifest_path, _ = _contained_regular_path(root, MANIFEST_PATH)
    manifest: dict[str, object] | None = None
    if manifest_path is not None:
        try:
            manifest = load_json_strict(manifest_path)
        except PolicyValidationError:
            pass
    if manifest is not None:
        surface_values = manifest.get("surfaces")
        if isinstance(surface_values, list):
            for relative_path in ADVISORY_CONSUMER_PATHS:
                matches = [
                    cast(dict[str, object], item)
                    for item in surface_values
                    if isinstance(item, dict)
                    and item.get("path") == relative_path
                ]
                if len(matches) != 1:
                    errors.append(
                        error(
                            relative_path,
                            "must have exactly one manifest surface for this "
                            "advisory consumer",
                            f"keep exactly one manifest surface with path "
                            f"{relative_path!r}",
                        )
                    )
                    continue
                surface = matches[0]
                if surface.get("authority") != "advisory":
                    errors.append(
                        error(
                            relative_path,
                            "manifest authority must be advisory",
                            "set authority to 'advisory'",
                        )
                    )
                if surface.get("canonical_for") != []:
                    errors.append(
                        error(
                            relative_path,
                            "manifest canonical_for must be empty",
                            "set canonical_for to []",
                        )
                    )
    return errors


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
