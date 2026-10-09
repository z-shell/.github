#!/usr/bin/env python3
"""Tests for automation/agents/org-routing.py (decisions/0031)."""

import contextlib
import copy
import importlib.util
import io
import hashlib
import json
import os
import shutil

# Tests invoke only fixed git commands against a temporary repository.
import subprocess  # nosec B404
import tempfile
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).with_name("org-routing.py")
PUBLIC_ROOT = SCRIPT_PATH.parents[2]
SPEC = importlib.util.spec_from_file_location("org_routing", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load generator from {SCRIPT_PATH}")
routing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(routing)

SKILL_BODY = "\n# Code review\n\nInspect the diff and report findings.\n"
CANONICAL_SKILL = (
    "---\ndescription: Review changes.\nname: code-review\n---\n" + SKILL_BODY
)


def installed_skill(pinned: str, *, indent: str = "  ", body: str = SKILL_BODY) -> str:
    """Render a skill as ``gh skill install --pin`` writes it downstream."""
    metadata = "".join(
        f"{indent}{key}: {value}\n"
        for key, value in (
            ("github-path", ".github/skills/code-review"),
            ("github-pinned", pinned),
            ("github-ref", pinned),
            ("github-repo", "https://github.com/z-shell/.github"),
            ("github-tree-sha", "0" * 40),
        )
    )
    return (
        "---\ndescription: Review changes.\nmetadata:\n"
        + metadata
        + "name: code-review\n---\n\n"
        + body.lstrip("\n")
    )


def git(root: Path, *arguments: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed git arguments
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class OrgFixture:
    """A throwaway canonical repository with one approved skill."""

    def __init__(self, directory: Path) -> None:
        self.root = directory / "org"
        skill = self.root / ".github/skills/code-review/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(CANONICAL_SKILL, encoding="utf-8")
        git(self.root, "init", "-q")
        git(
            self.root,
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.invalid",
            "add",
            ".",
        )
        git(
            self.root,
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.invalid",
            "commit",
            "-q",
            "--no-verify",
            "-m",
            "skill",
        )
        self.revision = git(self.root, "rev-parse", "HEAD")
        self.manifest = {
            "version": 1,
            "repository": "z-shell/.github",
            "canonical_policy": "AGENTS.md",
            "surfaces": [
                {
                    "id": "skill-code-review",
                    "path": ".github/skills/code-review/SKILL.md",
                    "kind": "skill",
                    "tasks": ["code-review", "review-readiness"],
                    "file_patterns": ["**"],
                }
            ],
            "downstream": [
                {"repository": "z-shell/plain"},
                {
                    "repository": "z-shell/tool",
                    "surfaces": [
                        {
                            "path": ".github/instructions/go.instructions.md",
                            "tasks": ["implementation"],
                            "file_patterns": ["internal/**"],
                        }
                    ],
                    "vendored_skills": ["code-review"],
                },
            ],
        }
        self.approved = {
            "version": 1,
            "source": "z-shell/.github",
            "skills": {
                "code-review": {
                    "path": ".github/skills/code-review",
                    "revision": self.revision,
                    "digest": routing.skill_digest(CANONICAL_SKILL),
                    "files": ["SKILL.md"],
                }
            },
        }
        # Project profiles are optional: older organization revisions have none.
        self.profiles: dict | None = None
        self.write()

    def write(self) -> None:
        manifest = self.root / ".github/instruction-surfaces.json"
        manifest.write_text(
            json.dumps(self.manifest, indent=2) + "\n", encoding="utf-8"
        )
        approved = self.root / "knowledge/domains/agents/data/approved-skills.json"
        approved.parent.mkdir(parents=True, exist_ok=True)
        approved.write_text(
            json.dumps(self.approved, indent=2) + "\n", encoding="utf-8"
        )
        profiles = self.root / routing.PROFILES_PATH
        if self.profiles is None:
            profiles.unlink(missing_ok=True)
        else:
            profiles.parent.mkdir(parents=True, exist_ok=True)
            profiles.write_text(
                json.dumps(self.profiles, indent=2) + "\n", encoding="utf-8"
            )

    def load(self):
        return routing.load_org(self.root)


def make_downstream(directory: Path, revision: str) -> Path:
    root = directory / "tool"
    (root / ".github/instructions").mkdir(parents=True)
    (root / ".github/instructions/go.instructions.md").write_text(
        "# Go\n", encoding="utf-8"
    )
    skill = root / ".github/skills/code-review/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(installed_skill(revision), encoding="utf-8")
    (root / "AGENTS.md").write_text(
        "# Project guidelines\n\nLocal rules.\n", encoding="utf-8"
    )
    return root


def run_main(*arguments: str) -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        status = routing.main(list(arguments))
    return status, output.getvalue()


class ProjectDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.fixture = OrgFixture(self.directory)
        self.source = "knowledge/domains/tooling/rules.md"
        path = self.fixture.root / self.source
        path.parent.mkdir(parents=True)
        path.write_text('---\napplyTo: "internal/**"\n---\n\n# Project rules\n\n[procedure](../../../runbooks/triage.md)\n')
        git(self.fixture.root, "add", self.source)
        git(self.fixture.root, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "approved source")
        self.record = {
            "repository": "z-shell/tool", "source": self.source,
            "target": ".github/instructions/go.instructions.md",
            "revision": git(self.fixture.root, "rev-parse", "HEAD"),
            "source_blob": git(self.fixture.root, "rev-parse", "HEAD:" + self.source),
            "content_sha256": "0" * 64,
            "project_revision": "c" * 40, "project_source_blob": "d" * 40,
        }
        rendered = routing.delivery.render_project(path.read_text(), self.record)
        self.record["content_sha256"] = hashlib.sha256(rendered.encode()).hexdigest()
        self.write_records([self.record])
        self.checkout = make_downstream(self.directory, self.fixture.revision)

    def write_records(self, records):
        (self.fixture.root / routing.delivery.PROJECT_MANIFEST).write_text(json.dumps({"version": 1, "consumers": records}))

    def apply(self):
        return run_main("--org-root", str(self.fixture.root), "apply", "--repository", "z-shell/tool", "--root", str(self.checkout))

    def test_apply_and_check_use_approved_blob_even_with_dirty_authoring_source(self):
        (self.fixture.root / self.source).write_text("Unapproved dirty instruction")
        original = (self.checkout / "AGENTS.md").read_text()
        self.assertEqual(self.apply()[0], 0)
        self.assertIn("Local rules.", (self.checkout / "AGENTS.md").read_text())
        self.assertNotEqual(original, (self.checkout / "AGENTS.md").read_text())
        target = self.checkout / self.record['target']
        self.assertIn("# Project rules", target.read_text())
        self.assertNotIn("Unapproved dirty", target.read_text())
        self.assertEqual(routing.check(self.checkout, 'z-shell/tool', self.fixture.load()), [])
        target.write_text(target.read_text() + '\nUnauthorized rule\n')
        self.assertTrue(routing.check(self.checkout, 'z-shell/tool', self.fixture.load()))

    def test_wrong_source_blob_or_digest_cannot_modify_project(self):
        original = (self.checkout / "AGENTS.md").read_bytes()
        consumer = (self.checkout / self.record['target']).read_bytes()
        for field, value in [('revision', 'f' * 40), ('source_blob', 'e' * 40), ('content_sha256', 'f' * 64)]:
            with self.subTest(field=field):
                self.write_records([{**self.record, field: value}])
                self.assertEqual(self.apply()[0], 1)
                self.assertEqual((self.checkout / "AGENTS.md").read_bytes(), original)
                self.assertEqual((self.checkout / self.record['target']).read_bytes(), consumer)

    def test_invalid_later_consumer_preserves_every_project_file(self):
        second = {**self.record, 'source': 'knowledge/domains/tooling/missing.md', 'target': '.github/instructions/second.instructions.md'}
        self.fixture.manifest['downstream'][1]['surfaces'].append({'path': second['target'], 'tasks': ['implementation'], 'file_patterns': ['internal/**']})
        self.fixture.write()
        self.write_records([self.record, second])
        original = (self.checkout / 'AGENTS.md').read_bytes()
        consumer = (self.checkout / self.record['target']).read_bytes()
        self.assertEqual(self.apply()[0], 1)
        self.assertEqual((self.checkout / 'AGENTS.md').read_bytes(), original)
        self.assertEqual((self.checkout / self.record['target']).read_bytes(), consumer)
        self.assertFalse((self.checkout / second['target']).exists())

    def test_verify_approved_checks_project_records(self):
        self.assertEqual(run_main('--org-root', str(self.fixture.root), 'verify-approved')[0], 0)
        self.write_records([{**self.record, 'source_blob': 'f' * 40}])
        self.assertEqual(run_main('--org-root', str(self.fixture.root), 'verify-approved')[0], 1)

    def test_selector_mismatch_fails_before_writes(self):
        self.fixture.manifest['downstream'][1]['surfaces'][0]['file_patterns'] = ['other/**']
        self.fixture.write()
        original = (self.checkout / 'AGENTS.md').read_bytes()
        consumer = (self.checkout / self.record['target']).read_bytes()
        self.assertEqual(self.apply()[0], 1)
        self.assertEqual((self.checkout / 'AGENTS.md').read_bytes(), original)
        self.assertEqual((self.checkout / self.record['target']).read_bytes(), consumer)
        self.assertEqual(run_main('--org-root', str(self.fixture.root), 'verify-approved')[0], 1)

    def test_broken_agents_symlink_cannot_write_outside_project(self):
        agents = self.checkout / 'AGENTS.md'
        agents.unlink()
        outside = self.directory / 'outside.md'
        agents.symlink_to(outside)
        self.assertEqual(self.apply()[0], 1)
        self.assertFalse(outside.exists())

    def test_caller_sparse_inputs_run_without_source_history(self):
        self.assertEqual(self.apply()[0], 0)
        sparse = self.directory / 'sparse'
        workflow = (PUBLIC_ROOT / '.github/workflows/org-routing.yml').read_text()
        block = workflow.split('sparse-checkout: |\n', 1)[1].split('sparse-checkout-cone-mode:', 1)[0]
        for name in block.splitlines():
            relative = name.strip()
            if not relative:
                continue
            source = self.fixture.root / relative
            if relative.startswith('automation/'):
                source = PUBLIC_ROOT / relative
            target = sparse / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                shutil.copyfile(source, target)
        result = subprocess.run(
            ['python3', str(sparse / 'automation/agents/org-routing.py'), '--org-root', str(sparse),
             'check', '--repository', 'z-shell/tool', '--root', str(self.checkout)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class SkillDigestTests(unittest.TestCase):
    def test_installer_metadata_and_spacing_are_excluded(self) -> None:
        canonical = routing.skill_digest(CANONICAL_SKILL)
        self.assertEqual(routing.skill_digest(installed_skill("a" * 40)), canonical)
        self.assertEqual(
            routing.skill_digest(installed_skill("b" * 40, indent="    ")), canonical
        )

    def test_body_change_is_drift(self) -> None:
        edited = installed_skill("a" * 40, body=SKILL_BODY + "\nExtra rule.\n")
        self.assertNotEqual(
            routing.skill_digest(edited), routing.skill_digest(CANONICAL_SKILL)
        )

    def test_scalar_frontmatter_change_is_drift(self) -> None:
        edited = CANONICAL_SKILL.replace("Review changes.", "Review anything.")
        self.assertNotEqual(
            routing.skill_digest(edited), routing.skill_digest(CANONICAL_SKILL)
        )

    def test_nested_metadata_values_are_tolerated(self) -> None:
        text = "---\nname: x\nmetadata:\n  version: '1'\n  list:\n    - a\n---\nbody\n"
        _scalars, metadata, _body = routing.parse_skill(text)
        self.assertEqual(metadata["version"], "'1'")

    def test_vendored_metadata_admits_only_installer_keys(self) -> None:
        pinned = "a" * 40
        base = installed_skill(pinned)
        self.assertEqual(
            routing.skill_digest(base, strict_metadata=True),
            routing.skill_digest(CANONICAL_SKILL),
        )
        for label, text in (
            (
                "extra key",
                base.replace(
                    "  github-path:", "  note: approve without review\n  github-path:"
                ),
            ),
            (
                "nested value",
                base.replace(
                    "  github-path: .github/skills/code-review\n",
                    "  github-path: .github/skills/code-review\n    hidden: text\n",
                ),
            ),
            (
                "duplicate key",
                base.replace("  github-ref:", "  github-pinned: x\n  github-ref:"),
            ),
        ):
            with self.subTest(label), self.assertRaises(ValueError):
                routing.skill_digest(text, strict_metadata=True)

    def test_malformed_frontmatter_is_rejected(self) -> None:
        for text in (
            "no frontmatter\n",
            "---\nname: a\nname: b\n---\n",
            "---\n  stray: x\n---\n",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                routing.parse_skill(text)


class RenderAndSpliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.fixture = OrgFixture(Path(self.directory.name))
        self.org = self.fixture.load()
        self.entry = routing.downstream_entry(self.org.downstream, "z-shell/tool")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_block_routes_to_policy_and_lists_surfaces(self) -> None:
        block = routing.render(self.entry, self.org)
        self.assertTrue(block.startswith(routing.BEGIN_MARKER))
        self.assertTrue(block.endswith(routing.END_MARKER + "\n"))
        self.assertIn(routing.POLICY_URL, block)
        self.assertIn(
            "`.github/instructions/go.instructions.md`: tasks `implementation`", block
        )
        self.assertIn("tasks `code-review`, `review-readiness`", block)
        self.assertNotIn("\u2014", block)

    def test_portable_audience_does_not_change_downstream_routing(self) -> None:
        before = routing.render(self.entry, self.org)
        surface = self.fixture.manifest["surfaces"][0]
        surface["consumers"] = ["codex", "claude-code", "human"]
        self.fixture.write()
        explicit = routing.render(self.entry, self.fixture.load())
        surface["consumers"] = ["agent", "human"]
        self.fixture.write()
        portable = routing.render(self.entry, self.fixture.load())
        self.assertEqual(before, explicit)
        self.assertEqual(explicit, portable)

    def test_splice_preserves_repository_content(self) -> None:
        block = routing.render(self.entry, self.org)
        text = "# Title\n\nLocal rules.\n"
        spliced = routing.splice(text, block, "z-shell/tool")
        self.assertTrue(spliced.startswith("# Title\n\n" + block))
        self.assertTrue(spliced.endswith("\nLocal rules.\n"))
        self.assertEqual(routing.splice(spliced, block, "z-shell/tool"), spliced)

    def test_splice_replaces_only_the_generated_region(self) -> None:
        block = routing.render(self.entry, self.org)
        stale = (
            "# T\n\n"
            + routing.BEGIN_MARKER
            + "\nold\n"
            + routing.END_MARKER
            + "\n\nKeep.\n"
        )
        self.assertEqual(
            routing.splice(stale, block, "z-shell/tool"),
            "# T\n\n" + block + "\nKeep.\n",
        )

    def test_misplaced_block_is_moved_to_the_top(self) -> None:
        block = routing.render(self.entry, self.org)
        placed = "# T\n\n" + block + "\nKeep.\n"
        for moved in (
            "# T\n\nKeep.\n\n" + block,
            "# T\n\n```text\n" + block + "```\n\nKeep.\n",
        ):
            with self.subTest(moved=moved[:30]):
                result = routing.splice(moved, block, "z-shell/tool")
                self.assertTrue(result.startswith("# T\n\n" + block))
                self.assertNotEqual(result, moved)
        self.assertEqual(routing.splice(placed, block, "z-shell/tool"), placed)

    def test_missing_agents_gets_minimal_body(self) -> None:
        created = routing.splice(
            None, routing.render(self.entry, self.org), "z-shell/tool"
        )
        self.assertTrue(
            created.startswith("# Agent instructions: tool\n\n" + routing.BEGIN_MARKER)
        )
        self.assertIn("## Repository guidance", created)

    def test_unbalanced_markers_are_rejected(self) -> None:
        block = routing.render(self.entry, self.org)
        for text in (
            routing.BEGIN_MARKER + "\n",
            routing.END_MARKER + "\n" + routing.BEGIN_MARKER + "\n",
            (routing.BEGIN_MARKER + "\n" + routing.END_MARKER + "\n") * 2,
        ):
            with self.subTest(text=text), self.assertRaises(routing.RoutingError):
                routing.splice(text, block, "z-shell/tool")


class CheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        base = Path(self.directory.name)
        self.fixture = OrgFixture(base)
        self.root = make_downstream(base, self.fixture.revision)
        status, _ = run_main(
            "--org-root",
            str(self.fixture.root),
            "apply",
            "--repository",
            "z-shell/tool",
            "--root",
            str(self.root),
        )
        self.assertEqual(status, 0)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def check(self) -> list[str]:
        return routing.check(self.root, "z-shell/tool", self.fixture.load())

    def test_applied_checkout_is_current_and_apply_is_idempotent(self) -> None:
        self.assertEqual(self.check(), [])
        status, output = run_main(
            "--org-root",
            str(self.fixture.root),
            "apply",
            "--repository",
            "z-shell/tool",
            "--root",
            str(self.root),
        )
        self.assertEqual((status, output.strip()), (0, "AGENTS.md is current"))

    def test_edited_generated_region_fails(self) -> None:
        agents = self.root / "AGENTS.md"
        agents.write_text(
            agents.read_text().replace("Read it before", "Skim it before")
        )
        self.assertTrue(
            any("differs from the generated block" in item for item in self.check())
        )

    def test_repository_owned_edits_pass(self) -> None:
        agents = self.root / "AGENTS.md"
        agents.write_text(agents.read_text() + "\nMore local rules.\n")
        self.assertEqual(self.check(), [])

    def test_missing_block_and_missing_agents_fail(self) -> None:
        (self.root / "AGENTS.md").write_text("# Project\n")
        self.assertTrue(any("block is missing" in item for item in self.check()))
        (self.root / "AGENTS.md").unlink()
        self.assertTrue(any("AGENTS.md: missing" in item for item in self.check()))

    def test_missing_declared_surface_fails(self) -> None:
        (self.root / ".github/instructions/go.instructions.md").unlink()
        self.assertTrue(
            any("declared surface is missing" in item for item in self.check())
        )

    def test_undeclared_surfaces_fail(self) -> None:
        for relative in (
            ".github/instructions/extra.instructions.md",
            ".github/agents/helper.agent.md",
            ".github/prompts/task.prompt.md",
            ".github/skills/local/SKILL.md",
            ".github/copilot-instructions.md",
        ):
            with self.subTest(relative=relative):
                path = self.root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("---\nname: local\n---\nx\n")
                self.assertTrue(
                    any(item.startswith(relative + ": ") for item in self.check())
                )
                path.unlink()

    def test_unroutable_instruction_files_fail(self) -> None:
        for relative in (
            ".github/skills/My_Skill/SKILL.md",
            ".github/agents/odd name.agent.md",
            "docs/AGENTS.md",
            "CLAUDE.md",
            ".claude/rules/local.md",
            ".cursorrules",
        ):
            with self.subTest(relative=relative):
                path = self.root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x\n")
                self.assertTrue(
                    any(
                        item.startswith(relative + ": ")
                        and "not a routable surface" in item
                        for item in self.check()
                    ),
                    self.check(),
                )
                path.unlink()

    def test_nested_scoped_instructions_must_be_declared(self) -> None:
        path = self.root / ".github/instructions/sub/a.instructions.md"
        path.parent.mkdir(parents=True)
        path.write_text("x\n")
        self.assertTrue(
            any(
                item.startswith(".github/instructions/sub/a.instructions.md: ")
                and "not declared downstream" in item
                for item in self.check()
            )
        )

    def test_git_inventory_excludes_dependencies_but_keeps_project_guidance(
        self,
    ) -> None:
        git(self.root, "init", "-q")
        (self.root / ".gitignore").write_text("node_modules/\nignored/\n")
        dependency = self.root / "node_modules/package/CLAUDE.md"
        dependency.parent.mkdir(parents=True)
        dependency.write_text("Dependency guidance\n")
        self.assertEqual(self.check(), [])
        tracked = self.root / "ignored/AGENTS.md"
        tracked.parent.mkdir()
        tracked.write_text("Tracked project guidance\n")
        git(self.root, "add", "-f", "ignored/AGENTS.md")
        self.assertTrue(any("ignored/AGENTS.md" in e for e in self.check()))
        new = self.root / "docs/CLAUDE.md"
        new.parent.mkdir()
        new.write_text("New project guidance\n")
        self.assertTrue(any("docs/CLAUDE.md" in e for e in self.check()))
        tracked.unlink()
        new.unlink()
        self.assertEqual(self.check(), [])

    def test_ignored_declared_surface_is_still_required(self) -> None:
        git(self.root, "init", "-q")
        (self.root / ".gitignore").write_text(".github/instructions/\n")
        (self.root / ".github/instructions/go.instructions.md").unlink()
        self.assertTrue(any("declared surface is missing" in e for e in self.check()))

    def test_control_characters_in_paths_are_escaped(self) -> None:
        path = self.root / ".github/prompts/a\n::error title=x::y.prompt.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n")
        errors = self.check()
        self.assertTrue(errors)
        self.assertFalse(
            any(line.startswith("::") for e in errors for line in e.splitlines())
        )

    def test_project_without_adapter_passes(self) -> None:
        self.assertFalse((self.root / ".github/copilot-instructions.md").exists())
        self.assertEqual(self.check(), [])

    def test_adapter_file_fails_with_removal_fix(self) -> None:
        path = self.root / ".github/copilot-instructions.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        for text in ("@../AGENTS.md\n", "# Copilot\n\nLocal guidance.\n"):
            with self.subTest(text=text):
                path.write_text(text)
                errors = self.check()
                self.assertTrue(
                    any(
                        item.startswith(".github/copilot-instructions.md: ")
                        and "carry no Copilot adapter" in item
                        and "only instruction entry point" in item
                        for item in errors
                    ),
                    errors,
                )
                self.assertFalse(any("downstream manifest" in e for e in errors))
                path.unlink()

    def test_adapter_symlink_to_agents_fails_with_removal_fix(self) -> None:
        (self.root / ".github/copilot-instructions.md").symlink_to("../AGENTS.md")
        self.assertEqual(
            self.check(),
            [
                ".github/copilot-instructions.md: project repositories carry no "
                "Copilot adapter; fix: remove it; AGENTS.md is the project's only "
                "instruction entry point (runbooks/new-repository.md)"
            ],
        )

    def test_undeclared_organization_skill_fails_with_vendoring_fix(self) -> None:
        other = self.root / ".github/skills/zi-install/SKILL.md"
        other.parent.mkdir(parents=True)
        other.write_text(installed_skill("c" * 40).replace("code-review", "zi-install"))
        self.assertTrue(
            any("add zi-install to vendored_skills" in item for item in self.check())
        )

    def test_stale_pin_fails_even_with_identical_content(self) -> None:
        skill = self.root / ".github/skills/code-review/SKILL.md"
        skill.write_text(installed_skill("d" * 40))
        errors = self.check()
        self.assertTrue(any("is not the approved revision" in item for item in errors))
        self.assertFalse(any("content differs" in item for item in errors))

    def test_drifted_content_fails(self) -> None:
        skill = self.root / ".github/skills/code-review/SKILL.md"
        skill.write_text(
            installed_skill(self.fixture.revision, body=SKILL_BODY + "local edit\n")
        )
        self.assertTrue(any("content differs" in item for item in self.check()))

    def test_extra_skill_file_fails(self) -> None:
        (self.root / ".github/skills/code-review/notes.md").write_text("x\n")
        self.assertTrue(any("differ from approved" in item for item in self.check()))

    def test_symlinks_in_a_vendored_skill_fail(self) -> None:
        skill_dir = self.root / ".github/skills/code-review"
        for name, target in (("extra.md", "../../../AGENTS.md"), ("refs", "../../..")):
            with self.subTest(name=name):
                link = skill_dir / name
                link.symlink_to(target)
                self.assertTrue(
                    any(f"{name}@" in item for item in self.check()), self.check()
                )
                link.unlink()

    def test_inconsistent_installer_ref_fails(self) -> None:
        skill = self.root / ".github/skills/code-review/SKILL.md"
        text = skill.read_text()
        skill.write_text(
            text.replace(f"github-ref: {self.fixture.revision}", "github-ref: main")
        )
        self.assertTrue(any("github-ref differs" in item for item in self.check()))

    def test_missing_vendored_skill_fails(self) -> None:
        (self.root / ".github/skills/code-review/SKILL.md").unlink()
        self.assertTrue(
            any("vendored skill is missing" in item for item in self.check())
        )

    def test_symlinked_agents_is_rejected(self) -> None:
        agents = self.root / "AGENTS.md"
        target = self.root.parent / "outside.md"
        target.write_text(agents.read_text())
        agents.unlink()
        agents.symlink_to(target)
        self.assertTrue(any("not a regular file" in item for item in self.check()))

    def test_cli_exit_status(self) -> None:
        status, output = run_main(
            "--org-root",
            str(self.fixture.root),
            "check",
            "--repository",
            "z-shell/tool",
            "--root",
            str(self.root),
        )
        self.assertEqual(
            (status, output.strip()), (0, "org routing for z-shell/tool is current")
        )
        (self.root / "AGENTS.md").write_text("# P\n")
        status, output = run_main(
            "--org-root",
            str(self.fixture.root),
            "check",
            "--repository",
            "z-shell/tool",
            "--root",
            str(self.root),
        )
        self.assertEqual(status, 1)
        self.assertIn("ERROR: AGENTS.md", output)

    def test_undeclared_repository_is_an_error(self) -> None:
        status, output = run_main(
            "--org-root",
            str(self.fixture.root),
            "render",
            "--repository",
            "z-shell/other",
        )
        self.assertEqual(status, 1)
        self.assertIn("is not declared downstream", output)


class InventoryValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.fixture = OrgFixture(Path(self.directory.name))

    def tearDown(self) -> None:
        self.directory.cleanup()

    def errors(self) -> list[str]:
        self.fixture.write()
        try:
            self.fixture.load()
        except routing.RoutingError as exc:
            return str(exc).splitlines()
        return []

    def test_fixture_is_valid(self) -> None:
        self.assertEqual(self.errors(), [])

    def test_downstream_schema_violations(self) -> None:
        original = copy.deepcopy(self.fixture.manifest)
        cases = {
            "unknown field": lambda d: d[0].update(extra=1),
            "must match z-shell/<name>": lambda d: d[0].update(repository="other/x"),
            "canonical repository is not downstream": lambda d: d.insert(
                0, {"repository": "z-shell/.github"}
            ),
            "out of order": lambda d: d.reverse(),
            "duplicate repository": lambda d: d.append({"repository": "z-shell/tool"}),
            "not a routable instruction surface": lambda d: d[1]["surfaces"].append(
                {
                    "path": "../escape.instructions.md",
                    "tasks": ["x"],
                    "file_patterns": ["**"],
                }
            ),
            "which project repositories do not carry": lambda d: d[1]["surfaces"].insert(
                0,
                {
                    "path": ".github/copilot-instructions.md",
                    "tasks": ["all"],
                    "file_patterns": ["**"],
                },
            ),
            "tasks must be a non-empty unique string list": lambda d: d[1]["surfaces"][
                0
            ].update(tasks=[]),
            "file_patterns must be a non-empty unique string list": lambda d: d[1][
                "surfaces"
            ][0].update(file_patterns=["a`b"]),
            "has no approved revision": lambda d: d[1].update(
                vendored_skills=["code-review", "unknown"]
            ),
            "as a local surface too": lambda d: d[1]["surfaces"].append(
                {
                    "path": ".github/skills/code-review/SKILL.md",
                    "tasks": ["x"],
                    "file_patterns": ["**"],
                }
            ),
            "surfaces must be sorted by path": lambda d: d[1]["surfaces"].insert(
                0,
                {
                    "path": ".github/prompts/z.prompt.md",
                    "tasks": ["x"],
                    "file_patterns": ["**"],
                },
            ),
            "vendored_skills must be sorted": lambda d: d[1].update(
                vendored_skills=["code-review", "a-skill"]
            ),
        }
        for expected, mutate in cases.items():
            with self.subTest(expected=expected):
                self.fixture.manifest = copy.deepcopy(original)
                mutate(self.fixture.manifest["downstream"])
                self.assertTrue(
                    any(expected in item for item in self.errors()), self.errors()
                )

    def test_approved_schema_violations(self) -> None:
        original = copy.deepcopy(self.fixture.approved)
        cases = {
            "revision must be a full commit SHA": lambda a: a["skills"][
                "code-review"
            ].update(revision="main"),
            "digest must be a sha256": lambda a: a["skills"]["code-review"].update(
                digest="x"
            ),
            "path must be": lambda a: a["skills"]["code-review"].update(
                path=".github/skills/other"
            ),
            "files must list SKILL.md": lambda a: a["skills"]["code-review"].update(
                files=["x.md"]
            ),
            "source must be": lambda a: a.update(source="someone/else"),
            "version must be 1": lambda a: a.update(version=True),
        }
        for expected, mutate in cases.items():
            with self.subTest(expected=expected):
                self.fixture.approved = copy.deepcopy(original)
                mutate(self.fixture.approved)
                self.assertTrue(
                    any(expected in item for item in self.errors()), self.errors()
                )

    def test_approved_skill_must_be_an_organization_surface(self) -> None:
        self.fixture.manifest["surfaces"] = []
        self.assertTrue(
            any("not an organization skill surface" in item for item in self.errors())
        )

    def test_verify_approved_detects_wrong_digest_and_files(self) -> None:
        org = self.fixture.load()
        self.assertEqual(routing.verify_approved(self.fixture.root, org.approved), [])
        org.approved["skills"]["code-review"]["digest"] = "0" * 64
        org.approved["skills"]["code-review"]["files"] = ["SKILL.md", "extra.md"]
        errors = routing.verify_approved(self.fixture.root, org.approved)
        self.assertTrue(any("digest does not match" in item for item in errors))
        self.assertTrue(any("files" in item for item in errors))

    def test_verify_approved_rejects_an_unreachable_revision(self) -> None:
        git(self.fixture.root, "checkout", "-q", "-b", "side")
        (self.fixture.root / "side.txt").write_text("x\n")
        git(self.fixture.root, "add", "side.txt")
        git(
            self.fixture.root,
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.invalid",
            "commit",
            "-q",
            "--no-verify",
            "-m",
            "side",
        )
        side = git(self.fixture.root, "rev-parse", "HEAD")
        git(self.fixture.root, "checkout", "-q", "-")
        org = self.fixture.load()
        org.approved["skills"]["code-review"]["revision"] = side
        errors = routing.verify_approved(self.fixture.root, org.approved)
        self.assertTrue(any("not an ancestor of HEAD" in item for item in errors))


RESOURCE_PATH = "references/criteria.md"
RESOURCE_TEXT = "# Criteria\n\nCRITICAL blocks merge.\n"


class MultiFileSkillTests(unittest.TestCase):
    """A bundled resource is pinned by its Git blob id, like SKILL.md by digest."""

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        base = Path(self.directory.name)
        self.fixture = OrgFixture(base)
        resource = self.fixture.root / ".github/skills/code-review" / RESOURCE_PATH
        resource.parent.mkdir(parents=True)
        resource.write_text(RESOURCE_TEXT, encoding="utf-8")
        self.fixture.revision = commit_all(self.fixture.root, "resource")
        self.blob = routing.git_blob_id(RESOURCE_TEXT.encode("utf-8"))
        self.fixture.approved["skills"]["code-review"].update(
            revision=self.fixture.revision,
            files=["SKILL.md", RESOURCE_PATH],
            resources={RESOURCE_PATH: self.blob},
        )
        self.fixture.write()
        self.root = make_downstream(base, self.fixture.revision)
        vendored = self.root / ".github/skills/code-review" / RESOURCE_PATH
        vendored.parent.mkdir(parents=True)
        vendored.write_text(RESOURCE_TEXT, encoding="utf-8")
        status, _ = run_main(
            "--org-root", str(self.fixture.root),
            "apply", "--repository", "z-shell/tool", "--root", str(self.root),
        )
        self.assertEqual(status, 0)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def errors(self) -> list[str]:
        self.fixture.write()
        try:
            self.fixture.load()
        except routing.RoutingError as exc:
            return str(exc).splitlines()
        return []

    def test_blob_id_matches_git(self) -> None:
        listed = git(
            self.fixture.root, "rev-parse",
            f"HEAD:.github/skills/code-review/{RESOURCE_PATH}",
        )
        self.assertEqual(self.blob, listed)

    def test_pinned_resources_verify_and_check(self) -> None:
        org = self.fixture.load()
        self.assertEqual(routing.verify_approved(self.fixture.root, org.approved), [])
        self.assertEqual(routing.check(self.root, "z-shell/tool", org), [])

    def test_edited_resource_fails_check(self) -> None:
        vendored = self.root / ".github/skills/code-review" / RESOURCE_PATH
        vendored.write_text(RESOURCE_TEXT + "Local rule.\n", encoding="utf-8")
        errors = routing.check(self.root, "z-shell/tool", self.fixture.load())
        self.assertTrue(
            any(
                item.startswith(f".github/skills/code-review/{RESOURCE_PATH}: ")
                and "content differs from the approved skill resource" in item
                for item in errors
            ),
            errors,
        )

    def test_wrong_recorded_blob_fails_verify_approved(self) -> None:
        org = self.fixture.load()
        org.approved["skills"]["code-review"]["resources"] = {RESOURCE_PATH: "0" * 40}
        errors = routing.verify_approved(self.fixture.root, org.approved)
        self.assertTrue(any("resources" in item and self.blob in item for item in errors), errors)

    def test_multi_file_record_needs_every_resource_pinned(self) -> None:
        record = self.fixture.approved["skills"]["code-review"]
        for resources in (None, {}, {RESOURCE_PATH: "main"}, {RESOURCE_PATH: self.blob, "x.md": self.blob}):
            with self.subTest(resources=resources):
                if resources is None:
                    record.pop("resources", None)
                else:
                    record["resources"] = resources
                self.assertTrue(
                    any("resources must map each file" in item for item in self.errors()),
                    self.errors(),
                )

    def test_single_file_record_may_not_pin_resources(self) -> None:
        record = self.fixture.approved["skills"]["code-review"]
        record.update(files=["SKILL.md"], resources={RESOURCE_PATH: self.blob})
        self.assertTrue(any("resources must map each file" in item for item in self.errors()))


EXTERNAL_SKILL = "---\ndescription: Install Zi.\nname: zi-install\n---\n\n# Zi install\n\nRun the installer.\n"
EXTERNAL_PATH = "plugins/z-shell/skills/zi-install"


def commit_all(root: Path, message: str) -> str:
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@example.invalid",
        "commit",
        "-q",
        "--no-verify",
        "-m",
        message,
    )
    return git(root, "rev-parse", "HEAD")


def installed_external(
    pinned: str, *, repo: str = "https://github.com/z-shell/agent-skills"
) -> str:
    """Render the external skill as ``gh skill install --pin`` writes it."""
    metadata = "".join(
        f"  {key}: {value}\n"
        for key, value in (
            ("github-path", EXTERNAL_PATH),
            ("github-pinned", pinned),
            ("github-ref", pinned),
            ("github-repo", repo),
            ("github-tree-sha", "0" * 40),
        )
    )
    return (
        "---\ndescription: Install Zi.\nmetadata:\n"
        + metadata
        + "name: zi-install\n---\n\n# Zi install\n\nRun the installer.\n"
    )


class ApprovedSourceTests(unittest.TestCase):
    """Approved skills from a source other than the canonical repository (decisions/0037)."""

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        base = Path(self.directory.name)
        self.fixture = OrgFixture(base)
        self.source = base / "agent-skills"
        skill = self.source / EXTERNAL_PATH / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(EXTERNAL_SKILL, encoding="utf-8")
        git(self.source, "init", "-q")
        self.revision = commit_all(self.source, "skill")
        self.fixture.approved["skills"]["zi-install"] = {
            "source": "z-shell/agent-skills",
            "path": EXTERNAL_PATH,
            "revision": self.revision,
            "digest": routing.skill_digest(EXTERNAL_SKILL),
            "files": ["SKILL.md"],
            "tasks": ["zi-install"],
        }
        self.fixture.manifest["downstream"][1]["vendored_skills"] = [
            "code-review",
            "zi-install",
        ]
        self.fixture.write()

    def errors(self) -> list[str]:
        self.fixture.write()
        try:
            self.fixture.load()
        except routing.RoutingError as exc:
            return str(exc).splitlines()
        return []

    def test_external_skill_needs_no_canonical_copy_or_surface(self) -> None:
        self.assertEqual(self.errors(), [])
        org = self.fixture.load()
        self.assertEqual(org.source_of("zi-install"), "z-shell/agent-skills")
        self.assertEqual(org.source_of("code-review"), "z-shell/.github")
        self.assertEqual(org.tasks_for_skill("zi-install"), ["zi-install"])

    def test_source_schema_violations(self) -> None:
        original = copy.deepcopy(self.fixture.approved)
        cases = {
            "source must be one of": lambda r, c: r.update(source="someone/else"),
            "source must be one of ['z-shell/agent-skills']": lambda r, c: r.update(
                source=["z-shell/agent-skills"]
            ),
            "omit source for z-shell/.github skills": lambda r, c: c.update(
                source="z-shell/.github"
            ),
            "path must be plugins/<plugin>/skills/zi-install": lambda r, c: r.update(
                path=".github/skills/zi-install"
            ),
            "needs tasks": lambda r, c: r.pop("tasks"),
            "takes its tasks from its organization skill surface": lambda r, c: c.update(
                tasks=["code-review"]
            ),
        }
        for expected, mutate in cases.items():
            with self.subTest(expected=expected):
                self.fixture.approved = copy.deepcopy(original)
                skills = self.fixture.approved["skills"]
                mutate(skills["zi-install"], skills["code-review"])
                self.assertTrue(
                    any(expected in item for item in self.errors()), self.errors()
                )

    def test_verify_approved_requires_a_checkout_of_the_source(self) -> None:
        org = self.fixture.load()
        errors = routing.verify_approved(self.fixture.root, org.approved)
        self.assertEqual(len(errors), 1)
        self.assertIn("no checkout of it was given", errors[0])
        self.assertIn("--source-root z-shell/agent-skills=PATH", errors[0])
        roots = {"z-shell/agent-skills": self.source}
        self.assertEqual(
            routing.verify_approved(self.fixture.root, org.approved, roots), []
        )
        org.approved["skills"]["zi-install"]["digest"] = "0" * 64
        errors = routing.verify_approved(self.fixture.root, org.approved, roots)
        self.assertTrue(
            any("zi-install digest does not match" in e for e in errors), errors
        )

    def test_verify_approved_reads_the_source_not_the_organization(self) -> None:
        # The organization checkout lacks the source revision, so reading it there fails.
        org = self.fixture.load()
        roots = {"z-shell/agent-skills": self.fixture.root}
        errors = routing.verify_approved(self.fixture.root, org.approved, roots)
        self.assertTrue(any("cannot read zi-install" in e for e in errors), errors)

    def test_cli_source_root(self) -> None:
        root = str(self.fixture.root)
        self.assertEqual(run_main("--org-root", root, "verify-approved")[0], 1)
        status, output = run_main(
            "--org-root",
            root,
            "verify-approved",
            "--source-root",
            f"z-shell/agent-skills={self.source}",
        )
        self.assertEqual(
            (status, output.strip()),
            (0, "approved skill and project knowledge revisions verified"),
        )
        for value in ("z-shell/.github=x", "someone/else=x", "z-shell/agent-skills"):
            with self.subTest(value=value):
                status, output = run_main(
                    "--org-root", root, "verify-approved", "--source-root", value
                )
                self.assertEqual(status, 1)
                self.assertIn("must be OWNER/REPO=PATH", output)

    def test_downstream_check_uses_the_skill_source(self) -> None:
        base = Path(self.directory.name)
        downstream = make_downstream(base, self.fixture.revision)
        skill = downstream / ".github/skills/zi-install/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(installed_external(self.revision), encoding="utf-8")
        arguments = ("--org-root", str(self.fixture.root))
        target = ("--repository", "z-shell/tool", "--root", str(downstream))
        self.assertEqual(run_main(*arguments, "apply", *target)[0], 0)
        block = (downstream / "AGENTS.md").read_text()
        self.assertIn(
            "- `.github/skills/zi-install/SKILL.md`: tasks `zi-install`; files `**`; "
            f"skill from `z-shell/agent-skills` vendored at approved revision `{self.revision[:12]}`",
            block,
        )
        self.assertIn("organization skill vendored at approved revision", block)
        org = self.fixture.load()
        self.assertEqual(routing.check(downstream, "z-shell/tool", org), [])
        skill.write_text(
            installed_external(
                self.revision, repo="https://github.com/z-shell/.github"
            ),
            encoding="utf-8",
        )
        errors = routing.check(downstream, "z-shell/tool", org)
        self.assertTrue(
            any(
                "does not name the approved source" in e
                and f"gh skill install z-shell/agent-skills {EXTERNAL_PATH} --pin {self.revision}"
                in e
                for e in errors
            ),
            errors,
        )

    def test_undeclared_skill_from_an_approved_source_is_reported(self) -> None:
        base = Path(self.directory.name)
        downstream = make_downstream(base, self.fixture.revision)
        self.fixture.manifest["downstream"][1]["vendored_skills"] = ["code-review"]
        self.fixture.approved["skills"].pop("zi-install")
        self.fixture.write()
        org = self.fixture.load()
        self.assertEqual(
            run_main(
                "--org-root",
                str(self.fixture.root),
                "apply",
                "--repository",
                "z-shell/tool",
                "--root",
                str(downstream),
            )[0],
            0,
        )
        skill = downstream / ".github/skills/zi-install/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(installed_external(self.revision), encoding="utf-8")
        errors = routing.check(downstream, "z-shell/tool", org)
        self.assertTrue(
            any("add zi-install to vendored_skills" in e for e in errors), errors
        )


def tool_profile() -> dict:
    return {
        "component": "Tool",
        "verified": {"revision": "a" * 40, "date": "2026-10-09"},
        "version": {"command": "tool --version", "note": None},
        "branch": "main",
        "zsh": {"minimum": "5.8.1", "tested": ["5.8.1", "5.9.2"], "platforms": ["Linux"]},
        "install": ["zi light z-shell/tool"],
        "verification": ["make test"],
        "report_fields": [
            {"label": "Configuration", "description": "The `tool.json` in effect."}
        ],
    }


class ProjectProfileTests(unittest.TestCase):
    """Project profiles feed the block's issue-reporting section (decisions/0040)."""

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.fixture = OrgFixture(Path(self.directory.name))
        self.fixture.profiles = {"version": 1, "profiles": {"z-shell/tool": tool_profile()}}

    def tearDown(self) -> None:
        self.directory.cleanup()

    def errors(self) -> list[str]:
        self.fixture.write()
        try:
            self.fixture.load()
        except routing.RoutingError as exc:
            return str(exc).splitlines()
        return []

    def block(self, repository: str = "z-shell/tool") -> str:
        self.fixture.write()
        org = self.fixture.load()
        return routing.render(routing.downstream_entry(org.downstream, repository), org)

    def test_profile_renders_reporting_section_inside_the_block(self) -> None:
        block = self.block()
        section = block.index("## Reporting issues")
        self.assertLess(section, block.index(routing.END_MARKER))
        self.assertGreater(section, block.index("`AGENTS.md` (this file)"))
        self.assertIn(routing.TRIAGE_URL, block)
        self.assertIn("give the output of `tool --version`.", block)
        self.assertIn("- `### Configuration`: The `tool.json` in effect.", block)
        self.assertNotIn("\u2014", block)

    def test_only_intake_facts_are_rendered(self) -> None:
        # Branch, versions, install and test commands stay repository-owned text.
        block = self.block()
        for unrendered in ("make test", "zi light z-shell/tool", "5.8.1", "Linux"):
            self.assertNotIn(unrendered, block)

    def test_note_without_command_and_no_extra_fields(self) -> None:
        profile = self.fixture.profiles["profiles"]["z-shell/tool"]
        profile["version"] = {"command": None, "note": "Give the release tag."}
        profile["report_fields"] = []
        block = self.block()
        self.assertIn("in form order. Give the release tag.", block)
        self.assertNotIn("add these headings", block)

    def test_repository_without_profile_and_missing_file_render_unchanged(self) -> None:
        with_profiles = self.block("z-shell/plain")
        self.fixture.profiles = None
        self.assertEqual(with_profiles, self.block("z-shell/plain"))
        self.assertNotIn("## Reporting issues", self.block())

    def test_applied_block_checks_current(self) -> None:
        self.fixture.write()
        org = self.fixture.load()
        root = make_downstream(Path(self.directory.name), self.fixture.revision)
        status, _ = run_main(
            "--org-root", str(self.fixture.root), "apply",
            "--repository", "z-shell/tool", "--root", str(root),
        )
        self.assertEqual(status, 0)
        self.assertIn("## Reporting issues", (root / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertEqual(routing.check(root, "z-shell/tool", org), [])

    def test_profile_schema_violations(self) -> None:
        original = copy.deepcopy(self.fixture.profiles)
        cases = {
            "must hold exactly version 1": lambda p: p.update(version=2),
            "is not declared downstream": lambda p: p["profiles"].update({"z-shell/zz-absent": tool_profile()}),
            "out of order": lambda p: p.update(profiles={"z-shell/tool": tool_profile(), "z-shell/plain": tool_profile()}),
            "unknown field 'extra'": lambda p: p["profiles"]["z-shell/tool"].update(extra=1),
            "missing field 'branch'": lambda p: p["profiles"]["z-shell/tool"].pop("branch"),
            "verified is invalid": lambda p: p["profiles"]["z-shell/tool"]["verified"].update(revision="main"),
            "tool verified is invalid": lambda p: p["profiles"]["z-shell/tool"]["verified"].update(date="2026-13-45"),
            "must hold exactly version 1": lambda p: p.update(version=True),
            "tool profile must be an object": lambda p: p["profiles"].update({"z-shell/tool": []}),
            "tool version note is invalid": lambda p: p["profiles"]["z-shell/tool"]["version"].update(note="opens <!-- here"),
            "tool version note is invalid ": lambda p: p["profiles"]["z-shell/tool"]["version"].update(note="unclosed ` span"),
            "tool report_fields is invalid": lambda p: p["profiles"]["z-shell/tool"]["report_fields"][0].update(label="`code`"),
            "tool component or branch is invalid": lambda p: p["profiles"]["z-shell/tool"].update(component="bell\a"),
            "give a command, a note, or both": lambda p: p["profiles"]["z-shell/tool"].update(version={"command": None, "note": None}),
            "version command is invalid": lambda p: p["profiles"]["z-shell/tool"]["version"].update(command="`x`"),
            "zsh is invalid": lambda p: p["profiles"]["z-shell/tool"]["zsh"].update(tested=["latest"]),
            "verification is invalid": lambda p: p["profiles"]["z-shell/tool"].update(verification=[]),
            "report_fields is invalid": lambda p: p["profiles"]["z-shell/tool"]["report_fields"][0].update(description="ends -->"),
            "keep one 'Configuration' field": lambda p: p["profiles"]["z-shell/tool"]["report_fields"].append(
                {"label": "Configuration", "description": "Again."}
            ),
        }
        for expected, mutate in cases.items():
            with self.subTest(expected):
                self.fixture.profiles = copy.deepcopy(original)
                mutate(self.fixture.profiles)
                errors = self.errors()
                self.assertTrue(any(expected.strip() in message for message in errors), errors)
                if mutate is not cases["out of order"] and "downstream" not in expected:
                    self.assertEqual(len(errors), 1, errors)


class RepositoryInventoryTests(unittest.TestCase):
    """The committed inventory is valid and its approved revisions are real."""

    def test_committed_inventory_is_valid(self) -> None:
        org = routing.load_org(PUBLIC_ROOT)
        self.assertTrue(org.downstream)
        self.assertTrue(org.profiles)
        for repository in org.profiles:
            entry = routing.downstream_entry(org.downstream, repository)
            self.assertIn("## Reporting issues", routing.render(entry, org))

    def test_committed_approved_revisions_verify(self) -> None:
        try:
            toplevel = git(PUBLIC_ROOT, "rev-parse", "--show-toplevel")
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("no git history available")
        if Path(toplevel).resolve() != PUBLIC_ROOT.resolve():
            self.skipTest("not a git checkout of this repository")
        shallow = git(PUBLIC_ROOT, "rev-parse", "--is-shallow-repository")
        if shallow == "true":
            self.skipTest("shallow clone; verify-approved runs in CI with full history")
        org = routing.load_org(PUBLIC_ROOT)
        # CI checks out each external source and names it here; locally an
        # unset variable verifies the canonical records and requires the
        # missing-checkout refusal for every external one.
        agent_skills = os.environ.get("Z_SHELL_AGENT_SKILLS_ROOT")
        source_roots = (
            {"z-shell/agent-skills": Path(agent_skills)} if agent_skills else {}
        )
        external = sorted(
            name
            for name, record in org.approved["skills"].items()
            if routing.skill_source(record) not in source_roots
            and routing.skill_source(record) != routing.CANONICAL_REPOSITORY
        )
        errors = routing.verify_approved(PUBLIC_ROOT, org.approved, source_roots)
        self.assertEqual(
            errors,
            [
                routing.error(
                    routing.APPROVED_PATH,
                    f"skill {name} comes from "
                    f"{routing.skill_source(org.approved['skills'][name])}, "
                    "and no checkout of it was given",
                    f"pass --source-root {routing.skill_source(org.approved['skills'][name])}"
                    "=PATH with full history",
                )
                for name in external
            ],
        )


if __name__ == "__main__":
    unittest.main()
