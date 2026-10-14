"""Temporary, dependency-free safety gate for the unmergeable Ubuntu canary."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
REUSABLE = {
    "codeql",
    "commit-lint",
    "dependency-review",
    "labeler-config-audit-test",
    "labels-sync-test",
    "lychee",
    "org-routing",
    "release-prepare",
    "repo-settings-audit-test",
    "trunk",
    "zsh-ci",
    "zsh-lint",
    "zsh-policy-consumers",
}


def read(name):
    return (WORKFLOWS / f"{name}.yml").read_text(encoding="utf-8")


def named_step(text, name):
    # Deliberately narrow: these canary workflows have six-space step lists.
    steps = re.split(r"(?m)^      - name: ", text)[1:]
    matches = [step for step in steps if name in step.splitlines()[0]]
    if len(matches) != 1:
        raise AssertionError(f"expected one step named {name!r}")
    return matches[0]


def assert_disabled(test, text, name):
    step = named_step(text, name)
    test.assertRegex(step, r"(?m)^        if: \$\{\{ false \}\}$")
    test.assertEqual(len(re.findall(r"(?m)^        if:", step)), 1)


class CanarySafetyTests(unittest.TestCase):
    def test_release_has_no_publication_or_inference(self):
        text = read("release-prepare")
        assert_disabled(self, text, "Draft changelog with GitHub Models")
        assert_disabled(self, text, "Open or update release proposal issue")
        self.assertNotRegex(text, r"(?m)^\s+(?:issues|models):")
        self.assertIn('test -n "$VERSION"', text)
        self.assertIn('test -s "$RUNNER_TEMP/release-prepare/fallback.md"', text)

    def test_lychee_has_no_issue_or_cache_writes(self):
        text = read("lychee")
        assert_disabled(self, text, "Save cache")
        assert_disabled(self, text, "Create Issue From File")
        self.assertNotRegex(text, r"(?m)^\s+issues:")
        self.assertIn("key: cache-lychee-${{ github.sha }}", text)
        self.assertIn("key: ${{ steps.restore-cache.outputs.cache-primary-key }}", text)

    def test_codeql_analysis_does_not_upload(self):
        text = read("codeql")
        self.assertIn("        upload: never", text)
        self.assertNotRegex(text, r"(?m)^\s+security-events: write")

    def test_all_reusable_linux_jobs_use_the_trial_image(self):
        inventory = {
            path.stem
            for path in WORKFLOWS.glob("*.yml")
            if re.search(r"(?m)^  workflow_call:", path.read_text())
        }
        self.assertEqual(inventory, REUSABLE)
        for name in sorted(REUSABLE - {"trunk"}):
            with self.subTest(workflow=name):
                runners = re.findall(r"(?m)^\s+runs-on: (.+)$", read(name))
                self.assertTrue(runners)
                for runner in runners:
                    if name == "zsh-ci":
                        self.assertEqual(runner, "${{ inputs.canary-runner }}")
                        self.assertIn("default: ubuntu-26.04", read(name))
                    else:
                        self.assertIn("ubuntu-26.04", runner)
                    self.assertNotIn("ubuntu-latest", runner)

    def test_concurrency_groups_do_not_cancel_sibling_calls(self):
        groups = []
        for name in sorted(REUSABLE):
            groups.extend(re.findall(r"(?m)^  group: (.+)$", read(name)))
        self.assertEqual(len(groups), len(set(groups)))

    def test_policy_consumer_uses_the_supported_pinned_fixture(self):
        text = read("zsh-policy-consumers")
        step = named_step(text, "Check out repository")
        self.assertIn("repository: z-shell/agent-skills", step)
        self.assertIn("ref: e18fb0396f2c2a1de9a83e95256530b3d04f020e", step)
        self.assertIn("CALLER: z-shell/agent-skills", text)

    def test_harness_is_complete_and_gates_every_call(self):
        text = read("ubuntu26-canary")
        self.assertNotIn("workflow_dispatch", text)
        self.assertNotIn("secrets: inherit", text)
        self.assertNotIn("concurrency:", text)
        self.assertIn("github.head_ref == 'feature-712-ubuntu26-canary'", text)
        self.assertIn(
            "python3 -m unittest automation/ci/test_ubuntu26_canary.py -v", text
        )
        jobs = re.split(r"(?m)^  [a-z0-9-]+:\n", text.split("jobs:\n", 1)[1])[1:]
        names = []
        for job in jobs:
            match = re.search(r"uses: \./\.github/workflows/([a-z-]+)\.yml", job)
            if match:
                names.append(match.group(1))
                self.assertRegex(job, r"needs: (?:safety|\[safety, zsh-[a-z0-9-]+\])")
                self.assertNotIn("write", job)
        self.assertEqual(set(names), REUSABLE)
        self.assertEqual(names.count("trunk"), 2)
        self.assertEqual(names.count("zsh-ci"), 4)
        for version in ["latest", "5.9", "5.9.2"]:
            self.assertIn(f'zsh-version: "{version}"', text)
        self.assertEqual(text.count("require-sources: true"), 4)
        self.assertEqual(text.count("run-zcompile: true"), 4)
        self.assertIn("runs-on: ubuntu-26.04", text)
        self.assertIn("check-mode: all", text)
        self.assertIn("aff60185cddb4b829f39f2db82aae9fc7bce3e7d", text)

    def test_native_trials_continue_after_a_failed_predecessor(self):
        text = read("ubuntu26-canary")
        for job in ["zsh-59", "zsh-592", "zsh-control-59"]:
            with self.subTest(job=job):
                block = re.split(
                    r"(?m)^  [a-z0-9-]+:", text.split(f"  {job}:\n", 1)[1]
                )[0]
                self.assertIn(
                    "if: ${{ !cancelled() && needs.safety.result == 'success' }}", block
                )
        control = text.split("  zsh-control-59:\n", 1)[1].split(
            "\n  zsh-lint:", 1
        )[0]
        self.assertIn("canary-runner: ubuntu-24.04", control)
        self.assertIn('zsh-version: "5.9"', control)

    def test_trunk_control_uses_same_full_scan_on_previous_image(self):
        text = read("ubuntu26-canary")
        control = text.split("  trunk-control:\n", 1)[1].split("\n  zsh-latest:", 1)[0]
        self.assertIn("runs-on: ubuntu-24.04", control)
        self.assertIn("check-mode: all", control)


if __name__ == "__main__":
    unittest.main()
