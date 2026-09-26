#!/usr/bin/env python3
"""Tests for scripts/org-routing.py (decisions/0031)."""

import contextlib
import copy
import importlib.util
import io
import json

# Tests invoke only fixed git commands against a temporary repository.
import subprocess  # nosec B404
import tempfile
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).with_name("org-routing.py")
PUBLIC_ROOT = SCRIPT_PATH.parents[1]
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
        self.write()

    def write(self) -> None:
        manifest = self.root / ".github/instruction-surfaces.json"
        manifest.write_text(
            json.dumps(self.manifest, indent=2) + "\n", encoding="utf-8"
        )
        approved = self.root / "lib/approved-skills.json"
        approved.parent.mkdir(parents=True, exist_ok=True)
        approved.write_text(
            json.dumps(self.approved, indent=2) + "\n", encoding="utf-8"
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
        self.org = OrgFixture(Path(self.directory.name)).load()
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

    def test_adapter_symlink_to_agents_is_not_a_surface(self) -> None:
        (self.root / ".github/copilot-instructions.md").symlink_to("../AGENTS.md")
        self.assertEqual(self.check(), [])

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


class RepositoryInventoryTests(unittest.TestCase):
    """The committed inventory is valid and its approved revisions are real."""

    def test_committed_inventory_is_valid(self) -> None:
        org = routing.load_org(PUBLIC_ROOT)
        self.assertTrue(org.downstream)

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
        self.assertEqual(routing.verify_approved(PUBLIC_ROOT, org.approved), [])


if __name__ == "__main__":
    unittest.main()
