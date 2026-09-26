"""Behavioral tests for the shared lint runner, without downloading an analyzer."""

import importlib.util
import json
import os
import subprocess  # nosec B404 - fixed analyzer/test executable with argv, no shell.
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("zsh_lint_ci.py")
SPEC = importlib.util.spec_from_file_location("lint_ci", SCRIPT)
CI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CI)


class LintIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "target"
        self.root.mkdir()
        (self.root / "functions").mkdir()
        (self.root / "functions/with space").write_text("print ok\n")
        (self.root / "functions/.hidden").write_text("print ok\n")
        self.analyzer = self.base / "analyzer"
        self.analyzer.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "Path(os.environ['ARGUMENT_LOG']).write_text(json.dumps(sys.argv[1:]))\n"
            "print(os.environ['REPORT'])\n"
            "sys.stderr.write(os.environ.get('ERROR_TEXT', ''))\n"
            "sys.exit(int(os.environ.get('EXIT_CODE', '0')))\n"
        )
        self.analyzer.chmod(0o700)

    def report(self, diagnostics=None):
        diagnostics = diagnostics or []
        return dict(
            version=1,
            diagnostics=diagnostics,
            summary=dict(
                files=2,
                diagnostics=len(diagnostics),
                errors=sum(d["severity"] == "error" for d in diagnostics),
                warnings=sum(d["severity"] == "warning" for d in diagnostics),
                infos=0,
                hints=0,
            ),
        )

    def invoke(
        self,
        report=None,
        paths="functions",
        code=0,
        mode="strict",
        stderr="",
        config="",
    ):
        output = self.base / "output"
        result = subprocess.run(  # nosec B603 - local test fixture and runner.
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(self.root),
                "--analyzer",
                str(self.analyzer),
                "--output",
                str(output),
                "--mode",
                mode,
                "--config",
                config,
            ],
            env={
                **os.environ,
                "ZSH_LINT_PATHS": paths,
                "REPORT": json.dumps(report if report is not None else self.report()),
                "EXIT_CODE": str(code),
                "ERROR_TEXT": stderr,
                "ARGUMENT_LOG": str(self.base / "args.json"),
                "GITHUB_STEP_SUMMARY": str(self.base / "summary.md"),
            },
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertTrue((output / "result.json").exists())
        return result

    def test_inventory_preserves_hidden_extensionless_spaces_and_deduplicates(self):
        result = self.invoke(paths="functions\nfunctions/with space\n\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            json.loads((self.base / "args.json").read_text()),
            ["--format=json", "./functions/.hidden", "./functions/with space"],
        )
        self.assertEqual(
            json.loads((self.base / "output/inventory.json").read_text()),
            ["functions/.hidden", "functions/with space"],
        )

    def test_bad_roots_fail_before_execution(self):
        for paths in ("", ".", "..", "/outside", "missing", "functions/../functions"):
            with self.subTest(paths=paths):
                result = self.invoke(paths=paths)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.base / "args.json").exists())

    def test_symlinks_are_rejected(self):
        (self.root / "functions/escape").symlink_to(self.base)
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertFalse((self.base / "args.json").exists())

    def test_empty_directory_is_not_success(self):
        (self.root / "empty").mkdir()
        self.assertNotEqual(self.invoke(paths="empty").returncode, 0)

    def test_explicit_config_is_passed_as_an_argument(self):
        (self.root / "config with space.json").write_text("{}")
        result = self.invoke(config="config with space.json")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn(
            "./config with space.json",
            json.loads((self.base / "args.json").read_text()),
        )

    def diagnostic(self, rule="rule/example", severity="warning"):
        return dict(
            rule=rule,
            severity=severity,
            file="./functions/with space",
            message="value%\n::error::injected",
        )

    def test_observation_tolerates_only_semantic_findings(self):
        report = self.report([self.diagnostic()])
        self.assertEqual(self.invoke(report, code=1).returncode, 1)
        result = self.invoke(report, code=1, mode="observe")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("value%25%0A::error::injected", result.stdout)
        self.assertEqual(len(result.stdout.splitlines()), 1)
        parser = self.report([self.diagnostic(rule="parse/error", severity="error")])
        self.assertEqual(self.invoke(parser, code=1, mode="observe").returncode, 1)

    def test_tool_failure_and_stderr_fail_even_in_observation(self):
        for code, stderr in ((2, ""), (1, ""), (0, "configuration failed")):
            with self.subTest(code=code, stderr=stderr):
                self.assertEqual(
                    self.invoke(code=code, stderr=stderr, mode="observe").returncode, 1
                )
                self.assertTrue((self.base / "output/diagnostics.json").exists())

    def test_invalid_envelopes_fail(self):
        bad = [
            [],
            {"version": 2},
            self.report(),
            self.report([self.diagnostic()]),
            self.report(),
        ]
        bad[2]["summary"]["files"] = 0
        bad[3]["diagnostics"][0]["file"] = "../outside"
        bad[4]["summary"]["errors"] = False
        for report in bad:
            with self.subTest(report=report):
                self.assertEqual(self.invoke(report).returncode, 1)

    def test_timeout_preserves_failure_evidence(self):
        self.analyzer.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(3)\n")
        args = type(
            "Args",
            (),
            dict(
                root=self.root,
                analyzer=self.analyzer,
                output=self.base / "timed",
                mode="observe",
                config="",
                timeout=0.01,
            ),
        )()
        from unittest.mock import patch

        with patch.dict(os.environ, {"ZSH_LINT_PATHS": "functions"}), patch(
            "sys.stdout"
        ):

            self.assertEqual(CI.run(args), 1)
        self.assertEqual(
            json.loads((args.output / "result.json").read_text())["status"], "failed"
        )
        self.assertTrue((args.output / "stderr.txt").exists())

    def test_configuration_cannot_escape_checkout(self):
        (self.root / "config.json").symlink_to(self.base / "outside.json")
        self.assertEqual(self.invoke(config="config.json").returncode, 1)
        self.assertFalse((self.base / "args.json").exists())

    def test_workflow_preflight_rejects_invalid_refs_modes_and_identity(self):
        workflow = SCRIPT.parents[1] / ".github/workflows/zsh-lint.yml"
        preflight = (
            workflow.read_text()
            .split("        run: |\n", 1)[1]
            .split("\n      - name:", 1)[0]
        )
        for ref, mode, identity, expected in (
            (
                "a" * 40,
                "strict",
                {"workflow_repository": "z-shell/.github", "workflow_sha": "b" * 40},
                0,
            ),
            (
                "main",
                "strict",
                {"workflow_repository": "z-shell/.github", "workflow_sha": "b" * 40},
                1,
            ),
            (
                "a" * 40,
                "ignore",
                {"workflow_repository": "z-shell/.github", "workflow_sha": "b" * 40},
                1,
            ),
            ("a" * 40, "strict", {}, 1),
        ):
            with self.subTest(ref=ref, mode=mode, identity=identity):
                result = subprocess.run(  # nosec B603 - trusted workflow preflight.
                    ["/bin/bash", "-c", textwrap.dedent(preflight)],
                    env={
                        **os.environ,
                        "ANALYZER_REF": ref,
                        "LINT_MODE": mode,
                        "JOB_CONTEXT": json.dumps(identity),
                        "GITHUB_OUTPUT": str(self.base / "job-output"),
                    },
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, expected, result.stderr)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):
            json.loads('{"version":1,"version":2}', object_pairs_hook=CI.unique_object)

    def test_property_escaping(self):
        self.assertEqual(CI.escape("a,b:c%\n", property_value=True), "a%2Cb%3Ac%25%0A")


if __name__ == "__main__":
    unittest.main()
