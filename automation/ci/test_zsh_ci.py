"""Execute the native workflow's shell block against isolated source trees."""

import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/zsh-ci.yml"


class NativeWorkflowTests(unittest.TestCase):
    def run_check(
        self,
        files,
        extra="",
        required="true",
        compile="true",
        links=None,
        fail_compile=False,
    ):
        source = WORKFLOW.read_text().split("      - name: Run zsh -n\n", 1)[1]
        script = textwrap.dedent(source.split("        run: |\n", 1)[1])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, content in files.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
            for name, target in (links or {}).items():
                (root / name).symlink_to(root / target)
            env = dict(
                os.environ,
                EXTRA_FILES=extra,
                REQUIRE_SOURCES=required,
                RUN_ZCOMPILE=compile,
            )
            if fail_compile:
                binary = root / "bin"
                binary.mkdir()
                stub = binary / "zsh"
                stub.write_text(
                    '#!/bin/sh\n[ "$1" != -fc ] || exit 42\n'
                    f'exec "{shutil.which("zsh")}" "$@"\n'
                )
                stub.chmod(0o700)
                env["PATH"] = str(binary) + os.pathsep + env["PATH"]
            result = subprocess.run(
                ["bash", "-c", script],
                cwd=root,
                text=True,
                capture_output=True,
                env=env,
            )
            self.assertFalse(list(root.rglob("*.zwc")))
            return result

    def test_extensionless_and_space_paths(self):
        result = self.run_check(
            {"lib/_zi": "print ok\n", "with space.zsh": "print ok\n"}, "lib/_zi"
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_extensionless_source_fails(self):
        result = self.run_check({"lib/_zi": "if then\n"}, "lib/_zi")
        self.assertNotEqual(result.returncode, 0)

    def test_empty_inventory_contract(self):
        self.assertNotEqual(self.run_check({}).returncode, 0)
        self.assertEqual(self.run_check({}, required="false").returncode, 0)

    def test_invalid_extra_paths_fail(self):
        for path in ("../outside", "/etc/passwd", "missing", "*.zsh"):
            with self.subTest(path=path):
                self.assertNotEqual(
                    self.run_check({"ok.zsh": "true\n"}, path).returncode, 0
                )

    def test_symlink_sources_fail(self):
        files = {"lib/_zi": "true\n"}
        for extra, links in (
            ("link", {"link": "lib/_zi"}),
            ("link/_zi", {"link": "lib"}),
        ):
            with self.subTest(extra=extra):
                self.assertNotEqual(
                    self.run_check(files, extra, links=links).returncode, 0
                )

    def test_compiler_failure_propagates_only_when_enabled(self):
        for enabled, expected in (("true", False), ("false", True)):
            result = self.run_check(
                {"ok.zsh": "true\n"}, compile=enabled, fail_compile=True
            )
            self.assertEqual(result.returncode == 0, expected)

    def test_syntax_failure_cannot_be_hidden_by_later_success(self):
        result = self.run_check({"bad.zsh": "if then\n", "good.zsh": "true\n"})
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
