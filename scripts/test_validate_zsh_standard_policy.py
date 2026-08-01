from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from types import ModuleType

sys.dont_write_bytecode = True
SCRIPT_PATH = Path(__file__).with_name("validate-zsh-standard-policy.py")
PUBLIC_ROOT = SCRIPT_PATH.resolve().parent.parent
EXPECTED_SHELL_DISPATCHER_SHA256 = (
    "2c02e09c25047c6a16744e6b8be17afb8817ac67eb3a4a450d347bc88e8db8e3"
)
CORE_CONTRACT_PATHS = (
    "lib/zsh-standard-policy.json",
    ".github/instruction-surfaces.json",
    ".github/instructions/zsh-scripting.instructions.md",
    ".github/instructions/shell.instructions.md",
)
CONSUMER_PATHS = (
    ".github/agents/zsh-plugin-standard-reviewer.agent.md",
    ".github/skills/new-zsh-plugin/SKILL.md",
    ".github/skills/new-zsh-plugin/templates/plugin.plugin.zsh",
    ".github/skills/zunit-test/SKILL.md",
    "PATTERNS.md",
    ".github/README.md",
)
CONTRACT_PATHS = CORE_CONTRACT_PATHS + CONSUMER_PATHS


def load_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "validate_zsh_standard_policy",
        SCRIPT_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_contract_fixture(root: Path) -> None:
    for relative_path in CONTRACT_PATHS:
        source = PUBLIC_ROOT / relative_path
        destination = root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


class ZshStandardPolicyValidatorTests(unittest.TestCase):
    def make_fixture(self) -> Path:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        root = Path(temporary_directory.name)
        copy_contract_fixture(root)
        return root

    def test_validator_module_exists(self) -> None:
        self.assertTrue(
            SCRIPT_PATH.is_file(),
            "create scripts/validate-zsh-standard-policy.py",
        )

    def read_policy(self, root: Path) -> dict[str, object]:
        return json.loads(
            (root / "lib/zsh-standard-policy.json").read_text(encoding="utf-8")
        )

    def write_policy(self, root: Path, policy: dict[str, object]) -> None:
        (root / "lib/zsh-standard-policy.json").write_text(
            json.dumps(policy, indent=2) + "\n",
            encoding="utf-8",
        )

    def instruction_rule_block(self, root: Path, rule_id: str) -> str:
        path = root / ".github/instructions/zsh-scripting.instructions.md"
        text = path.read_text(encoding="utf-8")
        marker = f"### `{rule_id}`"
        start = text.index(marker)
        end = text.find("\n### `", start + len(marker))
        if end == -1:
            end = len(text)
        return text[start:end]

    def replace_instruction_rule_metadata(
        self,
        root: Path,
        rule_id: str,
        field: str,
        values: list[str],
    ) -> None:
        path = root / ".github/instructions/zsh-scripting.instructions.md"
        text = path.read_text(encoding="utf-8")
        block = self.instruction_rule_block(root, rule_id)
        prefix = f"- {field}: "
        old_line = next(
            line for line in block.splitlines() if line.startswith(prefix)
        )
        new_line = prefix + ", ".join(f"`{value}`" for value in values)
        path.write_text(
            text.replace(block, block.replace(old_line, new_line, 1), 1),
            encoding="utf-8",
        )

    def assert_error_contains(self, errors: list[str], *needles: str) -> None:
        self.assertTrue(
            any(all(needle in message for needle in needles) for message in errors),
            f"expected one error containing {needles!r}; got {errors!r}",
        )

    def assert_dispatcher_digest_mismatch(
        self,
        errors: list[str],
        actual_digest: str,
    ) -> None:
        self.assertEqual(
            errors,
            [
                ".github/instructions/shell.instructions.md: canonical "
                "dispatcher content digest mismatch; expected sha256:"
                f"{EXPECTED_SHELL_DISPATCHER_SHA256}, got sha256:{actual_digest}; "
                "fix: restore the approved dispatcher, or after policy review "
                "update SHELL_DISPATCHER_SHA256 for the exact reviewed text"
            ],
        )

    def test_valid_fixture_has_no_errors(self) -> None:
        root = self.make_fixture()

        self.assertEqual(load_validator().validate(root), [])

    def test_declares_canonical_startup_profile(self) -> None:
        policy = self.read_policy(PUBLIC_ROOT)
        profiles = policy["execution_profiles"]
        self.assertIsInstance(profiles, dict)

        self.assertEqual(
            tuple(profiles),
            (
                "standalone-executable",
                "startup-file",
                "sourced-library",
                "autoload-function",
                "test-fixture",
            ),
        )
        self.assertEqual(
            profiles["startup-file"],
            {
                "title": "Startup file",
                "description": (
                    "A Zsh startup or shutdown file read for a defined shell "
                    "lifecycle phase that may make phase-owned effects."
                ),
            },
        )

    def test_maps_all_startup_basenames_to_startup_profile(self) -> None:
        policy = self.read_policy(PUBLIC_ROOT)
        source = policy["source_classification"]
        self.assertIsInstance(source, dict)
        startup_basenames = source["startup_basenames"]
        self.assertIsInstance(startup_basenames, list)

        self.assertEqual(
            startup_basenames,
            [
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
        )
        self.assertNotIn(
            "sourced-library",
            [item["profile"] for item in startup_basenames],
        )

    def test_startup_profile_has_exact_rule_membership(self) -> None:
        policy = self.read_policy(PUBLIC_ROOT)
        rules = policy["normative_rules"]
        self.assertIsInstance(rules, list)
        expected_rule_ids = [
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
        ]
        matching_rules = [
            rule for rule in rules if "startup-file" in rule["profiles"]
        ]

        self.assertEqual(
            [rule["id"] for rule in matching_rules],
            expected_rule_ids,
        )
        self.assertEqual(len(matching_rules), 47)
        for rule in matching_rules:
            with self.subTest(rule_id=rule["id"]):
                if rule["id"] == "zsh/completion/preserve-trust-boundaries":
                    self.assertEqual(
                        rule["profiles"],
                        ["startup-file", "autoload-function"],
                    )
                    continue
                if rule["id"] == "zsh/options/localize":
                    self.assertEqual(
                        rule["profiles"],
                        [
                            "startup-file",
                            "sourced-library",
                            "autoload-function",
                        ],
                    )
                    continue
                standalone_index = rule["profiles"].index(
                    "standalone-executable"
                )
                self.assertEqual(
                    rule["profiles"][standalone_index + 1],
                    "startup-file",
                )

    def test_registers_command_execution_as_fourteenth_source(self) -> None:
        policy = self.read_policy(PUBLIC_ROOT)
        sources = policy["documentation_sources"]
        self.assertIsInstance(sources, dict)

        self.assertEqual(len(sources), 14)
        self.assertEqual(tuple(sources)[-1], "command-execution")
        self.assertEqual(
            sources["command-execution"],
            {
                "title": "Command Execution",
                "url": (
                    "https://zsh.sourceforge.io/Doc/Release/"
                    "Command-Execution.html"
                ),
                "kind": "official-manual",
            },
        )

    def test_trust_paths_uses_exact_domain_evidence(self) -> None:
        policy = self.read_policy(PUBLIC_ROOT)
        rules = policy["normative_rules"]
        self.assertIsInstance(rules, list)
        rule = next(
            item for item in rules if item["id"] == "zsh/security/trust-paths"
        )
        expected = [
            "command-execution",
            "shell-builtins",
            "functions",
            "completion-system",
        ]

        self.assertEqual(rule["evidence"], expected)
        block = self.instruction_rule_block(
            PUBLIC_ROOT,
            "zsh/security/trust-paths",
        )
        self.assertIn(
            "- Evidence: `command-execution`, `shell-builtins`, `functions`, "
            "`completion-system`",
            block,
        )
        self.assertNotIn("`shell-grammar`", block)
        self.assertIn(
            "Trust only controlled executable search paths (`$path`), autoload "
            "search paths (`fpath`), module search paths (`$module_path`), and "
            "completion directories.",
            " ".join(block.split()),
        )

    def test_instruction_declares_five_execution_profiles(self) -> None:
        path = PUBLIC_ROOT / ".github/instructions/zsh-scripting.instructions.md"
        text = path.read_text(encoding="utf-8")
        start = text.index("## Execution-profile selection")
        end = text.index("\n## Compatibility and repository-floor model", start)
        block = text[start:end]

        self.assertIn("The five profiles are:", block)
        self.assertLess(
            block.index("`standalone-executable`"),
            block.index("`startup-file`"),
        )
        self.assertLess(
            block.index("`startup-file`"),
            block.index("`sourced-library`"),
        )
        self.assertLess(
            block.index("`sourced-library`"),
            block.index("`autoload-function`"),
        )
        self.assertLess(
            block.index("`autoload-function`"),
            block.index("`test-fixture`"),
        )
        self.assertIn("startup or shutdown file", block)
        self.assertIn("lifecycle phase", block)
        self.assertIn("may make phase-owned effects", block)
        self.assertIn("caller-preserving `sourced-library`", block)
        self.assertIn(
            "https://zsh.sourceforge.io/Doc/Release/Files.html",
            block,
        )
        self.assertNotIn("deliberately configures shell state", block)
        self.assertNotIn("intentionally changes shell state", block)

    def test_startup_rules_explain_completion_and_localization_scope(self) -> None:
        completion = " ".join(
            self.instruction_rule_block(
                PUBLIC_ROOT,
                "zsh/completion/preserve-trust-boundaries",
            ).split()
        )
        localization = " ".join(
            self.instruction_rule_block(
                PUBLIC_ROOT,
                "zsh/options/localize",
            ).split()
        )

        self.assertIn("startup file initializes completion", completion)
        self.assertIn("autoloaded completion code runs", completion)
        self.assertIn("reusable function bodies", localization)
        self.assertIn("temporary function-local work", localization)
        self.assertIn("not intentional top-level lifecycle effects", localization)

    def test_rejects_duplicate_json_keys(self) -> None:
        root = self.make_fixture()
        policy_path = root / "lib/zsh-standard-policy.json"
        policy_text = policy_path.read_text(encoding="utf-8")
        policy_path.write_text(
            policy_text.replace(
                '  "schema_version": 1,\n',
                '  "schema_version": 1,\n  "schema_version": 1,\n',
                1,
            ),
            encoding="utf-8",
        )

        errors = load_validator().validate(root)

        self.assertTrue(
            any(
                "lib/zsh-standard-policy.json: duplicate JSON key "
                "'schema_version'" in message
                for message in errors
            ),
            errors,
        )

    def test_rejects_unknown_fields(self) -> None:
        root = self.make_fixture()
        policy = self.read_policy(root)
        policy["unknown_contract"] = True
        stable_release = policy["stable_release"]
        self.assertIsInstance(stable_release, dict)
        stable_release["unknown_release"] = True
        self.write_policy(root, policy)

        errors = load_validator().validate(root)

        self.assert_error_contains(errors, "$.unknown_contract")
        self.assert_error_contains(errors, "$.stable_release.unknown_release")

    def test_rejects_invalid_release_metadata(self) -> None:
        cases = (
            ("version", "5.9.x", "$.stable_release.version"),
            ("release_date", "2026-02-30", "$.stable_release.release_date"),
            ("manual_url", "http://zsh.sourceforge.io/", "$.stable_release.manual_url"),
            (
                "semantic_review.owner",
                " ",
                "$.stable_release.semantic_review.owner",
            ),
            (
                "source_artifact.url",
                "http://zsh.sourceforge.io/zsh.tar.xz",
                "$.stable_release.source_artifact.url",
            ),
            (
                "source_artifact.sha256",
                "A" * 64,
                "$.stable_release.source_artifact.sha256",
            ),
        )
        for field, value, expected_path in cases:
            with self.subTest(field=field):
                root = self.make_fixture()
                policy = self.read_policy(root)
                stable_release = policy["stable_release"]
                self.assertIsInstance(stable_release, dict)
                if field.startswith("semantic_review."):
                    semantic_review = stable_release["semantic_review"]
                    self.assertIsInstance(semantic_review, dict)
                    semantic_review[field.removeprefix("semantic_review.")] = value
                elif field.startswith("source_artifact."):
                    stable_release["source_artifact"] = {
                        "url": "https://zsh.sourceforge.io/zsh-5.9.2.tar.xz",
                        "sha256": "a" * 64,
                    }
                    source_artifact = stable_release["source_artifact"]
                    self.assertIsInstance(source_artifact, dict)
                    source_artifact[field.removeprefix("source_artifact.")] = value
                else:
                    stable_release[field] = value
                self.write_policy(root, policy)

                errors = load_validator().validate(root)

                self.assert_error_contains(errors, expected_path)

    def test_schema_rejects_malformed_urls_and_continues(self) -> None:
        cases = (
            ("manual-url", "$.stable_release.manual_url"),
            ("release-notes-url", "$.stable_release.release_notes_url"),
            (
                "documentation-url",
                "$.documentation_sources.manual-index.url",
            ),
            ("source-artifact-url", "$.stable_release.source_artifact.url"),
        )
        module = load_validator()
        for field, expected_path in cases:
            with self.subTest(field=field):
                root = self.make_fixture()
                policy = self.read_policy(root)
                stable_release = policy["stable_release"]
                self.assertIsInstance(stable_release, dict)
                semantic_review = stable_release["semantic_review"]
                self.assertIsInstance(semantic_review, dict)
                semantic_review["owner"] = ""
                if field == "manual-url":
                    stable_release["manual_url"] = "https://["
                elif field == "release-notes-url":
                    stable_release["release_notes_url"] = "https://["
                elif field == "documentation-url":
                    sources = policy["documentation_sources"]
                    self.assertIsInstance(sources, dict)
                    source = sources["manual-index"]
                    self.assertIsInstance(source, dict)
                    source["url"] = "https://["
                else:
                    stable_release["source_artifact"] = {
                        "url": "https://[",
                        "sha256": "a" * 64,
                    }

                errors = module.validate_policy_schema(policy)

                self.assert_error_contains(errors, expected_path)
                self.assert_error_contains(
                    errors,
                    "$.stable_release.semantic_review.owner",
                )

    def test_composed_validation_reports_malformed_urls_by_field(self) -> None:
        root = self.make_fixture()
        policy = self.read_policy(root)
        stable_release = policy["stable_release"]
        self.assertIsInstance(stable_release, dict)
        stable_release["manual_url"] = "https://["
        stable_release["source_artifact"] = {
            "url": "https://[",
            "sha256": "a" * 64,
        }
        self.write_policy(root, policy)

        errors = load_validator().validate(root)

        self.assert_error_contains(errors, "$.stable_release.manual_url")
        self.assert_error_contains(errors, "$.stable_release.source_artifact.url")
        self.assertFalse(
            any(
                "validation could not inspect repository input" in message
                for message in errors
            ),
            errors,
        )

    def test_rejects_nonofficial_documentation_sources(self) -> None:
        cases = (
            ("http://zsh.sourceforge.io/Doc/Release/index.html", "manual-index"),
            ("https://example.com/zsh-manual", "manual-index"),
        )
        for url, evidence_id in cases:
            with self.subTest(url=url):
                root = self.make_fixture()
                policy = self.read_policy(root)
                sources = policy["documentation_sources"]
                self.assertIsInstance(sources, dict)
                source = sources[evidence_id]
                self.assertIsInstance(source, dict)
                source["url"] = url
                self.write_policy(root, policy)

                errors = load_validator().validate(root)

                self.assert_error_contains(errors, evidence_id)

    def test_rejects_rule_schema_and_duplicate_ids(self) -> None:
        cases = (
            ("invalid-id", lambda rule: rule.__setitem__("id", "zsh/Bad"), "$.normative_rules[0].id"),
            ("invalid-enum", lambda rule: rule.__setitem__("level", "must"), "$.normative_rules[0].level"),
            (
                "unknown-profile",
                lambda rule: rule.__setitem__("profiles", ["unknown-profile"]),
                "$.normative_rules[0].profiles",
            ),
            (
                "unknown-evidence",
                lambda rule: rule.__setitem__("evidence", ["unknown-evidence"]),
                "$.normative_rules[0].evidence",
            ),
            ("duplicate-id", None, "duplicate normative rule id"),
            (
                "duplicate-member",
                lambda rule: rule.__setitem__(
                    "enforcement",
                    [rule["enforcement"][0], rule["enforcement"][0]],
                ),
                "$.normative_rules[0].enforcement",
            ),
        )
        for name, mutation, expected in cases:
            with self.subTest(name=name):
                root = self.make_fixture()
                policy = self.read_policy(root)
                rules = policy["normative_rules"]
                self.assertIsInstance(rules, list)
                first = rules[0]
                self.assertIsInstance(first, dict)
                if name == "duplicate-id":
                    duplicate = dict(rules[1])
                    duplicate["id"] = first["id"]
                    rules[1] = duplicate
                else:
                    self.assertIsNotNone(mutation)
                    mutation(first)
                self.write_policy(root, policy)

                errors = load_validator().validate(root)

                self.assert_error_contains(errors, expected)

    def test_rejects_invalid_source_classification(self) -> None:
        def wrong_type(source: dict[str, object]) -> None:
            source["tracked_files_only"] = "true"

        def duplicate_suffix(source: dict[str, object]) -> None:
            suffixes = source["suffixes"]
            self.assertIsInstance(suffixes, list)
            suffixes.append(dict(suffixes[0]))

        def shell_suffix(source: dict[str, object]) -> None:
            suffixes = source["suffixes"]
            self.assertIsInstance(suffixes, list)
            suffixes.append({"value": ".sh", "profile": None})

        def missing_compiled_suffix(source: dict[str, object]) -> None:
            exclusions = source["exclusions"]
            self.assertIsInstance(exclusions, dict)
            exclusions["compiled_suffixes"] = []

        def reordered_globs(source: dict[str, object]) -> None:
            globs = source["path_globs"]
            self.assertIsInstance(globs, list)
            globs[0], globs[1] = globs[1], globs[0]

        def unknown_profile(source: dict[str, object]) -> None:
            suffixes = source["suffixes"]
            self.assertIsInstance(suffixes, list)
            suffix = suffixes[0]
            self.assertIsInstance(suffix, dict)
            suffix["profile"] = "unknown-profile"

        def sourced_startup_basename(source: dict[str, object]) -> None:
            startup_basenames = source["startup_basenames"]
            self.assertIsInstance(startup_basenames, list)
            startup_basename = startup_basenames[0]
            self.assertIsInstance(startup_basename, dict)
            startup_basename["profile"] = "sourced-library"

        cases = (
            (
                "wrong-type",
                wrong_type,
                ("$.source_classification.tracked_files_only",),
            ),
            (
                "duplicate-suffix",
                duplicate_suffix,
                ("$.source_classification.suffixes",),
            ),
            ("shell-suffix", shell_suffix, (".sh",)),
            (
                "missing-compiled-suffix",
                missing_compiled_suffix,
                ("$.source_classification.exclusions.compiled_suffixes",),
            ),
            (
                "reordered-glob",
                reordered_globs,
                ("$.source_classification.path_globs",),
            ),
            ("unknown-profile", unknown_profile, ("unknown-profile",)),
            (
                "sourced-startup-basename",
                sourced_startup_basename,
                (
                    "$.source_classification.startup_basenames",
                    "exact ordered source-class contract",
                ),
            ),
        )
        for name, mutation, expected_fragments in cases:
            with self.subTest(name=name):
                root = self.make_fixture()
                policy = self.read_policy(root)
                source = policy["source_classification"]
                self.assertIsInstance(source, dict)
                mutation(source)
                self.write_policy(root, policy)

                errors = load_validator().validate(root)

                self.assert_error_contains(errors, *expected_fragments)

    def test_rejects_startup_profile_out_of_canonical_order(self) -> None:
        root = self.make_fixture()
        policy = self.read_policy(root)
        profiles = policy["execution_profiles"]
        self.assertIsInstance(profiles, dict)
        startup_profile = {
            "title": "Startup file",
            "description": (
                "A Zsh startup or shutdown file that configures shell state "
                "for its lifecycle phase."
            ),
        }
        policy["execution_profiles"] = {
            "standalone-executable": profiles["standalone-executable"],
            "sourced-library": profiles["sourced-library"],
            "startup-file": startup_profile,
            "autoload-function": profiles["autoload-function"],
            "test-fixture": profiles["test-fixture"],
        }
        self.write_policy(root, policy)

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            "$.execution_profiles",
            "five canonical profiles in order",
        )

    def test_rejects_exact_startup_profile_metadata_drift(self) -> None:
        root = self.make_fixture()
        policy = self.read_policy(root)
        profiles = policy["execution_profiles"]
        self.assertIsInstance(profiles, dict)
        startup = profiles["startup-file"]
        self.assertIsInstance(startup, dict)
        startup["description"] = "Another non-empty description."
        self.write_policy(root, policy)

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            "$.execution_profiles.startup-file.description",
            "canonical profile description",
        )

    def test_rejects_coordinated_startup_membership_removal(self) -> None:
        root = self.make_fixture()
        policy = self.read_policy(root)
        rules = policy["normative_rules"]
        self.assertIsInstance(rules, list)
        rule = next(
            item for item in rules if item["id"] == "zsh/security/trust-paths"
        )
        rule["profiles"].remove("startup-file")
        self.write_policy(root, policy)
        self.replace_instruction_rule_metadata(
            root,
            "zsh/security/trust-paths",
            "Profiles",
            rule["profiles"],
        )

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            "$.normative_rules",
            "startup-file memberships",
            "exact canonical ordered rule inventory",
        )

    def test_rejects_coordinated_startup_membership_addition(self) -> None:
        root = self.make_fixture()
        policy = self.read_policy(root)
        rules = policy["normative_rules"]
        self.assertIsInstance(rules, list)
        rule = next(
            item
            for item in rules
            if item["id"] == "zsh/security/no-passive-network"
        )
        rule["profiles"].insert(0, "startup-file")
        self.write_policy(root, policy)
        self.replace_instruction_rule_metadata(
            root,
            "zsh/security/no-passive-network",
            "Profiles",
            rule["profiles"],
        )

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            "$.normative_rules",
            "startup-file memberships",
            "exact canonical ordered rule inventory",
        )

    def test_rejects_coordinated_trust_path_evidence_drift(self) -> None:
        root = self.make_fixture()
        policy = self.read_policy(root)
        rules = policy["normative_rules"]
        self.assertIsInstance(rules, list)
        rule = next(
            item for item in rules if item["id"] == "zsh/security/trust-paths"
        )
        rule["evidence"] = [
            "shell-grammar",
            "functions",
            "completion-system",
        ]
        self.write_policy(root, policy)
        self.replace_instruction_rule_metadata(
            root,
            "zsh/security/trust-paths",
            "Evidence",
            rule["evidence"],
        )

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            "$.normative_rules",
            "zsh/security/trust-paths",
            "exact canonical trust-path evidence",
        )

    def test_rejects_markdown_documentation_reference_index_drift(self) -> None:
        command_line = (
            "- `command-execution`: [Command Execution]"
            "(https://zsh.sourceforge.io/Doc/Release/Command-Execution.html)"
        )
        restricted_line = (
            "- `restricted-shell`: [Restricted Shell]"
            "(https://zsh.sourceforge.io/Doc/Release/Restricted-Shell.html)"
        )
        cases = (
            ("deletion", ""),
            (
                "reordering",
                f"{command_line}\n{restricted_line}",
            ),
            (
                "relabeling",
                command_line.replace("Command Execution", "Command Lookup"),
            ),
            (
                "wrong-url",
                command_line.replace(
                    "Command-Execution.html",
                    "Shell-Grammar.html",
                ),
            ),
            ("duplication", f"{command_line}\n{command_line}"),
            ("fenced-shadowing", f"```text\n{command_line}\n```"),
            ("commented-shadowing", f"<!-- {command_line} -->"),
        )
        for variant, replacement in cases:
            with self.subTest(variant=variant):
                root = self.make_fixture()
                path = (
                    root
                    / ".github/instructions/zsh-scripting.instructions.md"
                )
                text = path.read_text(encoding="utf-8")
                if variant == "reordering":
                    old = f"{restricted_line}\n{command_line}"
                else:
                    old = command_line
                self.assertIn(old, text)
                path.write_text(
                    text.replace(old, replacement, 1),
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    ".github/instructions/zsh-scripting.instructions.md",
                    "official documentation reference index",
                    "exact ordered registry",
                )

    def test_rejects_apply_to_drift(self) -> None:
        extra_glob = "**/drifted-zsh-source"
        for surface in ("json", "frontmatter", "manifest"):
            with self.subTest(surface=surface):
                root = self.make_fixture()
                if surface == "json":
                    policy = self.read_policy(root)
                    source = policy["source_classification"]
                    self.assertIsInstance(source, dict)
                    globs = source["path_globs"]
                    self.assertIsInstance(globs, list)
                    globs.append(extra_glob)
                    self.write_policy(root, policy)
                    expected_path = "lib/zsh-standard-policy.json"
                elif surface == "frontmatter":
                    path = root / ".github/instructions/zsh-scripting.instructions.md"
                    path.write_text(
                        path.read_text(encoding="utf-8").replace(
                            'applyTo: "',
                            f'applyTo: "{extra_glob},',
                            1,
                        ),
                        encoding="utf-8",
                    )
                    expected_path = ".github/instructions/zsh-scripting.instructions.md"
                else:
                    path = root / ".github/instruction-surfaces.json"
                    manifest = json.loads(path.read_text(encoding="utf-8"))
                    surfaces = {item["id"]: item for item in manifest["surfaces"]}
                    surfaces["instruction-zsh-scripting"]["file_patterns"][0] += (
                        f",{extra_glob}"
                    )
                    path.write_text(
                        json.dumps(manifest, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    expected_path = ".github/instruction-surfaces.json"

                errors = load_validator().validate(root)

                self.assert_error_contains(errors, expected_path, "applyTo")

    def test_rejects_manifest_shadow_and_alias_surfaces(self) -> None:
        cases = (
            ("contract-path", "path", "reuses canonical contract path"),
            (
                "canonical-ownership",
                "canonical_for",
                "reuses canonical ownership value",
            ),
            (
                "zsh-file-pattern",
                "file_patterns",
                "reuses canonical Zsh file_patterns",
            ),
            (
                "zsh-file-pattern-with-extra",
                "file_patterns_with_extra",
                "reuses canonical Zsh file_patterns",
            ),
            ("legacy-id", "id", "legacy surface id 'instruction-shell'"),
            ("duplicate-owner", "duplicate_owner", "has duplicate owners"),
        )
        for name, mutation, expected in cases:
            with self.subTest(name=name):
                root = self.make_fixture()
                path = root / ".github/instruction-surfaces.json"
                manifest = json.loads(path.read_text(encoding="utf-8"))
                surfaces = manifest["surfaces"]
                canonical_zsh = next(
                    surface
                    for surface in surfaces
                    if surface["id"] == "instruction-zsh-scripting"
                )
                shadow = {
                    "id": f"instruction-zsh-shadow-{name}",
                    "path": ".github/instructions/shadow.instructions.md",
                    "kind": "scoped-guidance",
                    "authority": "canonical-detail",
                    "consumers": ["codex"],
                    "tasks": ["shell"],
                    "file_patterns": ["**/*.shadow"],
                    "required": True,
                    "review_owner": "z-shell maintainers",
                    "canonical_for": ["shadow-guidance"],
                }
                if mutation == "path":
                    shadow["path"] = canonical_zsh["path"]
                elif mutation == "canonical_for":
                    shadow["canonical_for"] = ["zsh-scripting"]
                elif mutation == "file_patterns":
                    shadow["file_patterns"] = canonical_zsh["file_patterns"]
                elif mutation == "file_patterns_with_extra":
                    shadow["kind"] = "enforcement"
                    shadow["consumers"] = ["human", "ci"]
                    shadow["tasks"] = ["instruction-change"]
                    shadow["file_patterns"] = [
                        canonical_zsh["file_patterns"][0],
                        "**/*.shadow",
                    ]
                elif mutation == "id":
                    shadow["id"] = "instruction-shell"
                else:
                    shadow["canonical_for"] = ["zsh-standard-validation"]
                surfaces.append(shadow)
                path.write_text(
                    json.dumps(manifest, indent=2) + "\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    ".github/instruction-surfaces.json",
                    expected,
                )

    def test_rejects_markdown_rule_metadata_drift(self) -> None:
        cases = (
            ("Level", "`required`", "`recommended`"),
            (
                "Profiles",
                "`startup-file`, `sourced-library`, `autoload-function`",
                "`startup-file`, `autoload-function`",
            ),
            ("Minimum Zsh", "`null`", "`5.9.2`"),
            ("Basis", "`language-semantics`", "`mixed`"),
            ("Evidence", "`shell-builtins`, `options`", "`options`"),
            ("Enforcement", "`lint`, `runtime-test`", "`runtime-test`"),
        )
        for field, old, new in cases:
            with self.subTest(field=field):
                root = self.make_fixture()
                path = root / ".github/instructions/zsh-scripting.instructions.md"
                text = path.read_text(encoding="utf-8")
                marker = "### `zsh/options/localize`"
                start = text.index(marker)
                end = text.find("\n### `", start + len(marker))
                if end == -1:
                    end = len(text)
                block = text[start:end]
                original = f"- {field}: {old}"
                self.assertIn(original, block)
                changed = block.replace(original, f"- {field}: {new}", 1)
                path.write_text(text[:start] + changed + text[end:], encoding="utf-8")

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    "zsh/options/localize",
                    field,
                )

    def test_rejects_coordinated_normative_rule_inventory_drift(self) -> None:
        def rule_block(text: str, rule_id: str) -> tuple[int, int, str]:
            marker = f"### `{rule_id}`"
            start = text.index(marker)
            end = text.find("\n### `", start + len(marker))
            if end == -1:
                end = len(text)
            return start, end, text[start:end]

        for change in ("deletion", "insertion", "replacement", "reorder"):
            with self.subTest(change=change):
                root = self.make_fixture()
                policy = self.read_policy(root)
                rules = policy["normative_rules"]
                self.assertIsInstance(rules, list)
                instruction_path = (
                    root / ".github/instructions/zsh-scripting.instructions.md"
                )
                text = instruction_path.read_text(encoding="utf-8")
                first_id = rules[0]["id"]
                second_id = rules[1]["id"]
                self.assertIsInstance(first_id, str)
                self.assertIsInstance(second_id, str)

                if change == "deletion":
                    rules.pop(0)
                    start, end, _ = rule_block(text, first_id)
                    text = text[:start] + text[end:]
                elif change == "insertion":
                    inserted_id = "zsh/authority/inserted"
                    inserted_rule = dict(rules[0])
                    inserted_rule["id"] = inserted_id
                    rules.insert(1, inserted_rule)
                    _, end, block = rule_block(text, first_id)
                    inserted_block = block.replace(
                        f"### `{first_id}`",
                        f"### `{inserted_id}`",
                        1,
                    )
                    text = text[:end] + "\n" + inserted_block + text[end:]
                elif change == "replacement":
                    replacement_id = "zsh/authority/replacement"
                    rules[0]["id"] = replacement_id
                    text = text.replace(
                        f"### `{first_id}`",
                        f"### `{replacement_id}`",
                        1,
                    )
                else:
                    rules[0], rules[1] = rules[1], rules[0]
                    first_start, first_end, first_block = rule_block(text, first_id)
                    second_start, second_end, second_block = rule_block(
                        text, second_id
                    )
                    self.assertEqual(first_end + 1, second_start)
                    text = (
                        text[:first_start]
                        + second_block
                        + "\n"
                        + first_block
                        + text[second_end:]
                    )

                self.write_policy(root, policy)
                instruction_path.write_text(text, encoding="utf-8")

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    "$.normative_rules",
                    "exact canonical ordered inventory",
                )

    def test_instruction_qualifies_option_localization_exceptions(self) -> None:
        root = self.make_fixture()
        block = self.instruction_rule_block(root, "zsh/options/localize")
        prose = " ".join(block.split())

        for fragment in (
            "localizes most options, pattern-disable state, and signal traps",
            "`PRIVILEGED`",
            "`RESTRICTED`",
            "`POSIX_TRAPS`",
            "`LOCAL_TRAPS`",
            "Handle these exceptions explicitly",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, prose)

    def test_instruction_declares_autoload_loader_and_compilation_modes(self) -> None:
        root = self.make_fixture()
        block = self.instruction_rule_block(
            root,
            "zsh/autoload/suppress-alias-expansion",
        )

        self.assertIn("loader", block)
        self.assertIn("`autoload -Uz name`", block)
        self.assertIn("`zcompile -U -z`", block)

    def test_rejects_autoload_compilation_without_zsh_file_style(self) -> None:
        root = self.make_fixture()
        path = root / ".github/instructions/zsh-scripting.instructions.md"
        text = path.read_text(encoding="utf-8")
        text = text.replace("`zcompile -U -z`", "`zcompile -U`", 1)
        text += "\n## Unrelated compilation example\n\n`zcompile -U -z`\n"
        self.assertIn("`zcompile -U`", text)
        path.write_text(text, encoding="utf-8")

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            ".github/instructions/zsh-scripting.instructions.md",
            "zcompile -U -z",
        )

    def test_autoload_alias_rule_uses_exact_evidence(self) -> None:
        root = self.make_fixture()
        policy = self.read_policy(root)
        rules = policy["normative_rules"]
        self.assertIsInstance(rules, list)
        rule = next(
            item
            for item in rules
            if item["id"] == "zsh/autoload/suppress-alias-expansion"
        )
        block = self.instruction_rule_block(
            root,
            "zsh/autoload/suppress-alias-expansion",
        )

        self.assertEqual(rule["evidence"], ["functions", "shell-builtins"])
        self.assertIn("- Evidence: `functions`, `shell-builtins`", block)

    def test_instruction_uses_anonymous_sourced_isolation(self) -> None:
        root = self.make_fixture()
        block = self.instruction_rule_block(
            root,
            "zsh/sourced/preserve-caller-state",
        )
        prose = " ".join(block.split())

        self.assertIn("immediately executed anonymous function", prose)
        self.assertIn("() {\n  builtin emulate -L zsh", block)
        self.assertNotIn("plugin_initialize", block)

    def test_instruction_qualifies_standalone_emulation(self) -> None:
        root = self.make_fixture()
        block = self.instruction_rule_block(root, "zsh/standalone/initialize")
        prose = " ".join(block.split())

        self.assertIn(
            "`emulate -R zsh` resets settable option state to native Zsh defaults",
            prose,
        )
        self.assertIn("documented exceptions", prose)
        self.assertIn("does not clear other startup-file effects", prose)

    def test_instruction_makes_command_substitution_failure_profile_specific(
        self,
    ) -> None:
        root = self.make_fixture()
        block = self.instruction_rule_block(
            root,
            "zsh/status/preserve-command-substitution",
        )
        prose = " ".join(block.split())

        self.assertIn("function or sourced context", prose)
        self.assertIn("value=$(critical_command) || return", block)
        self.assertIn("standalone top level", prose)
        self.assertIn("value=$(critical_command) || exit", block)

    def test_instruction_uses_valid_array_boundary_command(self) -> None:
        root = self.make_fixture()
        block = self.instruction_rule_block(
            root,
            "zsh/expansion/preserve-boundaries",
        )

        self.assertIn('print -rl -- "${values[@]}"', block)
        self.assertNotIn('command -- "${values[@]}"', block)

    def test_instruction_printf_example_uses_newline_escape(self) -> None:
        root = self.make_fixture()
        block = self.instruction_rule_block(
            root,
            "zsh/output/literal-vs-formatted",
        )

        self.assertIn("printf '%s: %d\\n' \"$label\" \"$count\"", block)
        self.assertNotIn("printf '%s: %d\\\\n'", block)

    def test_native_authority_uses_precise_existing_evidence(self) -> None:
        root = self.make_fixture()
        policy = self.read_policy(root)
        rules = policy["normative_rules"]
        self.assertIsInstance(rules, list)
        rule = next(
            item
            for item in rules
            if item["id"] == "zsh/validation/native-authority"
        )
        expected = [
            "manual-index",
            "shell-grammar",
            "options",
            "shell-builtins",
        ]

        self.assertEqual(rule["evidence"], expected)
        block = self.instruction_rule_block(
            root,
            "zsh/validation/native-authority",
        )
        self.assertIn(
            "- Evidence: `manual-index`, `shell-grammar`, `options`, "
            "`shell-builtins`",
            block,
        )

    def test_ignores_fenced_or_commented_rule_blocks(self) -> None:
        wrappers = (
            ("fenced", "```markdown\n{block}```\n"),
            ("commented", "<!--\n{block}-->\n"),
        )
        for name, wrapper in wrappers:
            with self.subTest(name=name):
                root = self.make_fixture()
                path = root / ".github/instructions/zsh-scripting.instructions.md"
                text = path.read_text(encoding="utf-8")
                marker = "### `zsh/options/localize`"
                start = text.index(marker)
                end = text.find("\n### `", start + len(marker))
                self.assertNotEqual(end, -1)
                block = text[start + len(marker) : end]
                path.write_text(
                    text[:start]
                    + wrapper.format(block=f"{marker}{block}\n")
                    + text[end + 1 :],
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    ".github/instructions/zsh-scripting.instructions.md",
                    "one-to-one",
                )

    def test_rejects_noncanonical_rule_metadata_lines(self) -> None:
        cases = (
            (
                "leading-prose",
                "- Level: `required`",
                "- Level: policy says `required`",
                "Level",
            ),
            (
                "trailing-prose",
                "- Level: `required`",
                "- Level: `required` for all changes",
                "Level",
            ),
            (
                "duplicate-metadata",
                "- Enforcement: `lint`, `runtime-test`",
                "- Enforcement: `lint`, `runtime-test`\n- Level: `required`",
                "duplicate Level",
            ),
        )
        for name, old, new, expected in cases:
            with self.subTest(name=name):
                root = self.make_fixture()
                path = root / ".github/instructions/zsh-scripting.instructions.md"
                text = path.read_text(encoding="utf-8")
                marker = "### `zsh/options/localize`"
                start = text.index(marker)
                end = text.find("\n### `", start + len(marker))
                self.assertNotEqual(end, -1)
                block = text[start:end]
                self.assertIn(old, block)
                path.write_text(
                    text[:start] + block.replace(old, new, 1) + text[end:],
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    ".github/instructions/zsh-scripting.instructions.md",
                    expected,
                )

    def test_rejects_malformed_rule_headings(self) -> None:
        root = self.make_fixture()
        path = root / ".github/instructions/zsh-scripting.instructions.md"
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\n### zsh/malformed/heading\n\nUntracked rule-like prose.\n",
            encoding="utf-8",
        )

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            ".github/instructions/zsh-scripting.instructions.md",
            "malformed rule heading",
        )

    def test_declares_canonical_shell_dispatcher_digest(self) -> None:
        module = load_validator()

        self.assertEqual(
            getattr(module, "SHELL_DISPATCHER_SHA256", None),
            EXPECTED_SHELL_DISPATCHER_SHA256,
        )

    def test_rejects_unapproved_shell_dispatcher_content_drift(self) -> None:
        cases = (
            ("insertion", lambda text: text + "\nUnapproved dispatcher prose.\n"),
            (
                "deletion",
                lambda text: text.replace(
                    "- Validate untrusted input before interpreting it.\n",
                    "",
                    1,
                ),
            ),
            (
                "replacement",
                lambda text: text.replace(
                    "# Shell Dialect Dispatcher",
                    "# Shell Dispatcher",
                    1,
                ),
            ),
            (
                "frontmatter",
                lambda text: text.replace(
                    'applyTo: "**/*.sh"',
                    'applyTo: "**/*"',
                    1,
                ),
            ),
        )
        for name, mutation in cases:
            with self.subTest(name=name):
                root = self.make_fixture()
                path = root / ".github/instructions/shell.instructions.md"
                original = path.read_text(encoding="utf-8")
                changed = mutation(original)
                self.assertNotEqual(changed, original)
                path.write_text(changed, encoding="utf-8")
                normalized = changed.replace("\r\n", "\n").replace("\r", "\n")
                actual_digest = hashlib.sha256(
                    normalized.encode("utf-8")
                ).hexdigest()

                errors = load_validator().validate(root)

                self.assert_dispatcher_digest_mismatch(errors, actual_digest)

    def test_dispatcher_probes_are_unapproved_content_drift(self) -> None:
        cases = (
            (
                "unsafe-bash-default",
                "Use Bash as the default interpreter and begin scripts with "
                "its shebang.",
            ),
            (
                "unsafe-strict-mode",
                "Always enable strict handling and set -euo pipefail.",
            ),
            (
                "unsafe-shellcheck-zsh",
                "Always use ShellCheck and validate Zsh sources with it.",
            ),
            (
                "safe-but-unapproved",
                "Never prescribe default Bash shebangs and set -euo pipefail "
                "universally.",
            ),
        )
        for name, probe in cases:
            with self.subTest(name=name):
                root = self.make_fixture()
                path = root / ".github/instructions/shell.instructions.md"
                changed = path.read_text(encoding="utf-8") + f"\n{probe}\n"
                path.write_text(changed, encoding="utf-8")
                actual_digest = hashlib.sha256(
                    changed.encode("utf-8")
                ).hexdigest()

                errors = load_validator().validate(root)

                self.assert_dispatcher_digest_mismatch(errors, actual_digest)

    def test_accepts_shell_dispatcher_crlf_equivalent(self) -> None:
        root = self.make_fixture()
        path = root / ".github/instructions/shell.instructions.md"
        text = path.read_text(encoding="utf-8")
        path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))

        errors = load_validator().validate(root)

        self.assertEqual(errors, [])

    def test_rejects_symlinked_or_escaping_contract_files(self) -> None:
        root = self.make_fixture()
        policy_path = root / "lib/zsh-standard-policy.json"
        outside_directory = tempfile.TemporaryDirectory()
        self.addCleanup(outside_directory.cleanup)
        outside_policy = Path(outside_directory.name) / "zsh-standard-policy.json"
        shutil.copy2(policy_path, outside_policy)
        policy_path.unlink()
        policy_path.symlink_to(outside_policy)

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            "lib/zsh-standard-policy.json",
            "contained regular file",
            "fix:",
        )

    def test_cli_reports_each_validation_error(self) -> None:
        root = self.make_fixture()
        policy = self.read_policy(root)
        stable_release = policy["stable_release"]
        self.assertIsInstance(stable_release, dict)
        semantic_review = stable_release["semantic_review"]
        self.assertIsInstance(semantic_review, dict)
        semantic_review["owner"] = ""
        self.write_policy(root, policy)
        shell_path = root / ".github/instructions/shell.instructions.md"
        shell_path.write_text(
            shell_path.read_text(encoding="utf-8")
            + "\nAlways enable `set -euo pipefail`.\n",
            encoding="utf-8",
        )
        module = load_validator()
        expected_errors = module.validate(root)

        completed = subprocess.run(  # nosec B603
            [sys.executable, str(SCRIPT_PATH), "--root", str(root)],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(len(expected_errors), 2, expected_errors)
        self.assertEqual(expected_errors, sorted(expected_errors))
        self.assertTrue(all("\n" not in message for message in expected_errors))
        self.assert_error_contains(
            expected_errors,
            ".github/instructions/shell.instructions.md",
            "canonical dispatcher content digest mismatch",
        )
        self.assertFalse(
            any(
                "prohibited cross-dialect prescription" in message
                for message in expected_errors
            ),
            expected_errors,
        )
        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        output_lines = completed.stdout.splitlines()
        self.assertEqual(len(output_lines), 2, completed.stdout)
        self.assertEqual(
            output_lines,
            [f"ERROR: {message}" for message in expected_errors],
        )

    def test_cli_keeps_unknown_field_diagnostics_on_one_line(self) -> None:
        root = self.make_fixture()
        policy = self.read_policy(root)
        policy["bad\nINJECTED"] = True
        self.write_policy(root, policy)

        module = load_validator()
        expected_errors = module.validate(root)
        completed = subprocess.run(  # nosec B603
            [sys.executable, str(SCRIPT_PATH), "--root", str(root)],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(len(expected_errors), 1, expected_errors)
        self.assertTrue(all("\n" not in message for message in expected_errors))
        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        self.assertEqual(len(completed.stdout.splitlines()), 1, completed.stdout)

    def test_rejects_missing_consumer_canonical_link(self) -> None:
        root = self.make_fixture()
        relative_path = (
            ".github/agents/zsh-plugin-standard-reviewer.agent.md"
        )
        path = root / relative_path
        changed = path.read_text(encoding="utf-8").replace(
            ".github/instructions/zsh-scripting.instructions.md",
            ".github/instructions/missing-zsh-standard.md",
            1,
        )
        path.write_text(changed, encoding="utf-8")

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            relative_path,
            ".github/instructions/zsh-scripting.instructions.md",
            "fix:",
        )
        self.assertEqual(path.read_text(encoding="utf-8"), changed)

    def test_rejects_hidden_consumer_canonical_references(self) -> None:
        canonical_paths = (
            ".github/instructions/zsh-scripting.instructions.md",
            "lib/zsh-standard-policy.json",
        )
        reference_consumers = (
            ".github/agents/zsh-plugin-standard-reviewer.agent.md",
            ".github/skills/new-zsh-plugin/SKILL.md",
            ".github/skills/zunit-test/SKILL.md",
            "PATTERNS.md",
            ".github/README.md",
        )
        wrappers = (
            ("html-comment", "<!-- {canonical_path} -->"),
            (
                "backtick-fence",
                "```text\n{canonical_path}\n```",
            ),
            ("tilde-fence", "~~~text\n{canonical_path}\n~~~"),
        )
        for relative_path in reference_consumers:
            for canonical_path in canonical_paths:
                for wrapper_name, wrapper in wrappers:
                    with self.subTest(
                        relative_path=relative_path,
                        canonical_path=canonical_path,
                        wrapper=wrapper_name,
                    ):
                        root = self.make_fixture()
                        path = root / relative_path
                        text = path.read_text(encoding="utf-8")
                        self.assertIn(canonical_path, text)
                        changed = text.replace(
                            canonical_path,
                            "missing-canonical-reference",
                        )
                        changed += (
                            "\n\n"
                            + wrapper.format(canonical_path=canonical_path)
                            + "\n"
                        )
                        path.write_text(changed, encoding="utf-8")

                        errors = load_validator().validate(root)

                        self.assert_error_contains(
                            errors,
                            relative_path,
                            canonical_path,
                            "fix:",
                        )
                        self.assertEqual(
                            path.read_text(encoding="utf-8"),
                            changed,
                        )

    def test_rejects_container_fenced_or_indented_canonical_references(
        self,
    ) -> None:
        relative_path = ".github/skills/new-zsh-plugin/SKILL.md"
        canonical_paths = (
            ".github/instructions/zsh-scripting.instructions.md",
            "lib/zsh-standard-policy.json",
        )
        wrappers = (
            (
                "list-fence",
                "- ```text\n  {canonical_path}\n  ```",
            ),
            (
                "blockquote-fence",
                "> ```text\n> {canonical_path}\n> ```",
            ),
            ("four-space-code", "    {canonical_path}"),
            ("tab-code", "\t{canonical_path}"),
        )
        for canonical_path in canonical_paths:
            for wrapper_name, wrapper in wrappers:
                with self.subTest(
                    canonical_path=canonical_path,
                    wrapper=wrapper_name,
                ):
                    root = self.make_fixture()
                    path = root / relative_path
                    text = path.read_text(encoding="utf-8")
                    self.assertIn(canonical_path, text)
                    changed = text.replace(
                        canonical_path,
                        "missing-canonical-reference",
                    )
                    changed += (
                        "\n\n"
                        + wrapper.format(canonical_path=canonical_path)
                        + "\n"
                    )
                    path.write_text(changed, encoding="utf-8")

                    errors = load_validator().validate(root)

                    self.assert_error_contains(
                        errors,
                        relative_path,
                        canonical_path,
                        "fix:",
                    )

    def test_rejects_consumer_canonical_ownership(self) -> None:
        cases = (
            ("authority", "canonical"),
            ("canonical_for", ["zsh-plugin-review"]),
        )
        for field, value in cases:
            with self.subTest(field=field):
                root = self.make_fixture()
                path = root / ".github/instruction-surfaces.json"
                manifest = json.loads(path.read_text(encoding="utf-8"))
                surface = next(
                    item
                    for item in manifest["surfaces"]
                    if item["path"]
                    == ".github/agents/zsh-plugin-standard-reviewer.agent.md"
                )
                surface[field] = value
                path.write_text(
                    json.dumps(manifest, indent=2) + "\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                expected = "advisory" if field == "authority" else "canonical_for"
                self.assert_error_contains(
                    errors,
                    ".github/agents/zsh-plugin-standard-reviewer.agent.md",
                    expected,
                    "fix:",
                )

    def test_rejects_coordinated_consumer_manifest_path_drift(self) -> None:
        root = self.make_fixture()
        original_path = (
            ".github/agents/zsh-plugin-standard-reviewer.agent.md"
        )
        drifted_path = ".github/agents/drifted-zsh-reviewer.agent.md"
        (root / original_path).rename(root / drifted_path)
        manifest_path = root / ".github/instruction-surfaces.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        surface = next(
            item for item in manifest["surfaces"] if item["path"] == original_path
        )
        surface["path"] = drifted_path
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            original_path,
            "exactly one manifest surface",
            "fix:",
        )

    def test_rejects_consumer_rule_definition_heading(self) -> None:
        relative_path = ".github/skills/new-zsh-plugin/SKILL.md"
        cases = (
            ("plain", "### zsh/options/localize"),
            ("backticked", "### `zsh/options/localize`"),
        )
        for name, heading in cases:
            with self.subTest(name=name):
                root = self.make_fixture()
                path = root / relative_path
                path.write_text(
                    path.read_text(encoding="utf-8")
                    + f"\n{heading}\n\nDuplicated normative prose.\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    relative_path,
                    "rules belong in canonical instruction",
                    "fix:",
                )

        wrappers = (
            ("fenced", "```markdown\n### `zsh/options/localize`\n```\n"),
            ("commented", "<!--\n### zsh/options/localize\n-->\n"),
        )
        for name, addition in wrappers:
            with self.subTest(name=name):
                root = self.make_fixture()
                path = root / relative_path
                path.write_text(
                    path.read_text(encoding="utf-8") + "\n" + addition,
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assertEqual(errors, [])

    def test_rejects_valid_atx_h3_rule_heading_variants(self) -> None:
        relative_path = ".github/skills/new-zsh-plugin/SKILL.md"
        visible_headings = (
            "   ### zsh/options/localize",
            "### zsh/options/localize ###",
            " ### `zsh/options/localize`",
            "  ### `zsh/options/localize` ##",
            "   ### `zsh/options/localize` ###",
            "### ``zsh/options/localize`` ###   ",
            "### zsh/options/localize <!-- visible note -->",
        )
        for heading in visible_headings:
            with self.subTest(heading=heading):
                root = self.make_fixture()
                path = root / relative_path
                path.write_text(
                    path.read_text(encoding="utf-8")
                    + f"\n{heading}\n\nDuplicated normative prose.\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    relative_path,
                    "rules belong in canonical instruction",
                    "fix:",
                )

        invisible_or_code = (
            "    ### zsh/options/localize",
            "\t### zsh/options/localize",
            "## zsh/options/localize",
            "#### zsh/options/localize",
            "### zsh/options/localize guidance",
            "### zsh/options/localize###",
            "Inline `zsh/options/localize` citation.",
            "```markdown\n   ### `zsh/options/localize` ###\n```",
            "~~~markdown\n   ### `zsh/options/localize` ###\n~~~",
            "<!--\n   ### zsh/options/localize ###\n-->",
        )
        for addition in invisible_or_code:
            with self.subTest(non_heading=addition):
                root = self.make_fixture()
                path = root / relative_path
                path.write_text(
                    path.read_text(encoding="utf-8") + "\n" + addition + "\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assertEqual(errors, [])

        visible_after_literal_content = (
            "    ```markdown\n### zsh/options/localize",
            "```markdown\n<!-- literal comment\n```\n### zsh/options/localize",
        )
        for addition in visible_after_literal_content:
            with self.subTest(visible_after_literal_content=addition):
                root = self.make_fixture()
                path = root / relative_path
                path.write_text(
                    path.read_text(encoding="utf-8") + "\n" + addition + "\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    relative_path,
                    "rules belong in canonical instruction",
                    "fix:",
                )

    def test_container_fences_hide_only_their_normative_h3_content(
        self,
    ) -> None:
        relative_path = ".github/skills/new-zsh-plugin/SKILL.md"
        container_fences = (
            (
                "list",
                "- ```markdown\n  ### `zsh/options/localize`\n  ```",
            ),
            (
                "blockquote",
                "> ```markdown\n> ### `zsh/options/localize`\n> ```",
            ),
            (
                "list-blank",
                (
                    "- ```markdown\n"
                    "  hidden\n\n"
                    "  ### `zsh/options/localize`\n"
                    "  ```"
                ),
            ),
        )
        for container, fenced in container_fences:
            with self.subTest(container=container, content="hidden"):
                root = self.make_fixture()
                path = root / relative_path
                path.write_text(
                    path.read_text(encoding="utf-8") + "\n" + fenced + "\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assertEqual(errors, [])

            with self.subTest(container=container, content="visible-after"):
                root = self.make_fixture()
                path = root / relative_path
                path.write_text(
                    path.read_text(encoding="utf-8")
                    + "\n"
                    + fenced
                    + "\n### zsh/options/localize\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    relative_path,
                    "rules belong in canonical instruction",
                    "fix:",
                )

    def test_visual_column_and_continuation_fences_reprocess_visible_h3(
        self,
    ) -> None:
        validator = load_validator()
        rule_heading = "### `zsh/options/localize`"
        hidden_cases = (
            "- item\n  ```markdown\n  " + rule_heading + "\n  ```",
            "- ```markdown\n  " + rule_heading + "\n  ```",
            "-  ```markdown\n   " + rule_heading + "\n   ```",
            "-   ```markdown\n    " + rule_heading + "\n    ```",
            "-    ```markdown\n     " + rule_heading + "\n     ```",
            "> \t```markdown\n>   " + rule_heading + "\n>   ```",
            "- > ```markdown\n  > " + rule_heading + "\n  > ```",
            "> - ```markdown\n>   " + rule_heading + "\n>   ```",
        )
        for source in hidden_cases:
            with self.subTest(source=source):
                visible = validator._visible_markdown_lines(source)
                hidden_line_numbers = {
                    line_number
                    for line_number, line in enumerate(
                        source.splitlines(),
                        start=1,
                    )
                    if "zsh/options/localize" in line
                }
                self.assertTrue(hidden_line_numbers)
                self.assertTrue(
                    hidden_line_numbers.isdisjoint(
                        line_number for line_number, _ in visible
                    )
                )

                root = self.make_fixture()
                relative_path = ".github/skills/new-zsh-plugin/SKILL.md"
                path = root / relative_path
                path.write_text(
                    path.read_text(encoding="utf-8") + "\n" + source + "\n",
                    encoding="utf-8",
                )
                errors = validator.validate(root)
                self.assertFalse(
                    any(
                        message.startswith(f"{relative_path}:")
                        and "rules belong in canonical instruction" in message
                        for message in errors
                    ),
                    errors,
                )

        visible_cases = (
            "- item\n  ```markdown\n  hidden\n" + rule_heading,
            "- \t```markdown\n    <!-- literal\n    hidden\n    ```\n" + rule_heading,
            "-     ```markdown\n" + rule_heading,
        )
        for source in visible_cases:
            with self.subTest(source=source):
                visible = validator._visible_markdown_lines(source)
                self.assertIn(rule_heading, [line for _, line in visible])

    def test_repair_2_consumer_parser_outputs_match_frozen_golden(self) -> None:
        validator = load_validator()
        paths = (
            ".github/instructions/zsh-scripting.instructions.md",
            ".github/agents/zsh-plugin-standard-reviewer.agent.md",
            ".github/skills/new-zsh-plugin/SKILL.md",
            ".github/skills/new-zsh-plugin/templates/plugin.plugin.zsh",
            ".github/skills/zunit-test/SKILL.md",
            "PATTERNS.md",
            ".github/README.md",
        )
        instruction = (PUBLIC_ROOT / paths[0]).read_text(encoding="utf-8")
        snapshot = {
            "visible": {
                path: validator._visible_markdown_lines(
                    (PUBLIC_ROOT / path).read_text(encoding="utf-8")
                )
                for path in paths
            },
            "documentation_registry": (
                validator._documentation_reference_index_errors(instruction)
            ),
            "rule_blocks": {
                rule_id: validator._visible_markdown_rule_block(
                    instruction,
                    rule_id,
                )
                for rule_id in validator.NORMATIVE_RULE_IDS
            },
            "parsed_rules": validator._markdown_rules(instruction),
        }
        self.assertEqual(len(snapshot["rule_blocks"]), 59)
        digest = hashlib.sha256(
            json.dumps(
                snapshot,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()

        self.assertEqual(
            digest,
            "e85e0a71f0eb957efd9293e8dc1aa7e428163e0ec693f265e2fcff2bb4135d8b",
        )

    def test_rejects_list_and_nested_container_rule_headings(self) -> None:
        relative_path = ".github/skills/new-zsh-plugin/SKILL.md"
        additions = (
            "- ### zsh/options/localize",
            "- ### `zsh/options/localize`",
            "1. ### `zsh/options/localize`",
            "1. ### zsh/options/localize",
            "- > ### zsh/options/localize",
            "- > ### `zsh/options/localize`",
            "> - ### `zsh/options/localize`",
            "> - ### zsh/options/localize",
            "- item\n  ### `zsh/options/localize`",
            "-  item\n   ### `zsh/options/localize`",
            "-   item\n    ### `zsh/options/localize`",
            "-    item\n     ### `zsh/options/localize`",
            "-\n  ### `zsh/options/localize`",
            "1.\n   ### `zsh/options/localize`",
        )
        for addition in additions:
            with self.subTest(addition=addition):
                root = self.make_fixture()
                path = root / relative_path
                path.write_text(
                    path.read_text(encoding="utf-8") + f"\n\n{addition}\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    relative_path,
                    "rules belong in canonical instruction",
                    "fix:",
                )

    def test_container_prefix_paths_do_linear_suffix_work(self) -> None:
        validator = load_validator()
        for depth in (4_000, 8_000, 16_000, 32_000):
            with self.subTest(depth=depth):
                line = "> " * depth + "### `zsh/options/localize`"
                work = [0]
                content, containers = validator._markdown_container_view(
                    line,
                    work=work,
                )
                self.assertEqual(content, "### `zsh/options/localize`")
                self.assertEqual(len(containers), depth)
                self.assertLessEqual(work[0], 16 * len(line) + 64)
                self.assertGreaterEqual(
                    work[0],
                    2 * len(line) + len(content),
                )

                fence_work = [0]
                fence_content = validator._fence_container_content(
                    line,
                    containers,
                    work=fence_work,
                )
                self.assertEqual(fence_content, "### `zsh/options/localize`")
                self.assertLessEqual(fence_work[0], 16 * len(line) + 64)
                self.assertGreaterEqual(
                    fence_work[0],
                    2 * len(line) + len(fence_content),
                )

                active = (("list", 2),) + containers
                active_line = "  " + line
                active_work = [0]
                active_content, resolved = validator._resolve_markdown_container_view(
                    active_line,
                    active,
                    work=active_work,
                )
                self.assertEqual(active_content, "### `zsh/options/localize`")
                self.assertEqual(resolved, active)
                self.assertLessEqual(
                    active_work[0],
                    16 * len(active_line) + 64,
                )
                self.assertGreaterEqual(
                    active_work[0],
                    2 * len(active_line) + len(active_content),
                )

        active = (("list", 2), ("blockquote", 0), ("blockquote", 0))
        content, resolved = validator._resolve_markdown_container_view(
            "  > visible",
            active,
        )
        self.assertEqual(content, "visible")
        self.assertEqual(resolved, active[:2])

        for tab_count in (4_000, 8_000, 16_000):
            with self.subTest(tab_count=tab_count):
                tab_line = "\t" * tab_count + "visible"
                tab_work = [0]
                tab_content, tab_containers = (
                    validator._resolve_markdown_container_view(
                        tab_line,
                        (("list", 4),),
                        work=tab_work,
                    )
                )
                self.assertTrue(tab_content.endswith("visible"))
                self.assertEqual(tab_containers, (("list", 4),))
                self.assertLessEqual(
                    tab_work[0],
                    16 * len(tab_line) + 64,
                )

    def test_whitespace_only_lines_preserve_empty_markdown_content(self) -> None:
        validator = load_validator()
        for source in (" ", "  ", "   "):
            with self.subTest(source=repr(source)):
                self.assertEqual(
                    validator._markdown_container_view(source),
                    ("", ()),
                )

        active_list = (("list", 2),)
        active_nested = active_list + (("blockquote", 0),)
        for source in (" ", "  ", "   "):
            with self.subTest(container="list", source=repr(source)):
                self.assertEqual(
                    validator._resolve_markdown_container_view(
                        "  " + source,
                        active_list,
                    ),
                    ("", active_list),
                )
            with self.subTest(container="blockquote", source=repr(source)):
                self.assertEqual(
                    validator._markdown_container_view("> " + source),
                    ("", (("blockquote", 0),)),
                )
            with self.subTest(container="nested", source=repr(source)):
                self.assertEqual(
                    validator._resolve_markdown_container_view(
                        "  > " + source,
                        active_nested,
                    ),
                    ("", active_nested),
                )

        root = self.make_fixture()
        path = root / ".github/README.md"
        path.write_text(
            path.read_text(encoding="utf-8") + "\n \n  \n   \n",
            encoding="utf-8",
        )
        self.assertEqual(load_validator().validate(root), [])

    def test_positive_markdown_state_distinguishes_indented_content(
        self,
    ) -> None:
        validator = load_validator()
        canonical_path = ".github/instructions/zsh-scripting.instructions.md"
        source = (
            "Ordinary paragraph reference:\n"
            f"    {canonical_path}\n\n"
            f"    hidden/{canonical_path}\n\n"
            "1. Blank-separated list reference\n\n"
            f"   listed/{canonical_path}\n"
        )

        visible = validator._visible_markdown_lines(source)
        positive_lines = validator._positive_markdown_lines(visible)
        positive = validator._positive_visible_text(visible)

        self.assertIn(
            f"    {canonical_path}",
            [line for _, line in positive_lines],
        )
        self.assertNotIn(f"hidden/{canonical_path}", positive)
        self.assertIn(f"listed/{canonical_path}", positive)

    def test_visible_paragraph_and_blank_list_continuations_satisfy_references(
        self,
    ) -> None:
        relative_path = ".github/skills/new-zsh-plugin/SKILL.md"
        cases = (
            (
                ".github/instructions/zsh-scripting.instructions.md",
                (
                    "Visible canonical instruction reference:\n"
                    "    .github/instructions/zsh-scripting.instructions.md"
                ),
            ),
            (
                "lib/zsh-standard-policy.json",
                (
                    "1. Visible canonical policy reference\n\n"
                    "   lib/zsh-standard-policy.json"
                ),
            ),
        )
        for canonical_path, addition in cases:
            with self.subTest(canonical_path=canonical_path):
                root = self.make_fixture()
                path = root / relative_path
                text = path.read_text(encoding="utf-8")
                self.assertIn(canonical_path, text)
                path.write_text(
                    text.replace(canonical_path, "removed-canonical-path")
                    + f"\n\n{addition}\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                missing_reference_errors = [
                    message
                    for message in errors
                    if message.startswith(f"{relative_path}:")
                    and "missing visible canonical Zsh reference" in message
                    and canonical_path in message
                ]
                self.assertEqual(missing_reference_errors, [], errors)

    def test_rejects_indented_blockquote_paragraph_contradiction(self) -> None:
        root = self.make_fixture()
        relative_path = ".github/README.md"
        path = root / relative_path
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\n\n> Zsh standard validation is\n>     inactive.\n",
            encoding="utf-8",
        )

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            relative_path,
            "Phase 1 Zsh validation",
            "fix:",
        )

        container_breakouts = (
            (
                "list",
                "- ```markdown\n  hidden\n### zsh/options/localize",
            ),
            (
                "blockquote",
                "> ```markdown\n> hidden\n### zsh/options/localize",
            ),
            (
                "blockquote-blank",
                (
                    "> ```markdown\n"
                    "> hidden\n\n"
                    "> ### zsh/options/localize"
                ),
            ),
        )
        for container, breakout in container_breakouts:
            with self.subTest(container=container, content="breakout"):
                root = self.make_fixture()
                path = root / relative_path
                path.write_text(
                    path.read_text(encoding="utf-8")
                    + "\n"
                    + breakout
                    + "\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    relative_path,
                    "rules belong in canonical instruction",
                    "fix:",
                )

    def test_rejects_blockquoted_h3_and_invalid_backtick_fence_opener(
        self,
    ) -> None:
        relative_path = ".github/skills/new-zsh-plugin/SKILL.md"
        additions = (
            "> ### zsh/options/localize",
            "> ### `zsh/options/localize`",
            (
                "```markdown`invalid\n"
                "### zsh/options/localize\n"
                "```"
            ),
            (
                "-     ```markdown\n"
                "### zsh/options/localize"
            ),
        )
        for addition in additions:
            with self.subTest(addition=addition):
                root = self.make_fixture()
                path = root / relative_path
                path.write_text(
                    path.read_text(encoding="utf-8")
                    + "\n"
                    + addition
                    + "\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    relative_path,
                    "rules belong in canonical instruction",
                    "fix:",
                )

    def test_code_span_normalization_keeps_doubled_edge_spaces(self) -> None:
        root = self.make_fixture()
        relative_path = ".github/skills/new-zsh-plugin/SKILL.md"
        path = root / relative_path
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\n### `  zsh/options/localize  `\n",
            encoding="utf-8",
        )

        errors = load_validator().validate(root)

        self.assertEqual(errors, [])

    def test_block_boundaries_do_not_make_indented_references_visible(
        self,
    ) -> None:
        relative_path = ".github/agents/zsh-plugin-standard-reviewer.agent.md"
        canonical_path = ".github/instructions/zsh-scripting.instructions.md"
        hidden_references = (
            (
                "fenced-block",
                "Visible paragraph\n```text\nhidden\n```\n"
                f"    {canonical_path}",
            ),
            (
                "blank-blockquote",
                "> Visible paragraph\n>\n"
                f">     {canonical_path}",
            ),
            (
                "thematic-break",
                "Visible paragraph\n---\n"
                f"    {canonical_path}",
            ),
            (
                "empty-unordered-item",
                "Visible paragraph\n-\n"
                f"    {canonical_path}",
            ),
            (
                "top-level-fence-after-list",
                "- List paragraph\n```text\nhidden\n```\n"
                f"    {canonical_path}",
            ),
            (
                "setext-h1",
                "Visible heading\n===\n"
                f"    {canonical_path}",
            ),
            (
                "link-reference-definition",
                "[canonical]: https://example.test/reference\n"
                f"    {canonical_path}",
            ),
            (
                "html-block",
                "<div>\n"
                f"    {canonical_path}\n"
                "</div>",
            ),
            (
                "html-script-block",
                "<script>\n"
                f"    {canonical_path}\n"
                "</script>",
            ),
            (
                "html-pre-block",
                "<pre>\n"
                f"    {canonical_path}\n"
                "</pre>",
            ),
            (
                "html-style-block",
                "<style>\n"
                f"    {canonical_path}\n"
                "</style>",
            ),
            (
                "html-textarea-block",
                "<textarea>\n"
                f"    {canonical_path}\n"
                "</textarea>",
            ),
            (
                "html-processing-instruction",
                "<?target\n"
                f"    {canonical_path}\n"
                "?>",
            ),
            (
                "html-declaration",
                "<!DOCTYPE html\n"
                f"    {canonical_path}\n"
                ">",
            ),
            (
                "html-lowercase-declaration",
                "<!doctype html\n"
                f"    {canonical_path}\n"
                ">",
            ),
            (
                "html-raw-blockquote-looking-line",
                "<script>\n"
                f"> {canonical_path}\n"
                "</script>",
            ),
            (
                "html-raw-list-looking-line",
                "<script>\n"
                f"- {canonical_path}\n"
                "</script>",
            ),
            (
                "html-cdata",
                "<![CDATA[\n"
                f"    {canonical_path}\n"
                "]]>",
            ),
            (
                "html-custom-tag",
                "<custom-element>\n"
                f"    {canonical_path}\n"
                "</custom-element>",
            ),
            (
                "split-link-destination",
                "[canonical]:\n"
                f"  {canonical_path}",
            ),
            (
                "split-link-title",
                "[canonical]: /target\n"
                f"  \"{canonical_path}\"",
            ),
            (
                "multiline-link-title",
                "[canonical]: /target\n"
                "  \"title\n"
                f"  {canonical_path}\"",
            ),
            (
                "escaped-link-label",
                f"[can\\]onical]: {canonical_path}",
            ),
            (
                "multiline-link-label",
                "[\n"
                f"{canonical_path}\n"
                "]: /target",
            ),
            (
                "indented-code-after-multiline-link-label",
                "[\n"
                "canonical\n"
                "]: /target\n"
                f"    {canonical_path}",
            ),
            (
                "blockquote-empty-unordered-item",
                "> -\n"
                f">     {canonical_path}",
            ),
            (
                "blockquote-empty-ordered-item",
                "> 1.\n"
                f">     {canonical_path}",
            ),
        )
        for boundary, hidden_reference in hidden_references:
            with self.subTest(boundary=boundary):
                root = self.make_fixture()
                path = root / relative_path
                text = path.read_text(encoding="utf-8")
                self.assertIn(canonical_path, text)
                changed = text.replace(canonical_path, "moved-zsh-standard", 1)
                path.write_text(
                    changed + "\n\n" + hidden_reference + "\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    relative_path,
                    canonical_path,
                    "fix:",
                )

    def test_list_owned_fence_preserves_visible_reference_continuations(
        self,
    ) -> None:
        relative_path = ".github/agents/zsh-plugin-standard-reviewer.agent.md"
        canonical_path = ".github/instructions/zsh-scripting.instructions.md"
        for indentation in range(2, 6):
            with self.subTest(indentation=indentation):
                root = self.make_fixture()
                path = root / relative_path
                text = path.read_text(encoding="utf-8")
                self.assertIn(canonical_path, text)
                changed = text.replace(canonical_path, "moved-zsh-standard", 1)
                changed += (
                    "\n\n- list paragraph\n"
                    "  ```text\n"
                    "  hidden\n"
                    "  ```\n"
                    + " " * indentation
                    + canonical_path
                    + "\n"
                )
                path.write_text(changed, encoding="utf-8")

                errors = load_validator().validate(root)

                missing_reference_errors = [
                    message
                    for message in errors
                    if message.startswith(f"{relative_path}:")
                    and "missing visible canonical Zsh reference" in message
                    and canonical_path in message
                ]
                self.assertEqual(missing_reference_errors, [], errors)

    def test_leaf_blocks_cannot_supply_structural_headings(self) -> None:
        rule_id = "zsh/options/localize"
        consumer_path = ".github/skills/new-zsh-plugin/SKILL.md"
        hidden_h3_blocks = (
            f"<div>\n### `{rule_id}`\n</div>",
            f"<script>\n### `{rule_id}`\n</script>",
            f"<custom-element>\n### `{rule_id}`\n</custom-element>",
        )
        for hidden_h3 in hidden_h3_blocks:
            with self.subTest(kind=hidden_h3.splitlines()[0]):
                root = self.make_fixture()
                path = root / consumer_path
                path.write_text(
                    path.read_text(encoding="utf-8")
                    + "\n\n"
                    + hidden_h3
                    + "\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assertFalse(
                    any(
                        message.startswith(f"{consumer_path}:")
                        and "rules belong in canonical instruction" in message
                        for message in errors
                    ),
                    errors,
                )

        interrupting_h3_blocks = (
            f"[reference]: /target \"\n### `{rule_id}`\n\"",
            f"[\n### `{rule_id}`\n]: /target",
            f"<!-- --> ```\n### `{rule_id}`",
            f"<!--\n--> ```\n### `{rule_id}`",
            f"- <script>\n- ### `{rule_id}`",
        )
        for interrupting_h3 in interrupting_h3_blocks:
            with self.subTest(kind=interrupting_h3.splitlines()[0]):
                root = self.make_fixture()
                path = root / consumer_path
                path.write_text(
                    path.read_text(encoding="utf-8")
                    + "\n\n"
                    + interrupting_h3
                    + "\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    consumer_path,
                    "rules belong in canonical instruction",
                    "fix:",
                )

        readme_path = ".github/README.md"
        required_paths = (
            ".github/instructions/zsh-scripting.instructions.md\n"
            "lib/zsh-standard-policy.json\n"
            "scripts/validate-zsh-standard-policy.py"
        )
        hidden_h2_blocks = (
            "<div>\n## Instruction Architecture\n{paths}\n</div>",
            "<script>\n## Instruction Architecture\n{paths}\n</script>",
            "<custom-element>\n## Instruction Architecture\n{paths}\n</custom-element>",
        )
        for hidden_h2 in hidden_h2_blocks:
            with self.subTest(kind=hidden_h2.splitlines()[0]):
                root = self.make_fixture()
                path = root / readme_path
                text = path.read_text(encoding="utf-8")
                changed = text.replace(
                    "## Instruction Architecture",
                    "## Moved Instruction Architecture",
                    1,
                )
                path.write_text(
                    changed
                    + "\n\n"
                    + hidden_h2.format(paths=required_paths)
                    + "\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    readme_path,
                    "Instruction Architecture",
                    "scripts/validate-zsh-standard-policy.py",
                    "fix:",
                )

    def test_malformed_blocks_do_not_hide_visible_canonical_references(
        self,
    ) -> None:
        relative_path = ".github/agents/zsh-plugin-standard-reviewer.agent.md"
        canonical_path = ".github/instructions/zsh-scripting.instructions.md"
        visible_references = (
            (
                "type-7-tag-interrupting-paragraph",
                "Visible paragraph\n"
                "<custom-element>\n"
                f"    {canonical_path}\n"
                "</custom-element>",
            ),
            (
                "fence-marker-inside-raw-html",
                "<script>\n"
                "```text\n"
                "</script>\n"
                f"{canonical_path}",
            ),
            (
                "raw-html-any-type-1-end-tag",
                "<script>\n"
                "</pre>\n"
                f"{canonical_path}",
            ),
            (
                "reference-title-with-trailing-content",
                f"[{canonical_path}]: /target \"title\" trailing",
            ),
            (
                "reference-without-destination",
                f"[{canonical_path}]:",
            ),
            (
                "reference-title-with-blank-line",
                "[canonical]: /target \"title\n"
                f"  {canonical_path}\n\n"
                "closing title\"",
            ),
            (
                "multiline-label-with-blank-line",
                "[\n"
                f"{canonical_path}\n\n"
                "]: /target",
            ),
            (
                "multiline-label-with-setext-heading",
                "[\n"
                f"{canonical_path}\n"
                "===\n"
                "]: /target",
            ),
        )
        for boundary, visible_reference in visible_references:
            with self.subTest(boundary=boundary):
                root = self.make_fixture()
                path = root / relative_path
                text = path.read_text(encoding="utf-8")
                self.assertIn(canonical_path, text)
                changed = text.replace(canonical_path, "moved-zsh-standard", 1)
                path.write_text(
                    changed + "\n\n" + visible_reference + "\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                missing_reference_errors = [
                    message
                    for message in errors
                    if message.startswith(f"{relative_path}:")
                    and "missing visible canonical Zsh reference" in message
                    and canonical_path in message
                ]
                self.assertEqual(missing_reference_errors, [], errors)

    def test_rejects_copied_normative_rule_inventory(self) -> None:
        root = self.make_fixture()
        relative_path = ".github/skills/zunit-test/SKILL.md"
        path = root / relative_path
        policy = self.read_policy(root)
        rules = policy["normative_rules"]
        self.assertIsInstance(rules, list)
        copied_ids = "\n".join(
            f"- `{item['id']}`" for item in rules if isinstance(item, dict)
        )
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\n## Copied catalog\n\n"
            + copied_ids
            + "\n",
            encoding="utf-8",
        )

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            relative_path,
            "complete catalog duplication",
            "fix:",
        )

    def test_rejects_nonconforming_plugin_template(self) -> None:
        root = self.make_fixture()
        relative_path = (
            ".github/skills/new-zsh-plugin/templates/plugin.plugin.zsh"
        )
        path = root / relative_path
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\n# TODO: restore this marker\n"
            + "# https://example.test/#funtions-directory\n",
            encoding="utf-8",
        )

        errors = load_validator().validate(root)

        self.assert_error_contains(errors, relative_path, "TODO", "fix:")
        self.assert_error_contains(
            errors,
            relative_path,
            "#funtions-directory",
            "fix:",
        )

    def test_rejects_noncanonical_patterns_contract(self) -> None:
        root = self.make_fixture()
        relative_path = "PATTERNS.md"
        path = root / relative_path
        text = path.read_text(encoding="utf-8")
        changed = text.replace(
            "Patterns below are observed examples, not a\nsecond policy source.",
            "Patterns below define the policy.",
            1,
        )
        self.assertNotEqual(changed, text)
        path.write_text(changed, encoding="utf-8")

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            relative_path,
            "observed patterns are non-normative",
            "fix:",
        )

    def test_rejects_hidden_patterns_contract_with_visible_override(self) -> None:
        relative_path = "PATTERNS.md"
        old_contract = (
            "Patterns below are observed examples, not a\n"
            "second policy source. When an observed pattern conflicts with a "
            "required rule,\n"
            "the canonical standard wins and the pattern must be corrected."
        )
        hidden_contract = (
            "Patterns below are observed examples, not a second policy source. "
            "the canonical standard wins and the pattern must be corrected."
        )
        wrappers = (
            ("html-comment", f"<!-- {hidden_contract} -->"),
            ("backtick-fence", f"```text\n{hidden_contract}\n```"),
            ("tilde-fence", f"~~~text\n{hidden_contract}\n~~~"),
        )
        for wrapper_name, wrapper in wrappers:
            with self.subTest(wrapper=wrapper_name):
                root = self.make_fixture()
                path = root / relative_path
                text = path.read_text(encoding="utf-8")
                self.assertIn(old_contract, text)
                changed = text.replace(
                    old_contract,
                    "Patterns below are mandatory and override the canonical "
                    "Zsh owners.",
                    1,
                )
                changed += f"\n\n{wrapper}\n"
                path.write_text(changed, encoding="utf-8")

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    relative_path,
                    "observed patterns are non-normative",
                    "fix:",
                )

    def test_rejects_patterns_contract_hidden_in_container_fence(
        self,
    ) -> None:
        relative_path = "PATTERNS.md"
        old_contract = (
            "Patterns below are observed examples, not a\n"
            "second policy source. When an observed pattern conflicts with a "
            "required rule,\n"
            "the canonical standard wins and the pattern must be corrected."
        )
        hidden_contract = (
            "Patterns below are observed examples, not a second policy source. "
            "the canonical standard wins and the pattern must be corrected."
        )
        wrappers = (
            (
                "list",
                f"- ```text\n  {hidden_contract}\n  ```",
            ),
            (
                "blockquote",
                f"> ```text\n> {hidden_contract}\n> ```",
            ),
        )
        for container, wrapper in wrappers:
            with self.subTest(container=container):
                root = self.make_fixture()
                path = root / relative_path
                text = path.read_text(encoding="utf-8")
                self.assertIn(old_contract, text)
                changed = text.replace(
                    old_contract,
                    "Patterns below are mandatory and override the canonical "
                    "Zsh owners.\n\n"
                    + wrapper,
                    1,
                )
                path.write_text(changed, encoding="utf-8")

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    relative_path,
                    "observed patterns are non-normative",
                    "fix:",
                )

    def test_rejects_retired_patterns_contract_mutations(self) -> None:
        relative_path = "PATTERNS.md"
        fancy_owner = "z-shell/zsh-fancy-completions"
        fancy_evidence = f"{fancy_owner}:zsh-fancy-completions.plugin.zsh"
        section_contracts = {
            "Plugin entry-point skeleton": (
                (
                    "z-shell/zsh-eza:zsh-eza.plugin.zsh",
                    fancy_evidence,
                    "z-shell/z-a-meta-plugins:z-a-meta-plugins.plugin.zsh",
                ),
                (
                    "zsh/context/select-profile",
                    "zsh/sourced/preserve-caller-state",
                ),
            ),
            "Register the repository directory in `Plugins`": (
                (
                    "z-shell/zsh-eza:zsh-eza.plugin.zsh",
                    fancy_evidence,
                    "z-shell/z-a-meta-plugins:z-a-meta-plugins.plugin.zsh",
                ),
                (
                    "zsh/plugin/document-global-state",
                    "zsh/plugin/restore-state",
                ),
            ),
            "Guard `fpath` additions": (
                (
                    fancy_evidence,
                    "z-shell/z-a-meta-plugins:z-a-meta-plugins.plugin.zsh",
                    "z-shell/zsh-eza:zsh-eza.plugin.zsh",
                ),
                (
                    "zsh/security/trust-paths",
                    "zsh/plugin/restore-state",
                ),
            ),
        }
        for title, (evidence, rule_ids) in section_contracts.items():
            evidence_mutations = tuple(
                (
                    f"missing-evidence-{index}",
                    f"- `{repository}`\n",
                    "",
                )
                for index, repository in enumerate(evidence)
            ) + tuple(
                (
                    f"duplicate-evidence-{index}",
                    f"- `{repository}`\n",
                    f"- `{repository}`\n- `{repository}`\n",
                )
                for index, repository in enumerate(evidence)
            ) + tuple(
                (
                    f"extra-evidence-{marker_name}",
                    f"- `{evidence[-1]}`\n",
                    f"- `{evidence[-1]}`\n{marker} "
                    "`z-shell/unevidenced:replacement.plugin.zsh`\n",
                )
                for marker_name, marker in (
                    ("asterisk", "*"),
                    ("plus", "+"),
                    ("ordered-period", "1."),
                    ("ordered-parenthesis", "1)"),
                )
            )
            mutations = (
                evidence_mutations
                + (
                    ("status", "Status: retired.", "Status: active."),
                    (
                        "duplicate-status",
                        "Status: retired.",
                        "Status: retired.\n\nStatus: retired.",
                    ),
                    (
                        "instruction-route",
                        ".github/instructions/zsh-scripting.instructions.md",
                        ".github/instructions/missing-zsh-standard.md",
                    ),
                    (
                        "template-route",
                        ".github/skills/new-zsh-plugin/templates/plugin.plugin.zsh",
                        ".github/skills/new-zsh-plugin/templates/missing.plugin.zsh",
                    ),
                    (
                        "instruction-route-suffix",
                        ".github/instructions/zsh-scripting.instructions.md",
                        ".github/instructions/zsh-scripting.instructions.md.bak",
                    ),
                    (
                        "template-route-suffix",
                        ".github/skills/new-zsh-plugin/templates/plugin.plugin.zsh",
                        ".github/skills/new-zsh-plugin/templates/plugin.plugin.zsh.bak",
                    ),
                )
                + tuple(
                    (
                        f"rule-id-{index}",
                        rule_id,
                        f"zsh/missing/retired-rule-{index}",
                    )
                    for index, rule_id in enumerate(rule_ids)
                )
                + tuple(
                    (
                        f"rule-id-suffix-{index}",
                        rule_id,
                        f"{rule_id}-extra",
                    )
                    for index, rule_id in enumerate(rule_ids)
                )
            )
            for mutation, old, new in mutations:
                with self.subTest(title=title, mutation=mutation):
                    root = self.make_fixture()
                    path = root / relative_path
                    text = path.read_text(encoding="utf-8")
                    start = text.index(f"## {title}")
                    end = text.find("\n## ", start + 3)
                    if end == -1:
                        end = len(text)
                    section = text[start:end]
                    self.assertIn(old, section)
                    changed_section = section.replace(old, new, 1)
                    path.write_text(
                        text[:start] + changed_section + text[end:],
                        encoding="utf-8",
                    )

                    errors = load_validator().validate(root)

                    self.assert_error_contains(
                        errors,
                        relative_path,
                        title,
                        "retired section contract",
                        "fix:",
                    )

    def test_rejects_code_blocks_in_retired_patterns_sections(self) -> None:
        relative_path = "PATTERNS.md"
        section_names = (
            "Plugin entry-point skeleton",
            "Register the repository directory in `Plugins`",
            "Guard `fpath` additions",
        )
        additions = (
            "```\nreplacement\n```",
            "~~~zsh\nreplacement\n~~~",
            "```text\nreplacement\n```",
            "- ```zsh\n  replacement\n  ```",
            "> ~~~zsh\n> replacement\n> ~~~",
            "    replacement_code",
            "Visible paragraph\n---\n    replacement_code",
            "Visible paragraph\n-\n    replacement_code",
            "> Visible paragraph\n>\n>     replacement_code",
        )
        for title in section_names:
            for addition in additions:
                with self.subTest(title=title, addition=addition):
                    root = self.make_fixture()
                    path = root / relative_path
                    text = path.read_text(encoding="utf-8")
                    start = text.index(f"## {title}")
                    end = text.find("\n## ", start + 3)
                    if end == -1:
                        end = len(text)
                    path.write_text(
                        text[:end] + f"\n\n{addition}\n" + text[end:],
                        encoding="utf-8",
                    )

                    errors = load_validator().validate(root)

                    self.assert_error_contains(
                        errors,
                        relative_path,
                        title,
                        "must not publish replacement code",
                        "fix:",
                    )

    def test_allows_prose_in_retired_patterns_sections(self) -> None:
        root = self.make_fixture()
        relative_path = "PATTERNS.md"
        path = root / relative_path
        text = path.read_text(encoding="utf-8")
        title = "Plugin entry-point skeleton"
        start = text.index(f"## {title}")
        end = text.find("\n## ", start + 3)
        self.assertNotEqual(end, -1)
        addition = (
            "\n\nAllowed explanatory prose names `inline_identifier` and continues\n"
            "    with a deliberately indented paragraph line.\n"
        )
        path.write_text(text[:end] + addition + text[end:], encoding="utf-8")

        self.assertEqual(load_validator().validate(root), [])

    def test_requires_consumer_contracts_in_intended_sections(self) -> None:
        patterns_root = self.make_fixture()
        patterns_path = patterns_root / "PATTERNS.md"
        patterns_text = patterns_path.read_text(encoding="utf-8")
        patterns_contract = (
            "Patterns below are observed examples, not a\n"
            "second policy source. When an observed pattern conflicts with a "
            "required rule,\n"
            "the canonical standard wins and the pattern must be corrected."
        )
        self.assertIn(patterns_contract, patterns_text)
        patterns_path.write_text(
            patterns_text.replace(patterns_contract, "", 1)
            + f"\n\n{patterns_contract}\n",
            encoding="utf-8",
        )

        errors = load_validator().validate(patterns_root)

        self.assert_error_contains(
            errors,
            "PATTERNS.md",
            "observed patterns are non-normative",
            "fix:",
        )

        readme_path = ".github/README.md"
        section_cases = (
            (
                "Repository Structure",
                (
                    ".github/instructions/zsh-scripting.instructions.md",
                    "lib/zsh-standard-policy.json",
                ),
            ),
            (
                "Instruction Architecture",
                (
                    ".github/instructions/zsh-scripting.instructions.md",
                    "lib/zsh-standard-policy.json",
                    "scripts/validate-zsh-standard-policy.py",
                ),
            ),
        )
        for section_title, required_paths in section_cases:
            for required_path in required_paths:
                with self.subTest(
                    section=section_title,
                    required_path=required_path,
                ):
                    root = self.make_fixture()
                    path = root / readme_path
                    text = path.read_text(encoding="utf-8")
                    section_start = text.index(f"## {section_title}")
                    next_h2 = text.find("\n## ", section_start + 3)
                    section_end = len(text) if next_h2 == -1 else next_h2
                    section = text[section_start:section_end]
                    self.assertIn(required_path, section)
                    changed_section = section.replace(
                        required_path,
                        "moved-contract-path",
                    )
                    changed = (
                        text[:section_start]
                        + changed_section
                        + text[section_end:]
                        + f"\n\nVisible moved reference: `{required_path}`.\n"
                    )
                    path.write_text(changed, encoding="utf-8")

                    errors = load_validator().validate(root)

                    self.assert_error_contains(
                        errors,
                        readme_path,
                        section_title,
                        required_path,
                        "fix:",
                    )

    def test_rejects_incomplete_public_catalog(self) -> None:
        root = self.make_fixture()
        relative_path = ".github/README.md"
        path = root / relative_path
        text = path.read_text(encoding="utf-8")
        changed = text.replace(
            "scripts/validate-zsh-standard-policy.py",
            "scripts/deferred-zsh-standard-validator.py",
        )
        self.assertNotEqual(changed, text)
        path.write_text(changed, encoding="utf-8")

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            relative_path,
            "scripts/validate-zsh-standard-policy.py",
            "fix:",
        )

    def test_rejects_hidden_or_misplaced_public_validator_catalog(self) -> None:
        relative_path = ".github/README.md"
        validator_path = "scripts/validate-zsh-standard-policy.py"
        wrappers = (
            ("html-comment", f"<!-- {validator_path} -->"),
            ("backtick-fence", f"```text\n{validator_path}\n```"),
            ("tilde-fence", f"~~~text\n{validator_path}\n~~~"),
        )
        for wrapper_name, wrapper in wrappers:
            with self.subTest(wrapper=wrapper_name):
                root = self.make_fixture()
                path = root / relative_path
                text = path.read_text(encoding="utf-8")
                self.assertIn(validator_path, text)
                changed = text.replace(
                    validator_path,
                    "scripts/missing-zsh-standard-validator.py",
                )
                changed += f"\n\n{wrapper}\n"
                path.write_text(changed, encoding="utf-8")

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    relative_path,
                    validator_path,
                    "fix:",
                )

        root = self.make_fixture()
        path = root / relative_path
        text = path.read_text(encoding="utf-8")
        section_start = text.index("## Instruction Architecture")
        section_end = text.index("\n### Community Health Files", section_start)
        section = text[section_start:section_end]
        self.assertIn(validator_path, section)
        changed_section = section.replace(
            validator_path,
            "scripts/missing-zsh-standard-validator.py",
        )
        changed = (
            text[:section_start]
            + changed_section
            + text[section_end:]
            + f"\n\nVisible unrelated mention: `{validator_path}`.\n"
        )
        path.write_text(changed, encoding="utf-8")

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            relative_path,
            validator_path,
            "fix:",
        )

    def test_rejects_container_fenced_or_indented_readme_catalog_path(
        self,
    ) -> None:
        relative_path = ".github/README.md"
        validator_path = "scripts/validate-zsh-standard-policy.py"
        wrappers = (
            (
                "list-fence",
                f"- ```text\n  {validator_path}\n  ```",
            ),
            (
                "blockquote-fence",
                f"> ```text\n> {validator_path}\n> ```",
            ),
            ("four-space-code", f"    {validator_path}"),
            ("tab-code", f"\t{validator_path}"),
        )
        for wrapper_name, wrapper in wrappers:
            with self.subTest(wrapper=wrapper_name):
                root = self.make_fixture()
                path = root / relative_path
                text = path.read_text(encoding="utf-8")
                section_start = text.index("## Instruction Architecture")
                section_end = text.find("\n## ", section_start + 3)
                if section_end == -1:
                    section_end = len(text)
                section = text[section_start:section_end]
                self.assertIn(validator_path, section)
                changed_section = section.replace(
                    validator_path,
                    "scripts/missing-zsh-standard-validator.py",
                )
                changed = (
                    text[:section_start]
                    + changed_section
                    + "\n\n"
                    + wrapper
                    + "\n"
                    + text[section_end:]
                )
                path.write_text(changed, encoding="utf-8")

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    relative_path,
                    "Instruction Architecture",
                    validator_path,
                    "fix:",
                )

    def test_rejects_blockquoted_readme_catalog_section_heading(self) -> None:
        root = self.make_fixture()
        relative_path = ".github/README.md"
        path = root / relative_path
        text = path.read_text(encoding="utf-8")
        changed = text.replace(
            "## Instruction Architecture",
            "## Moved Instruction Architecture",
            1,
        )
        changed += (
            "\n\n> ## Instruction Architecture\n>\n"
            "> .github/instructions/zsh-scripting.instructions.md\n"
            "> lib/zsh-standard-policy.json\n"
            "> scripts/validate-zsh-standard-policy.py\n"
        )
        path.write_text(changed, encoding="utf-8")

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            relative_path,
            "Instruction Architecture",
            "scripts/validate-zsh-standard-policy.py",
            "fix:",
        )

    def test_empty_h2_ends_readme_catalog_section(self) -> None:
        root = self.make_fixture()
        relative_path = ".github/README.md"
        validator_path = "scripts/validate-zsh-standard-policy.py"
        path = root / relative_path
        text = path.read_text(encoding="utf-8")
        section_start = text.index("## Instruction Architecture")
        validator_index = text.index(validator_path, section_start)
        validator_line_start = text.rfind("\n", section_start, validator_index) + 1
        changed = (
            text[:validator_line_start]
            + "## \n"
            + text[validator_line_start:]
        )
        path.write_text(changed, encoding="utf-8")

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            relative_path,
            "Instruction Architecture",
            validator_path,
            "fix:",
        )

    def test_two_blank_lines_end_list_ownership_in_readme_section(self) -> None:
        root = self.make_fixture()
        relative_path = ".github/README.md"
        validator_path = "scripts/validate-zsh-standard-policy.py"
        path = root / relative_path
        text = path.read_text(encoding="utf-8")
        section_start = text.index("## Instruction Architecture")
        section_end = text.index("\n## Shared Actions", section_start)
        section = text[section_start:section_end]
        validator_line_start = section.rfind("\n", 0, section.index(validator_path))
        validator_line_end = section.index("\n", section.index(validator_path))
        changed_section = (
            section[:validator_line_start]
            + section[validator_line_end:]
            + "\n- list paragraph\n\n\n"
            + "  ## Unrelated Section\n"
            + f"  {validator_path}\n"
        )
        path.write_text(
            text[:section_start] + changed_section + text[section_end:],
            encoding="utf-8",
        )

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            relative_path,
            "Instruction Architecture",
            validator_path,
            "fix:",
        )

    def test_list_continuation_h2_cannot_anchor_readme_section(self) -> None:
        relative_path = ".github/README.md"
        attacks = (
            "- ## Instruction Architecture\n  {paths}",
            "- item\n  ## Instruction Architecture\n  {paths}",
            "-  item\n   ## Instruction Architecture\n   {paths}",
            "-   item\n    ## Instruction Architecture\n    {paths}",
            "-    item\n     ## Instruction Architecture\n     {paths}",
            "-\n  ## Instruction Architecture\n  {paths}",
            "1.\n   ## Instruction Architecture\n   {paths}",
        )
        paths = (
            ".github/instructions/zsh-scripting.instructions.md\n"
            "lib/zsh-standard-policy.json\n"
            "scripts/validate-zsh-standard-policy.py"
        )
        for attack in attacks:
            with self.subTest(attack=attack.splitlines()[0]):
                root = self.make_fixture()
                path = root / relative_path
                text = path.read_text(encoding="utf-8")
                changed = text.replace(
                    "## Instruction Architecture",
                    "## Moved Instruction Architecture",
                    1,
                )
                indent = attack.split("{paths}", 1)[0].splitlines()[-1]
                indent = indent[: len(indent) - len(indent.lstrip())]
                changed += "\n\n" + attack.format(
                    paths=paths.replace("\n", "\n" + indent)
                ) + "\n"
                path.write_text(changed, encoding="utf-8")

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    relative_path,
                    "Instruction Architecture",
                    "scripts/validate-zsh-standard-policy.py",
                    "fix:",
                )

    def test_list_continuation_h2_cannot_anchor_retired_section(self) -> None:
        root = self.make_fixture()
        relative_path = "PATTERNS.md"
        title = "Plugin entry-point skeleton"
        path = root / relative_path
        text = path.read_text(encoding="utf-8")
        changed = text.replace(f"## {title}", f"## Moved {title}", 1)
        section_start = text.index(f"## {title}")
        section_end = text.index("\n## ", section_start + 3)
        section_body = text[section_start:section_end].split("\n", 1)[1]
        listed_section = "\n".join(
            "  " + line if line else "" for line in section_body.splitlines()
        )
        changed += f"\n\n- wrapper\n  ## {title}\n{listed_section}\n"
        path.write_text(changed, encoding="utf-8")

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            relative_path,
            title,
            "retired section contract",
            "fix:",
        )

    def test_rejects_inactive_or_future_phase_zsh_validation_claims(self) -> None:
        relative_path = ".github/README.md"
        claims = (
            "Zsh standard validation is inactive.",
            "Zsh standard validation is not implemented.",
            "Zsh standard enforcement is planned for a later phase.",
            "Zsh standard validation will begin in a future phase.",
            "Validation of the Zsh standard remains currently inactive.",
            "The Zsh standard validator has not yet been implemented.",
            "Zsh standard enforcement is deferred until a later phase.",
            "Zsh standard enforcement is deferred to a later phase.",
        )
        for claim in claims:
            with self.subTest(claim=claim):
                root = self.make_fixture()
                path = root / relative_path
                path.write_text(
                    path.read_text(encoding="utf-8") + f"\n\n{claim}\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    relative_path,
                    "Phase 1 Zsh validation",
                    "fix:",
                )

    def test_rejects_wrapped_blockquote_zsh_validation_claim(self) -> None:
        root = self.make_fixture()
        relative_path = ".github/README.md"
        path = root / relative_path
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\n\n> Zsh standard validation is\n> inactive.\n",
            encoding="utf-8",
        )

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            relative_path,
            "Phase 1 Zsh validation",
            "fix:",
        )

    def test_allows_scoped_or_unrelated_readme_phase_language(self) -> None:
        relative_path = ".github/README.md"
        allowed_claims = (
            "Zsh standard validation is active.",
            "Zsh standard validation is not implemented by ShellCheck.",
            (
                "Zsh standard validation is active; classifier enforcement is "
                "planned for a later phase."
            ),
            (
                "Future-phase child enrollment is not implemented; Zsh "
                "standard validation is active."
            ),
            "Do not describe Zsh standard validation as inactive.",
            (
                "The validator reports inactive plugins while Zsh standard "
                "validation remains active."
            ),
            (
                "The Zsh standard validator is available; maintenance "
                "automation will begin in a future phase."
            ),
            (
                "Zsh standard validation is planned for a later phase in "
                "downstream repositories, while Phase 1 validation here is active."
            ),
        )
        for claim in allowed_claims:
            with self.subTest(claim=claim):
                root = self.make_fixture()
                path = root / relative_path
                path.write_text(
                    path.read_text(encoding="utf-8") + f"\n\n{claim}\n",
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                contradiction_errors = [
                    message
                    for message in errors
                    if message.startswith(f"{relative_path}:")
                    and "Phase 1 Zsh validation" in message
                ]
                self.assertEqual(contradiction_errors, [], errors)

    def test_rendered_plugin_template_restores_lifecycle_state(self) -> None:
        template_path = (
            PUBLIC_ROOT
            / ".github/skills/new-zsh-plugin/templates/plugin.plugin.zsh"
        )
        temporary_path: Path
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            plugin_root = temporary_path / "plugin [literal]*? space"
            functions_path = plugin_root / "functions"
            functions_path.mkdir(parents=True)
            entry_path = plugin_root / "demo.plugin.zsh"
            rendered = (
                template_path.read_text(encoding="utf-8")
                .replace("__NAME__", "demo")
                .replace("__KEY__", "DEMO")
                .replace("__FPATH_VAR__", "DEMO_FPATH")
            )
            entry_path.write_text(rendered, encoding="utf-8")

            environment = os.environ.copy()
            environment.pop("ZERO", None)
            try:
                syntax = subprocess.run(  # nosec B603
                    ["zsh", "-f", "-n", str(entry_path)],
                    check=False,
                    capture_output=True,
                    text=True,
                    env=environment,
                    timeout=10,
                )
            except subprocess.TimeoutExpired as exc:
                self.fail(
                    f"template syntax timed out after {exc.timeout} seconds"
                )
            self.assertEqual(
                syntax.returncode,
                0,
                syntax.stdout + syntax.stderr,
            )

            common = textwrap.dedent(
                r"""
                check_fpath() {
                  builtin emulate -L zsh
                  local actual=${(j:|:)fpath}
                  local expected=${(j:|:)argv}
                  [[ $actual == $expected ]] || {
                    print -u2 -r -- "fpath mismatch: actual=${actual} expected=${expected}"
                    return 1
                  }
                }

                check_scaffold_removed() {
                    (( ! ${+functions[demo_plugin_unload]} )) &&
                    (( ! ${+parameters[DEMO_FPATH]} )) &&
                    (( ! ${+parameters[DEMO_FPATH_ADDED]} )) &&
                    (( ! ${+parameters[DEMO_FPATH_PLUGINS_KEY_EXISTED]} )) &&
                    (( ! ${+parameters[DEMO_FPATH_PLUGINS_KEY_VALUE]} ))
                }

                unset PMSPEC
                """
            )
            cases = {
                "default-native": textwrap.dedent(
                    r"""
                    typeset -ga fpath=( /baseline )
                    typeset -gA Plugins=( OTHER caller-other )
                    unset PMSPEC
                    . "$1" || exit 10
                    check_fpath /baseline "$2" || exit 11
                    [[ ${Plugins[DEMO]} == ${1:h} ]] || exit 12
                    (( DEMO_FPATH_ADDED == 1 )) || exit 13
                    demo_plugin_unload || exit 14
                    check_fpath /baseline || exit 15
                    (( ! ${+Plugins[DEMO]} )) || exit 16
                    [[ ${Plugins[OTHER]} == caller-other ]] || exit 17
                    check_scaffold_removed || exit 18
                    """
                ),
                "preexisting-single": textwrap.dedent(
                    r"""
                    typeset -ga fpath=( "$2" /tail )
                    typeset -gA Plugins
                    . "$1" || exit 20
                    (( DEMO_FPATH_ADDED == 0 )) || exit 21
                    check_fpath "$2" /tail || exit 22
                    demo_plugin_unload || exit 23
                    check_fpath "$2" /tail || exit 24
                    check_scaffold_removed || exit 25
                    """
                ),
                "preexisting-duplicates": textwrap.dedent(
                    r"""
                    typeset -ga fpath=( "$2" /middle "$2" )
                    typeset -gA Plugins
                    . "$1" || exit 30
                    (( DEMO_FPATH_ADDED == 0 )) || exit 31
                    demo_plugin_unload || exit 32
                    check_fpath "$2" /middle "$2" || exit 33
                    check_scaffold_removed || exit 34
                    """
                ),
                "unset-pmspec-no-unset": textwrap.dedent(
                    r"""
                    setopt no_unset
                    typeset -ga fpath=( /baseline )
                    typeset -gA Plugins
                    unset PMSPEC
                    . "$1" || exit 40
                    [[ ! -o UNSET ]] || exit 41
                    demo_plugin_unload || exit 42
                    [[ ! -o UNSET ]] || exit 43
                    check_fpath /baseline || exit 44
                    check_scaffold_removed || exit 45
                    """
                ),
                "caller-ksh-arrays": textwrap.dedent(
                    r"""
                    setopt ksh_arrays
                    typeset -ga fpath=( "$2" /tail )
                    typeset -gA Plugins
                    . "$1" || exit 50
                    [[ -o KSH_ARRAYS ]] || exit 51
                    check_fpath "$2" /tail || exit 52
                    demo_plugin_unload || exit 53
                    [[ -o KSH_ARRAYS ]] || exit 54
                    check_fpath "$2" /tail || exit 55
                    check_scaffold_removed || exit 56
                    """
                ),
                "caller-no-function-argzero": textwrap.dedent(
                    r"""
                    unsetopt function_argzero
                    typeset caller_zero=$0
                    typeset -ga fpath=( /baseline )
                    typeset -gA Plugins
                    . "$1" || exit 60
                    [[ ! -o FUNCTION_ARGZERO ]] || exit 61
                    [[ $0 == "$caller_zero" ]] || exit 62
                    [[ ${Plugins[DEMO]} == ${1:h} ]] || exit 63
                    demo_plugin_unload || exit 64
                    [[ ! -o FUNCTION_ARGZERO ]] || exit 65
                    [[ $0 == "$caller_zero" ]] || exit 66
                    check_fpath /baseline || exit 67
                    check_scaffold_removed || exit 68
                    """
                ),
                "repeated-source": textwrap.dedent(
                    r"""
                    typeset -ga fpath=( /baseline )
                    typeset -gA Plugins
                    . "$1" || exit 70
                    (( DEMO_FPATH_ADDED == 1 )) || exit 71
                    . "$1" || exit 72
                    (( DEMO_FPATH_ADDED == 1 )) || exit 73
                    check_fpath /baseline "$2" || exit 74
                    demo_plugin_unload || exit 75
                    check_fpath /baseline || exit 76
                    (( ! ${+Plugins[DEMO]} )) || exit 77
                    check_scaffold_removed || exit 78
                    """
                ),
                "preexisting-plugin-key": textwrap.dedent(
                    r"""
                    typeset -ga fpath=( /baseline )
                    typeset -gA Plugins=(
                      DEMO 'caller original [literal]*? value'
                      OTHER caller-other
                    )
                    . "$1" || exit 80
                    [[ ${Plugins[DEMO]} == ${1:h} ]] || exit 81
                    . "$1" || exit 82
                    demo_plugin_unload || exit 83
                    [[ ${Plugins[DEMO]} == 'caller original [literal]*? value' ]] ||
                      exit 84
                    [[ ${Plugins[OTHER]} == caller-other ]] || exit 85
                    check_fpath /baseline || exit 86
                    check_scaffold_removed || exit 87
                    """
                ),
                "equal-entry-inserted-before-owned-append": textwrap.dedent(
                    r"""
                    typeset -ga fpath=( /baseline )
                    typeset -gA Plugins
                    . "$1" || exit 90
                    fpath=( "$2" "${fpath[@]}" )
                    check_fpath "$2" /baseline "$2" || exit 91
                    demo_plugin_unload || exit 92
                    check_fpath "$2" /baseline || exit 93
                    check_scaffold_removed || exit 94
                    """
                ),
                "loader-handled-first-source": textwrap.dedent(
                    r"""
                    typeset -ga fpath=( /baseline )
                    typeset -gA Plugins
                    PMSPEC=f
                    . "$1" || exit 100
                    (( DEMO_FPATH_ADDED == 0 )) || exit 101
                    check_fpath /baseline || exit 102
                    unset PMSPEC
                    . "$1" || exit 103
                    (( DEMO_FPATH_ADDED == 0 )) || exit 104
                    check_fpath /baseline || exit 105
                    demo_plugin_unload || exit 106
                    check_fpath /baseline || exit 107
                    (( ! ${+Plugins[DEMO]} )) || exit 108
                    check_scaffold_removed || exit 109
                    """
                ),
            }
            for case_name, body in cases.items():
                with self.subTest(case=case_name):
                    home = temporary_path / f"home-{case_name}"
                    zdotdir = temporary_path / f"zdot-{case_name}"
                    home.mkdir()
                    zdotdir.mkdir()
                    child_environment = environment.copy()
                    child_environment.update(
                        {
                            "HOME": str(home),
                            "ZDOTDIR": str(zdotdir),
                        }
                    )
                    try:
                        completed = subprocess.run(  # nosec B603
                            [
                                "zsh",
                                "-f",
                                "-c",
                                common + body,
                                case_name,
                                str(entry_path),
                                str(functions_path),
                            ],
                            check=False,
                            capture_output=True,
                            text=True,
                            env=child_environment,
                            timeout=10,
                        )
                    except subprocess.TimeoutExpired as exc:
                        self.fail(
                            f"{case_name} timed out after "
                            f"{exc.timeout} seconds"
                        )
                    self.assertEqual(
                        completed.returncode,
                        0,
                        completed.stdout + completed.stderr,
                    )

        self.assertFalse(
            temporary_path.exists(),
            "TemporaryDirectory must remove the rendered template tree",
        )

    def test_consumer_contract_uses_safe_text_reads(self) -> None:
        root = self.make_fixture()
        relative_path = ".github/skills/zunit-test/SKILL.md"
        path = root / relative_path
        outside_directory = tempfile.TemporaryDirectory()
        self.addCleanup(outside_directory.cleanup)
        outside_path = Path(outside_directory.name) / "SKILL.md"
        shutil.copy2(path, outside_path)
        path.unlink()
        path.symlink_to(outside_path)

        errors = load_validator().validate(root)

        self.assert_error_contains(
            errors,
            relative_path,
            "contained regular file",
            "fix:",
        )

    def test_consumer_contract_defers_to_malformed_manifest_error(self) -> None:
        root = self.make_fixture()
        relative_path = ".github/instruction-surfaces.json"
        (root / relative_path).write_text("{", encoding="utf-8")

        errors = load_validator().validate(root)
        manifest_errors = [
            message for message in errors if message.startswith(f"{relative_path}:")
        ]

        self.assertEqual(len(manifest_errors), 1, errors)
        self.assertIn("malformed JSON", manifest_errors[0])


class PublicZshStandardContractTests(unittest.TestCase):
    def test_public_zsh_consumers_defer_to_canonical_standard(self) -> None:
        canonical_path = (
            ".github/instructions/zsh-scripting.instructions.md"
        )
        policy_path = "lib/zsh-standard-policy.json"
        consumers = (
            ".github/agents/zsh-plugin-standard-reviewer.agent.md",
            ".github/skills/new-zsh-plugin/SKILL.md",
            ".github/skills/zunit-test/SKILL.md",
            "PATTERNS.md",
            ".github/README.md",
        )
        for relative_path in consumers:
            text = (PUBLIC_ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn(canonical_path, text, relative_path)
            self.assertIn(policy_path, text, relative_path)

        reviewer = (
            PUBLIC_ROOT / ".github/agents/zsh-plugin-standard-reviewer.agent.md"
        ).read_text(encoding="utf-8")
        for fragment in (
            "severity",
            "rule ID",
            "evidence ID",
            "execution profile",
            "consequence",
            "smallest safe correction",
        ):
            with self.subTest(reviewer_finding_field=fragment):
                self.assertIn(fragment, reviewer)

        new_plugin_skill = (
            PUBLIC_ROOT / ".github/skills/new-zsh-plugin/SKILL.md"
        ).read_text(encoding="utf-8")
        for fragment in (
            "sourced-library",
            "autoload-function",
            "isolated",
            "invoke `<name>_plugin_unload`",
            "assert post-unload restoration",
        ):
            with self.subTest(new_plugin_contract=fragment):
                self.assertIn(fragment, new_plugin_skill)

        zunit_skill = (
            PUBLIC_ROOT / ".github/skills/zunit-test/SKILL.md"
        ).read_text(encoding="utf-8")
        for fragment in (
            "test-fixture",
            "zsh/test/isolate-environment",
            "zsh/test/match-production-profile",
            "zsh/plugin/restore-state",
            "Declare each intentional negative fixture",
        ):
            with self.subTest(zunit_contract=fragment):
                self.assertIn(fragment, zunit_skill)

        template = (
            PUBLIC_ROOT
            / ".github/skills/new-zsh-plugin/templates/plugin.plugin.zsh"
        ).read_text(encoding="utf-8")
        self.assertNotIn("TODO", template)
        self.assertNotIn("#funtions-directory", template)
        self.assertNotIn('\n0="', template)
        self.assertEqual(template.count("builtin emulate -L zsh"), 2)
        for fragment in (
            "${PMSPEC-}",
            "__FPATH_VAR___ADDED",
            "__FPATH_VAR___PLUGINS_KEY_EXISTED",
            "__FPATH_VAR___PLUGINS_KEY_VALUE",
            "fpath[(Ie)${__FPATH_VAR__}]",
            "unfunction __NAME___plugin_unload",
            "zsh/security/trust-paths",
            "zsh/plugin/restore-state",
        ):
            with self.subTest(template_contract=fragment):
                self.assertIn(fragment, template)

        readme = (PUBLIC_ROOT / ".github/README.md").read_text(encoding="utf-8")
        self.assertIn("scripts/validate-zsh-standard-policy.py", readme)
        self.assertNotIn(
            "Zsh standard enforcement is deferred to a later phase",
            readme,
        )

    def test_consumers_define_plugins_restoration_as_preload_state(self) -> None:
        consumers = (
            ".github/agents/zsh-plugin-standard-reviewer.agent.md",
            ".github/skills/new-zsh-plugin/SKILL.md",
            ".github/skills/zunit-test/SKILL.md",
        )
        for relative_path in consumers:
            with self.subTest(relative_path=relative_path):
                text = (PUBLIC_ROOT / relative_path).read_text(encoding="utf-8")
                self.assertIn(
                    "pre-load state",
                    " ".join(text.split()),
                    relative_path,
                )

    def test_patterns_retire_unsafe_zsh_lifecycle_snippets(self) -> None:
        text = (PUBLIC_ROOT / "PATTERNS.md").read_text(encoding="utf-8")
        validator = load_validator()
        self.assertEqual(validator._retired_patterns_contract_errors(text), [])
        section_names = (
            "Plugin entry-point skeleton",
            "Register the repository directory in `Plugins`",
            "Guard `fpath` additions",
        )
        blocks: list[str] = []
        for section_name in section_names:
            start = text.index(f"## {section_name}")
            end = text.find("\n## ", start + 3)
            if end == -1:
                end = len(text)
            block = text[start:end]
            blocks.append(block)
            with self.subTest(section=section_name):
                self.assertIn("Observed in:", block)
                self.assertIn("Status: retired", block)
                self.assertNotIn("```zsh", block)

        retired_lifecycle = "\n".join(blocks)
        for fragment in (
            ".github/instructions/zsh-scripting.instructions.md",
            ".github/skills/new-zsh-plugin/templates/plugin.plugin.zsh",
            "not publish a replacement",
            "zsh/sourced/preserve-caller-state",
            "zsh/plugin/restore-state",
            "zsh/security/trust-paths",
        ):
            with self.subTest(retirement_contract=fragment):
                self.assertIn(fragment, retired_lifecycle)

        self.assertNotIn('\n0="${ZERO:', retired_lifecycle)
        self.assertNotIn("Plugins[PLUGIN_KEY]=", retired_lifecycle)
        self.assertNotIn('} "${0:h}/functions"', retired_lifecycle)

    def test_lifecycle_harness_is_option_sensitive_bounded_and_zero_neutral(
        self,
    ) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        start = source.index(
            "    def test_rendered_plugin_template_restores_lifecycle_state"
        )
        end = source.index(
            "\n    def test_consumer_contract_uses_safe_text_reads",
            start,
        )
        block = source[start:end]
        requirements = (
            ('environment.pop("ZERO", None)', 1),
            ("timeout=10", 2),
            ('"loader-handled-first-source"', 1),
            ("PMSPEC=f", 1),
            ("[[ ! -o UNSET ]]", 2),
            ("[[ ! -o FUNCTION_ARGZERO ]]", 2),
        )
        for fragment, minimum_count in requirements:
            with self.subTest(fragment=fragment):
                self.assertGreaterEqual(
                    block.count(fragment),
                    minimum_count,
                    block,
                )

    def test_zunit_example_guards_and_demonstrates_unload_lifecycle(
        self,
    ) -> None:
        text = (
            PUBLIC_ROOT / ".github/skills/zunit-test/SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "if (( ${+functions[my-plugin_plugin_unload]} )); then",
            text,
        )
        self.assertIn(
            "@test 'unload restores state and self-destructs'",
            text,
        )
        self.assertIn(
            'assert "${(j:|:)fpath}" same_as "${(j:|:)saved_fpath}"',
            text,
        )
        self.assertIn('assert "${+Plugins[MY_PLUGIN]}" equals 0', text)
        self.assertIn(
            'assert "${+functions[my-plugin_plugin_unload]}" equals 0',
            text,
        )
        self.assertIn(
            "one `@setup` and one `@teardown`, each running around every test",
            text,
        )


class PublicRepositoryTests(unittest.TestCase):
    def test_public_repository_zsh_standard_contract(self) -> None:
        self.assertTrue(
            SCRIPT_PATH.is_file(),
            "create scripts/validate-zsh-standard-policy.py",
        )
        self.assertEqual(load_validator().validate(PUBLIC_ROOT), [])


if __name__ == "__main__":
    unittest.main()
