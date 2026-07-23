#!/usr/bin/env python3

import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT_PATH = Path(__file__).with_name("validate-agent-policy.py")
PUBLIC_ROOT = SCRIPT_PATH.parents[1]
REQUIRED_IMPACT_QUESTIONS = (
    "Is this shared policy, scoped guidance, runtime-only behavior, or enforcement?",
    "Which runtimes and repository contexts must receive it?",
    "Is the canonical owner still correct?",
    "Does another surface now duplicate or contradict it?",
    "Does either manifest need an added, changed, or removed route?",
    "Can each supported runtime still receive the mandatory rule without relying on an optional hook or skill?",
    "Do generated output and size limits still pass?",
)
SPEC = importlib.util.spec_from_file_location("validate_agent_policy", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {SCRIPT_PATH}")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


BASE_MANIFEST = {
    "version": 1,
    "repository": "z-shell/.github",
    "canonical_policy": "AGENTS.md",
    "surfaces": [
        {
            "id": "organization-policy",
            "path": "AGENTS.md",
            "kind": "shared-policy",
            "authority": "canonical",
            "consumers": ["codex", "claude-code", "copilot", "gemini-cli", "human"],
            "tasks": ["all"],
            "file_patterns": ["**"],
            "required": True,
            "review_owner": "z-shell maintainers",
            "canonical_for": ["organization-policy"],
        },
        {
            "id": "organization-patterns",
            "path": "PATTERNS.md",
            "kind": "shared-policy",
            "authority": "canonical-detail",
            "consumers": ["codex", "claude-code", "copilot", "gemini-cli", "human"],
            "tasks": ["implementation"],
            "file_patterns": ["**"],
            "required": True,
            "review_owner": "z-shell maintainers",
            "canonical_for": ["implementation-patterns"],
        },
        {
            "id": "agent-memory",
            "path": ".github/AGENT_MEMORY.md",
            "kind": "runbook",
            "authority": "canonical-detail",
            "consumers": ["codex", "claude-code", "copilot", "gemini-cli", "human"],
            "tasks": ["handoff"],
            "file_patterns": ["**"],
            "required": True,
            "review_owner": "z-shell maintainers",
            "canonical_for": ["agent-handoffs"],
        },
        {
            "id": "public-agent-catalog",
            "path": ".github/README.md",
            "kind": "runbook",
            "authority": "advisory",
            "consumers": ["human"],
            "tasks": ["onboarding"],
            "file_patterns": ["**"],
            "required": True,
            "review_owner": "z-shell maintainers",
            "canonical_for": [],
        },
        {
            "id": "copilot-adapter",
            "path": ".github/copilot-instructions.md",
            "kind": "adapter",
            "authority": "adapter-only",
            "consumers": ["copilot"],
            "tasks": ["all"],
            "file_patterns": ["**"],
            "required": True,
            "review_owner": "z-shell maintainers",
            "canonical_for": [],
        },
    ],
}


def write_file(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_manifest(root: Path, manifest: dict[str, object]) -> None:
    write_file(
        root,
        ".github/instruction-surfaces.json",
        json.dumps(manifest, indent=2) + "\n",
    )


def make_repository(root: Path) -> dict[str, object]:
    manifest = copy.deepcopy(BASE_MANIFEST)
    write_file(root, "AGENTS.md", "# Agent policy\n")
    write_file(root, "PATTERNS.md", "# Organization patterns\n")
    write_file(root, ".github/AGENT_MEMORY.md", "# Agent handoffs\n")
    write_file(root, ".github/README.md", "# Public agent catalog\n")
    write_file(root, ".github/copilot-instructions.md", "@../AGENTS.md\n")
    write_manifest(root, manifest)
    return manifest


def make_surface(
    surface_id: str,
    path: str,
    *,
    kind: str = "runbook",
    authority: str = "advisory",
    consumers: list[str] | None = None,
    tasks: list[str] | None = None,
    file_patterns: list[str] | None = None,
    required: bool = True,
    canonical_for: list[str] | None = None,
) -> dict[str, object]:
    return {
        "id": surface_id,
        "path": path,
        "kind": kind,
        "authority": authority,
        "consumers": consumers or ["human"],
        "tasks": tasks or ["all"],
        "file_patterns": file_patterns or ["**"],
        "required": required,
        "review_owner": "z-shell maintainers",
        "canonical_for": canonical_for or [],
    }


class AgentPolicyValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = Path(temporary_directory.name)
        self.manifest = make_repository(self.root)

    def assert_error_contains(self, errors: list[str], *needles: str) -> None:
        self.assertTrue(
            any(all(needle in message for needle in needles) for message in errors),
            f"expected one error containing {needles!r}; got {errors!r}",
        )

    def test_valid_repository_has_no_errors(self) -> None:
        self.assertEqual(validator.validate(self.root), [])

    def test_rejects_invalid_json(self) -> None:
        write_file(self.root, ".github/instruction-surfaces.json", "{not json\n")

        errors = validator.validate(self.root)

        self.assert_error_contains(
            errors,
            ".github/instruction-surfaces.json",
            "invalid JSON",
        )

    def test_rejects_unknown_schema_version(self) -> None:
        self.manifest["version"] = 2
        write_manifest(self.root, self.manifest)

        errors = validator.validate(self.root)

        self.assert_error_contains(errors, ".github/instruction-surfaces.json", "version")

    def test_rejects_unknown_enum_values(self) -> None:
        cases = (
            ("kind", "unknown-kind"),
            ("authority", "unknown-authority"),
            ("consumer", "unknown-consumer"),
        )
        for field, invalid_value in cases:
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    manifest = make_repository(root)
                    surface = manifest["surfaces"][0]
                    if field == "consumer":
                        surface["consumers"] = [invalid_value]
                    else:
                        surface[field] = invalid_value
                    write_manifest(root, manifest)

                    errors = validator.validate(root)

                    self.assert_error_contains(errors, "organization-policy", invalid_value)

    def test_rejects_non_string_enum_values_without_traceback(self) -> None:
        cases = (("kind", ["adapter"]), ("authority", {"name": "canonical"}))
        for field, invalid_value in cases:
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    manifest = make_repository(root)
                    manifest["surfaces"][0][field] = invalid_value
                    write_manifest(root, manifest)

                    errors = validator.validate(root)

                    self.assert_error_contains(
                        errors,
                        "organization-policy",
                        repr(invalid_value),
                    )

    def test_rejects_duplicate_ids(self) -> None:
        duplicate = make_surface("organization-policy", "DUPLICATE.md")
        self.manifest["surfaces"].append(duplicate)
        write_file(self.root, "DUPLICATE.md", "# Duplicate\n")
        write_manifest(self.root, self.manifest)

        errors = validator.validate(self.root)

        self.assert_error_contains(errors, "organization-policy", "duplicate")

    def test_rejects_duplicate_paths(self) -> None:
        self.manifest["surfaces"].append(
            make_surface("duplicate-agent-policy", "AGENTS.md")
        )
        write_manifest(self.root, self.manifest)

        errors = validator.validate(self.root)

        self.assert_error_contains(errors, "AGENTS.md", "duplicate")

    def test_rejects_duplicate_canonical_owner(self) -> None:
        self.manifest["surfaces"][1]["canonical_for"].append("organization-policy")
        write_manifest(self.root, self.manifest)

        errors = validator.validate(self.root)

        self.assert_error_contains(errors, "organization-policy", "duplicate")

    def test_rejects_agent_or_skill_canonical_owner(self) -> None:
        cases = (
            ("agent", ".github/agents/policy.agent.md"),
            ("skill", ".github/skills/policy/SKILL.md"),
        )
        for kind, path in cases:
            with self.subTest(kind=kind):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    manifest = make_repository(root)
                    manifest["surfaces"].append(
                        make_surface(
                            f"canonical-{kind}",
                            path,
                            kind=kind,
                            authority="canonical-detail",
                            consumers=["codex"],
                            canonical_for=["mandatory-policy"],
                        )
                    )
                    write_file(root, path, f"# Canonical {kind}\n")
                    write_manifest(root, manifest)

                    errors = validator.validate(root)

                    self.assert_error_contains(
                        errors,
                        f"canonical-{kind}",
                        kind,
                        "mandatory-policy",
                    )

    def test_rejects_adapter_as_canonical(self) -> None:
        self.manifest["surfaces"][4]["authority"] = "canonical"
        write_manifest(self.root, self.manifest)

        errors = validator.validate(self.root)

        self.assert_error_contains(errors, "copilot-adapter", "adapter", "canonical")

    def test_rejects_optional_canonical_owner(self) -> None:
        self.manifest["surfaces"][0]["required"] = False
        write_manifest(self.root, self.manifest)

        errors = validator.validate(self.root)

        self.assert_error_contains(errors, "organization-policy", "required")

    def test_rejects_missing_canonical_policy(self) -> None:
        for value in (None, "PATTERNS.md"):
            with self.subTest(canonical_policy=value):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    manifest = make_repository(root)
                    if value is None:
                        manifest.pop("canonical_policy")
                    else:
                        manifest["canonical_policy"] = value
                    write_manifest(root, manifest)

                    errors = validator.validate(root)

                    self.assert_error_contains(
                        errors,
                        ".github/instruction-surfaces.json",
                        "canonical_policy",
                    )

    def test_rejects_missing_declared_path(self) -> None:
        cases = (("AGENTS.md", True), (".github/README.md", False))
        for relative_path, required in cases:
            with self.subTest(path=relative_path, required=required):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    manifest = make_repository(root)
                    surface = next(
                        item
                        for item in manifest["surfaces"]
                        if item["path"] == relative_path
                    )
                    surface["required"] = required
                    (root / relative_path).unlink()
                    write_manifest(root, manifest)

                    errors = validator.validate(root)

                    self.assert_error_contains(errors, relative_path, "regular file")

    def test_rejects_parent_path(self) -> None:
        self.manifest["surfaces"][3]["path"] = "../outside.md"
        write_manifest(self.root, self.manifest)

        errors = validator.validate(self.root)

        self.assert_error_contains(errors, "../outside.md", "escapes repository")

    def test_rejects_outside_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as outside_directory:
            outside = Path(outside_directory) / "AGENTS.md"
            outside.write_text("# Outside\n", encoding="utf-8")
            (self.root / "AGENTS.md").unlink()
            (self.root / "AGENTS.md").symlink_to(outside)

            errors = validator.validate(self.root)

        self.assert_error_contains(errors, "AGENTS.md", "escapes repository")

    def test_rejects_private_reference_in_active_surface(self) -> None:
        with (self.root / "AGENTS.md").open("a", encoding="utf-8") as policy:
            policy.write("Read workspace/repos.yml before editing.\n")

        errors = validator.validate(self.root)

        self.assert_error_contains(errors, "AGENTS.md", "workspace/repos.yml")

    def test_rejects_invalid_utf8_active_surface(self) -> None:
        (self.root / "PATTERNS.md").write_bytes(b"# Patterns\n\xff\n")

        errors = validator.validate(self.root)

        self.assert_error_contains(errors, "PATTERNS.md", "UTF-8")

    def test_rejects_workspace_group_path(self) -> None:
        with (self.root / "PATTERNS.md").open("a", encoding="utf-8") as patterns:
            patterns.write("See repos/docs/wiki/docs/example.md.\n")

        errors = validator.validate(self.root)

        self.assert_error_contains(errors, "PATTERNS.md", "repos/docs/")

    def test_allows_github_api_and_privacy_prose(self) -> None:
        with (self.root / "AGENTS.md").open("a", encoding="utf-8") as policy:
            policy.write(
                "Use gh api repos/{owner}/{repo} for public metadata.\n"
                "Protect private information and explain the privacy boundary.\n"
            )

        self.assertEqual(validator.validate(self.root), [])

    def test_does_not_scan_historical_unrouted_file(self) -> None:
        write_file(
            self.root,
            "decisions/archive/0001-legacy.md",
            "The old process used workspace/repos.yml.\n",
        )

        self.assertEqual(validator.validate(self.root), [])

    def test_rejects_public_vendor_root_files(self) -> None:
        for filename in ("CLAUDE.md", "GEMINI.md"):
            for variant in ("regular", "broken-symlink"):
                with self.subTest(filename=filename, variant=variant):
                    with tempfile.TemporaryDirectory() as directory:
                        root = Path(directory)
                        make_repository(root)
                        path = root / filename
                        if variant == "regular":
                            path.write_text("# Vendor policy\n", encoding="utf-8")
                        else:
                            os.symlink(root / "missing-target", path)

                        errors = validator.validate(root)

                        self.assert_error_contains(errors, filename, "vendor root")

    def test_rejects_wrong_copilot_adapter(self) -> None:
        with (self.root / ".github/copilot-instructions.md").open(
            "a", encoding="utf-8"
        ) as adapter:
            adapter.write("Additional policy.\n")

        errors = validator.validate(self.root)

        self.assert_error_contains(
            errors,
            ".github/copilot-instructions.md",
            "exact template",
        )

    def test_rejects_missing_apply_to(self) -> None:
        path = ".github/instructions/python.instructions.md"
        self.manifest["surfaces"].append(
            make_surface(
                "python-guidance",
                path,
                kind="scoped-guidance",
                authority="canonical-detail",
                consumers=["copilot"],
                file_patterns=["**/*.py"],
            )
        )
        write_file(
            self.root,
            path,
            '---\ndescription: "Python guidance"\n---\n\n# Python\n',
        )
        write_manifest(self.root, self.manifest)

        errors = validator.validate(self.root)

        self.assert_error_contains(errors, path, "applyTo")

    def test_rejects_apply_to_manifest_mismatch(self) -> None:
        path = ".github/instructions/python.instructions.md"
        self.manifest["surfaces"].append(
            make_surface(
                "python-guidance",
                path,
                kind="scoped-guidance",
                authority="canonical-detail",
                consumers=["copilot"],
                file_patterns=["**/*.sh"],
            )
        )
        write_file(
            self.root,
            path,
            '---\napplyTo: "**/*.py"\n---\n\n# Python\n',
        )
        write_manifest(self.root, self.manifest)

        errors = validator.validate(self.root)

        self.assert_error_contains(errors, path, "**/*.py", "**/*.sh")

    def test_rejects_nested_or_malformed_apply_to(self) -> None:
        cases = (
            (
                "nested",
                '---\ncontainer:\n  applyTo: "**/*.py"\n---\n\n# Python\n',
                "**/*.py",
            ),
            (
                "unterminated-quote",
                '---\napplyTo: "**/*.py\n---\n\n# Python\n',
                '"**/*.py',
            ),
        )
        for variant, content, manifest_pattern in cases:
            with self.subTest(variant=variant):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    manifest = make_repository(root)
                    path = ".github/instructions/python.instructions.md"
                    manifest["surfaces"].append(
                        make_surface(
                            "python-guidance",
                            path,
                            kind="scoped-guidance",
                            authority="canonical-detail",
                            consumers=["copilot"],
                            file_patterns=[manifest_pattern],
                        )
                    )
                    write_file(root, path, content)
                    write_manifest(root, manifest)

                    errors = validator.validate(root)

                    self.assert_error_contains(errors, path, "applyTo")

    def test_rejects_ambiguous_apply_to_yaml_syntax(self) -> None:
        cases = (
            ("alias", "*patterns", "*patterns"),
            ("anchor", '&patterns "**/*.py"', '&patterns "**/*.py"'),
            ("tag", '!glob "**/*.py"', '!glob "**/*.py"'),
            ("flow-sequence", '["**/*.py"]', '["**/*.py"]'),
            ("implicit-boolean", "true", "true"),
            ("invalid-double-escape", r'"**/\q.py"', r"**/\q.py"),
            ("invalid-single-quote", "'**/*.py'junk'", "**/*.py'junk"),
        )
        for variant, apply_to_source, manifest_pattern in cases:
            with self.subTest(variant=variant):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    manifest = make_repository(root)
                    path = ".github/instructions/python.instructions.md"
                    manifest["surfaces"].append(
                        make_surface(
                            "python-guidance",
                            path,
                            kind="scoped-guidance",
                            authority="canonical-detail",
                            consumers=["copilot"],
                            file_patterns=[manifest_pattern],
                        )
                    )
                    write_file(
                        root,
                        path,
                        f"---\napplyTo: {apply_to_source}\n---\n\n# Python\n",
                    )
                    write_manifest(root, manifest)

                    errors = validator.validate(root)

                    self.assert_error_contains(errors, path, "applyTo")

    def test_rejects_inventory_omission(self) -> None:
        omitted_paths = (
            ".github/instructions/unlisted.instructions.md",
            ".github/agents/unlisted.agent.md",
            ".github/skills/unlisted/SKILL.md",
            "runbooks/unlisted.md",
            "decisions/unlisted.md",
        )
        for omitted_path in omitted_paths:
            with self.subTest(path=omitted_path):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    make_repository(root)
                    write_file(root, omitted_path, "# Unlisted surface\n")

                    errors = validator.validate(root)

                    self.assert_error_contains(errors, omitted_path, "inventory")

    def test_inventory_requires_the_actual_surface_path(self) -> None:
        instruction_path = ".github/instructions/unlisted.instructions.md"
        alias_path = "instruction-alias.md"
        write_file(self.root, instruction_path, "# Unlisted surface\n")
        (self.root / alias_path).symlink_to(self.root / instruction_path)
        self.manifest["surfaces"].append(
            make_surface(
                "instruction-alias",
                alias_path,
                kind="scoped-guidance",
                authority="canonical-detail",
                consumers=["copilot"],
                file_patterns=["**/*.md"],
            )
        )
        write_manifest(self.root, self.manifest)

        errors = validator.validate(self.root)

        self.assert_error_contains(errors, instruction_path, "inventory")

    def test_scans_declared_skill_resources(self) -> None:
        skill_path = ".github/skills/example/SKILL.md"
        resource_path = ".github/skills/example/references/private.md"
        self.manifest["surfaces"].append(
            make_surface(
                "example-skill",
                skill_path,
                kind="skill",
                authority="canonical-detail",
                consumers=["codex", "claude-code"],
                tasks=["example"],
            )
        )
        write_file(self.root, skill_path, "# Example skill\n")
        write_file(
            self.root,
            resource_path,
            "Load workspace/repos.yml before continuing.\n",
        )
        write_manifest(self.root, self.manifest)

        errors = validator.validate(self.root)

        self.assert_error_contains(errors, resource_path, "workspace/repos.yml")

    def test_rejects_unreadable_inventory_directory(self) -> None:
        instructions = self.root / ".github/instructions"
        write_file(
            self.root,
            ".github/instructions/hidden.instructions.md",
            "# Hidden guidance\n",
        )
        instructions.chmod(0)
        try:
            errors = validator.validate(self.root)
        finally:
            instructions.chmod(0o700)

        self.assert_error_contains(errors, ".github/instructions", "inventory")

    def test_rejects_unreadable_skill_resource_directory(self) -> None:
        skill_path = ".github/skills/example/SKILL.md"
        resources = self.root / ".github/skills/example/references"
        self.manifest["surfaces"].append(
            make_surface(
                "example-skill",
                skill_path,
                kind="skill",
                authority="canonical-detail",
                consumers=["codex"],
                tasks=["example"],
            )
        )
        write_file(self.root, skill_path, "# Example skill\n")
        write_file(
            self.root,
            ".github/skills/example/references/private.md",
            "Read workspace/repos.yml.\n",
        )
        write_manifest(self.root, self.manifest)
        resources.chmod(0)
        try:
            errors = validator.validate(self.root)
        finally:
            resources.chmod(0o700)

        self.assert_error_contains(errors, "references", "scan skill resources")

    def test_validator_does_not_scan_itself(self) -> None:
        validator_path = "scripts/validate-agent-policy.py"
        self.manifest["surfaces"].append(
            make_surface(
                "agent-policy-validator",
                validator_path,
                kind="enforcement",
                authority="canonical-detail",
                consumers=["ci"],
                tasks=["validation"],
            )
        )
        write_file(
            self.root,
            validator_path,
            'FORBIDDEN_PUBLIC_TOKENS = ("workspace/repos.yml", "memory/")\n',
        )
        write_manifest(self.root, self.manifest)

        self.assertEqual(validator.validate(self.root), [])

    def test_rejects_relabeled_copilot_adapter(self) -> None:
        adapter = self.manifest["surfaces"][4]
        adapter["kind"] = "runbook"
        adapter["authority"] = "canonical"
        adapter["canonical_for"] = ["copilot-routing"]
        write_manifest(self.root, self.manifest)

        errors = validator.validate(self.root)

        self.assert_error_contains(errors, "copilot-adapter", "adapter-only")

    def test_errors_include_fix_command(self) -> None:
        for family in ("json", "manifest", "public", "scoped", "adapter"):
            with self.subTest(family=family):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    manifest = make_repository(root)
                    if family == "json":
                        write_file(root, ".github/instruction-surfaces.json", "{")
                    elif family == "manifest":
                        manifest["version"] = 2
                        write_manifest(root, manifest)
                    elif family == "public":
                        write_file(root, "AGENTS.md", "Read workspace/repos.yml.\n")
                    elif family == "scoped":
                        path = ".github/instructions/python.instructions.md"
                        manifest["surfaces"].append(
                            make_surface(
                                "python-guidance",
                                path,
                                kind="scoped-guidance",
                                authority="canonical-detail",
                                consumers=["copilot"],
                                file_patterns=["**/*.py"],
                            )
                        )
                        write_file(root, path, "---\n---\n# Python\n")
                        write_manifest(root, manifest)
                    else:
                        write_file(
                            root,
                            ".github/copilot-instructions.md",
                            "Additional policy.\n",
                        )

                    errors = validator.validate(root)

                    self.assertTrue(errors, f"{family} did not produce an error")
                    self.assertTrue(
                        all("; fix: " in message for message in errors),
                        f"{family} returned an error without a fix: {errors!r}",
                    )

    def test_cli_exit_codes(self) -> None:
        valid = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--root", str(self.root)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
        self.assertIn("agent policy validation passed", valid.stdout)

        self.manifest["version"] = 2
        write_manifest(self.root, self.manifest)
        invalid = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--root", str(self.root)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(invalid.returncode, 1, invalid.stdout + invalid.stderr)
        self.assertIn("ERROR: .github/instruction-surfaces.json:", invalid.stdout)

    def test_cli_rejects_json_parser_limits_without_traceback(self) -> None:
        write_file(
            self.root,
            ".github/instruction-surfaces.json",
            '{"version": ' + ("9" * 5000) + "}\n",
        )

        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--root", str(self.root)],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        self.assertNotIn("Traceback", completed.stdout + completed.stderr)
        self.assert_error_contains(
            [line.removeprefix("ERROR: ") for line in completed.stdout.splitlines()],
            ".github/instruction-surfaces.json",
            "invalid JSON",
            "fix:",
        )

    def test_cli_errors_remain_one_line_for_control_character_path(self) -> None:
        for separator in ("\n", "\u0085", "\u2028", "\u2029"):
            with self.subTest(separator=repr(separator)):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    manifest = make_repository(root)
                    manifest["surfaces"][3]["path"] = f"bad{separator}INJECTED"
                    write_manifest(root, manifest)

                    completed = subprocess.run(
                        [sys.executable, str(SCRIPT_PATH), "--root", str(root)],
                        check=False,
                        capture_output=True,
                        text=True,
                    )

                    self.assertEqual(
                        completed.returncode,
                        1,
                        completed.stdout + completed.stderr,
                    )
                    self.assertTrue(completed.stdout.splitlines())
                    self.assertTrue(
                        all(
                            line.startswith("ERROR: ")
                            for line in completed.stdout.splitlines()
                        ),
                        completed.stdout,
                    )

    def test_cli_escapes_control_characters_in_discovered_paths(self) -> None:
        cases = (
            ("inventory", "\n"),
            ("skill-resource", "\n"),
            ("inventory", "\u0085"),
            ("skill-resource", "\u2028"),
        )
        for variant, separator in cases:
            with self.subTest(variant=variant, separator=repr(separator)):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    manifest = make_repository(root)
                    if variant == "inventory":
                        write_file(
                            root,
                            f".github/instructions/bad{separator}name.instructions.md",
                            "# Undeclared guidance\n",
                        )
                    else:
                        skill_path = ".github/skills/example/SKILL.md"
                        manifest["surfaces"].append(
                            make_surface(
                                "example-skill",
                                skill_path,
                                kind="skill",
                                authority="canonical-detail",
                                consumers=["codex"],
                            )
                        )
                        write_file(root, skill_path, "# Example skill\n")
                        write_file(
                            root,
                            f".github/skills/example/bad{separator}resource.md",
                            "Read workspace/repos.yml.\n",
                        )
                        write_manifest(root, manifest)

                    expected_errors = validator.validate(root)
                    completed = subprocess.run(
                        [sys.executable, str(SCRIPT_PATH), "--root", str(root)],
                        check=False,
                        capture_output=True,
                        text=True,
                    )

                    output_lines = completed.stdout.splitlines()
                    self.assertEqual(
                        completed.returncode,
                        1,
                        completed.stdout + completed.stderr,
                    )
                    self.assertEqual(len(output_lines), len(expected_errors))
                    self.assertTrue(expected_errors)
                    self.assertTrue(
                        all(
                            "; fix: rename or remove the invalid path " in message
                            for message in expected_errors
                        ),
                        expected_errors,
                    )
                    self.assertTrue(
                        all(line.startswith("ERROR: ") for line in output_lines),
                        completed.stdout,
                    )


class PublicRepositoryTests(unittest.TestCase):
    def test_public_repository_documents_instruction_governance(self) -> None:
        adr = (
            PUBLIC_ROOT / "decisions/0014-portable-agent-instruction-architecture.md"
        ).read_text()
        self.assertIn("**Status:** PROPOSED", adr)
        self.assertIn("z-shell/.github#475", adr)

        runbook = (PUBLIC_ROOT / "runbooks/instruction-update.md").read_text()
        for question in REQUIRED_IMPACT_QUESTIONS:
            self.assertIn(question, runbook)

    def test_public_repository_has_no_validation_errors(self) -> None:
        self.assertEqual(validator.validate(PUBLIC_ROOT), [])

    def test_public_repository_uses_only_the_copilot_adapter(self) -> None:
        self.assertFalse((PUBLIC_ROOT / "CLAUDE.md").exists())
        self.assertFalse((PUBLIC_ROOT / "GEMINI.md").exists())
        self.assertFalse(
            (PUBLIC_ROOT / ".github/copilot-instructions.md").is_symlink()
        )
        self.assertEqual(
            (PUBLIC_ROOT / ".github/copilot-instructions.md").read_text(),
            "@../AGENTS.md\n",
        )


if __name__ == "__main__":
    unittest.main()
