from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

sys.dont_write_bytecode = True
SCRIPT_PATH = Path(__file__).with_name("validate-zsh-standard-policy.py")
PUBLIC_ROOT = SCRIPT_PATH.resolve().parent.parent
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

    def assert_error_contains(self, errors: list[str], *needles: str) -> None:
        self.assertTrue(
            any(all(needle in message for needle in needles) for message in errors),
            f"expected one error containing {needles!r}; got {errors!r}",
        )

    def test_valid_fixture_has_no_errors(self) -> None:
        root = self.make_fixture()

        self.assertEqual(load_validator().validate(root), [])

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

        cases = (
            ("wrong-type", wrong_type, "$.source_classification.tracked_files_only"),
            ("duplicate-suffix", duplicate_suffix, "$.source_classification.suffixes"),
            ("shell-suffix", shell_suffix, ".sh"),
            (
                "missing-compiled-suffix",
                missing_compiled_suffix,
                "$.source_classification.exclusions.compiled_suffixes",
            ),
            ("reordered-glob", reordered_globs, "$.source_classification.path_globs"),
            ("unknown-profile", unknown_profile, "unknown-profile"),
        )
        for name, mutation, expected in cases:
            with self.subTest(name=name):
                root = self.make_fixture()
                policy = self.read_policy(root)
                source = policy["source_classification"]
                self.assertIsInstance(source, dict)
                mutation(source)
                self.write_policy(root, policy)

                errors = load_validator().validate(root)

                self.assert_error_contains(errors, expected)

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
                "`sourced-library`, `autoload-function`",
                "`autoload-function`",
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
        self.assertIn("`zcompile -U`", block)

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

    def test_rejects_unsafe_shell_dispatcher_claims(self) -> None:
        cases = (
            ("default-bash", "\nStart with `#!/bin/bash` by default.\n"),
            ("blanket-strict", "\nAlways enable `set -euo pipefail`.\n"),
            ("shellcheck-zsh", "\nValidate Zsh with ShellCheck.\n"),
        )
        for name, addition in cases:
            with self.subTest(name=name):
                root = self.make_fixture()
                path = root / ".github/instructions/shell.instructions.md"
                path.write_text(
                    path.read_text(encoding="utf-8") + addition,
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    ".github/instructions/shell.instructions.md",
                )

    def test_rejects_paraphrased_shell_dispatcher_prescriptions(self) -> None:
        cases = (
            ("default-bash", "\nDefault new scripts to a Bash shebang.\n"),
            (
                "blanket-strict",
                "\nEnable `set -euo pipefail` in every shell script.\n",
            ),
            (
                "shellcheck-zsh",
                "\nRun ShellCheck against Zsh sources before committing.\n",
            ),
            (
                "negated-clause-then-bash",
                "\nDo not lint POSIX sh; default new scripts to a Bash shebang.\n",
            ),
            (
                "negated-clause-then-strict",
                "\nDo not use strict mode for POSIX sh; enable "
                "`set -euo pipefail` in every Zsh script.\n",
            ),
            (
                "negated-clause-then-shellcheck",
                "\nDo not validate Bash with ShellCheck; run ShellCheck "
                "against Zsh sources.\n",
            ),
        )
        for name, addition in cases:
            with self.subTest(name=name):
                root = self.make_fixture()
                path = root / ".github/instructions/shell.instructions.md"
                path.write_text(
                    path.read_text(encoding="utf-8") + addition,
                    encoding="utf-8",
                )

                errors = load_validator().validate(root)

                self.assert_error_contains(
                    errors,
                    ".github/instructions/shell.instructions.md",
                    "prohibited cross-dialect prescription",
                )

    def test_accepts_explicitly_negated_shell_dispatcher_claims(self) -> None:
        additions = (
            "\nDo not use `#!/bin/bash` as a default.\n",
            "\nNever prescribe `set -euo pipefail` universally.\n",
            "\nDo not validate Zsh with ShellCheck.\n",
        )
        for addition in additions:
            with self.subTest(addition=addition):
                root = self.make_fixture()
                path = root / ".github/instructions/shell.instructions.md"
                path.write_text(
                    path.read_text(encoding="utf-8") + addition,
                    encoding="utf-8",
                )

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


class PublicRepositoryTests(unittest.TestCase):
    def test_public_repository_zsh_standard_contract(self) -> None:
        self.assertTrue(
            SCRIPT_PATH.is_file(),
            "create scripts/validate-zsh-standard-policy.py",
        )
        self.assertEqual(load_validator().validate(PUBLIC_ROOT), [])


if __name__ == "__main__":
    unittest.main()
