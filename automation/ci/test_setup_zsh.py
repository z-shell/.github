#!/usr/bin/env python3
"""Exercise the setup action entry point with isolated installer commands."""

from __future__ import annotations

import json
import os
import re
import subprocess  # nosec B404 - regression tests execute the local action.
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTION = ROOT / "actions/setup-zsh"

FAKE_TOOL = r"""#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

name = Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ["COMMAND_LOG"], "a") as log:
    log.write(json.dumps([name, *args]) + "\n")
if name == os.environ.get("FAIL_TOOL"):
    sys.exit(7)
if name == "curl":
    if os.environ.get("MOVED_RELEASE") and "/old/" not in args[-1]:
        sys.exit(22)
    Path(args[args.index("--output") + 1]).write_bytes(b"release fixture")
elif name in ("sha256sum", "shasum"):
    if os.environ.get("BAD_CHECKSUM"):
        sys.exit(1)
    value = sys.stdin.read()
    if os.environ.get("BAD_PATCH") and ".patch" in value:
        sys.exit(1)
    assert "zsh.tar.xz" in value or ".patch" in value
elif name == "tar":
    source = Path(args[args.index("-C") + 1]) / ("zsh-" + os.environ["ZSH_VERSION"])
    source.mkdir()
    configure = source / "configure"
    configure.write_text("#!/bin/sh\nprintf '%s' \"${1#--prefix=}\" > prefix\n")
    configure.chmod(0o700)
elif name == "make" and "install.bin" in args:
    prefix = Path(Path("prefix").read_text())
    (prefix / "bin").mkdir()
    shell = prefix / "bin/zsh"
    shell.write_text("#!/bin/sh\nprintf '%s' \"$MOCK_ACTUAL_VERSION\"\n")
    shell.chmod(0o700)
elif name == "brew" and "--prefix" in args:
    print("/fixture/ncurses")
elif name == "zsh":
    print("zsh package fixture")
"""


class SetupZshTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        (self.bin / "bash").symlink_to("/bin/bash")
        self.runner_temp = self.root / "runner"
        self.runner_temp.mkdir()
        self.log = self.root / "commands.jsonl"
        self.path_file = self.root / "github-path"
        for name in (
            "sudo",
            "brew",
            "choco",
            "curl",
            "sha256sum",
            "shasum",
            "patch",
            "gpatch",
            "tar",
            "make",
            "zsh",
        ):
            tool = self.bin / name
            tool.write_text(FAKE_TOOL)
            tool.chmod(0o700)
        self.env = {
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "RUNNER_OS": "Linux",
            "RUNNER_TEMP": str(self.runner_temp),
            "GITHUB_PATH": str(self.path_file),
            "SETUP_ZSH_ACTION_PATH": str(ACTION),
            "COMMAND_LOG": str(self.log),
            "MOCK_ACTUAL_VERSION": "5.9.2",
        }

    def run_action(self, version="5.9.2", **env):
        # Execute the real action's run field, not a parallel test-only entry.
        metadata = (ACTION / "action.yml").read_text()
        command = re.search(r"^      run: (.+)$", metadata, re.MULTILINE)
        if command is None:
            self.fail("Action must declare its installer entry point")
        self.assertIn("ZSH_VERSION: ${{ inputs.version }}", metadata)
        return subprocess.run(  # nosec B603 - trusted repository action run field.
            ["/bin/bash", "-c", command.group(1)],
            env={**self.env, "ZSH_VERSION": version, **env},
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def commands(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def assert_not_exposed(self):
        self.assertFalse(self.path_file.exists())
        self.assertEqual([], list(self.runner_temp.iterdir()))

    def test_defaults_keep_platform_package_installers(self):
        for platform, installer in (
            ("Linux", "sudo"),
            ("macOS", "brew"),
            ("Windows", "choco"),
        ):
            with self.subTest(platform=platform):
                result = self.run_action("latest", RUNNER_OS=platform)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(installer, self.commands()[-2][0])
                self.assertEqual("zsh", self.commands()[-1][0])
                self.assert_not_exposed()

    def test_empty_version_keeps_package_default(self):
        result = self.run_action("")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(["sudo", "sudo", "zsh"], [c[0] for c in self.commands()])

    def test_exact_versions_install_without_replacing_system_shell(self):
        for version in ("5.8.1", "5.9", "5.9.2"):
            with self.subTest(version=version):
                result = self.run_action(version, MOCK_ACTUAL_VERSION=version)
                self.assertEqual(0, result.returncode, result.stderr)
                selected_bin = Path(self.path_file.read_text().splitlines()[-1])
                self.assertTrue(selected_bin.is_relative_to(self.runner_temp))
                self.assertTrue((selected_bin / "zsh").is_file())
                self.assertFalse(list(self.runner_temp.glob("setup-zsh-build.*")))
                commands = self.commands()
                names = [c[0] for c in commands]
                self.assertLess(names.index("sha256sum"), names.index("tar"))
                self.assertIn(
                    ["make", "install.bin", "install.modules", "install.fns"], commands
                )
                self.assertFalse(any(c[0] == "sudo" and "make" in c for c in commands))
        self.assertEqual(3, len(self.path_file.read_text().splitlines()))

    def test_unsupported_versions_and_injection_fail_before_commands(self):
        for version in ("5.8", "main", "../5.9", "5.9\n5.9.2", "$(touch injected)"):
            with self.subTest(version=version):
                result = self.run_action(version)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("Unsupported Zsh version", result.stderr)
                self.assertEqual([], self.commands())
                self.assertFalse((self.root / "injected").exists())
                self.assert_not_exposed()

    def test_exact_versions_on_other_platforms_fail_before_commands(self):
        for platform in ("Windows",):
            with self.subTest(platform=platform):
                result = self.run_action(RUNNER_OS=platform)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("only on Linux", result.stderr)
                self.assertEqual([], self.commands())
                self.assert_not_exposed()

    def test_patch_profile_and_provenance(self):
        output = self.root / "outputs"
        result = self.run_action(
            ZSH_PATCH_SET="trap-bounds-a3547fd4", GITHUB_OUTPUT=str(output)
        )
        self.assertEqual(0, result.returncode, result.stderr)
        values = dict(line.split("=", 1) for line in output.read_text().splitlines())
        self.assertEqual("5.9.2+trap-bounds-a3547fd4", values["profile"])
        provenance = json.loads(Path(values["provenance"]).read_text())
        self.assertEqual(
            "a3547fd4c165bd6c0c9c9d2643bd61b593f7bbaf", provenance["patch"]["commit"]
        )
        commands = self.commands()
        self.assertIn(["make", "TESTNUM=A05", "check"], commands)
        self.assertIn(["make", "TESTNUM=B11", "check"], commands)
        self.assertEqual(2, sum(c[0] == "patch" for c in commands))

    def test_invalid_patch_combinations_fail_before_commands(self):
        for version, patch in (
            ("latest", "trap-bounds-a3547fd4"),
            ("5.8.1", "trap-bounds-a3547fd4"),
            ("5.9.2", "unknown"),
        ):
            with self.subTest(version=version, patch=patch):
                self.assertNotEqual(
                    0, self.run_action(version, ZSH_PATCH_SET=patch).returncode
                )
                self.assertEqual([], self.commands())
                self.assert_not_exposed()

    def test_patch_integrity_and_application_failures_clean_install(self):
        for env in ({"BAD_PATCH": "1"}, {"FAIL_TOOL": "patch"}):
            with self.subTest(env=env):
                result = self.run_action(ZSH_PATCH_SET="trap-bounds-a3547fd4", **env)
                self.assertNotEqual(0, result.returncode)
                self.assert_not_exposed()

    def test_macos_exact_build_uses_native_dependencies(self):
        result = self.run_action(
            RUNNER_OS="macOS", ZSH_PATCH_SET="trap-bounds-a3547fd4"
        )
        self.assertEqual(0, result.returncode, result.stderr)
        commands = self.commands()
        self.assertIn(["brew", "install", "ncurses", "xz", "gpatch"], commands)
        self.assertNotIn("sudo", [c[0] for c in commands])
        self.assertIn("gpatch", [c[0] for c in commands])

    def test_old_macos_profile_records_legacy_dialect_and_linker(self):
        output = self.root / "outputs"
        result = self.run_action(
            "5.8.1",
            MOCK_ACTUAL_VERSION="5.8.1",
            RUNNER_OS="macOS",
            GITHUB_OUTPUT=str(output),
        )
        self.assertEqual(0, result.returncode, result.stderr)
        values = dict(line.split("=", 1) for line in output.read_text().splitlines())
        manifest = json.loads(Path(values["provenance"]).read_text())
        self.assertEqual("-O2 -std=gnu89", manifest["build"]["cflags"])
        self.assertEqual(
            "-bundle -flat_namespace -undefined dynamic_lookup",
            manifest["build"]["dlldflags"],
        )

    def test_old_linux_profiles_record_legacy_dialect_only(self):
        # GCC 14+ rejects the old boolcodes configure probe outside C89 mode.
        for version, cflags in (
            ("5.8.1", "-O2 -std=gnu89"),
            ("5.9", "-O2 -std=gnu89"),
            ("5.9.2", "-O2"),
        ):
            with self.subTest(version=version):
                output = self.root / f"outputs-{version}"
                result = self.run_action(
                    version, MOCK_ACTUAL_VERSION=version, GITHUB_OUTPUT=str(output)
                )
                self.assertEqual(0, result.returncode, result.stderr)
                values = dict(
                    line.split("=", 1) for line in output.read_text().splitlines()
                )
                manifest = json.loads(Path(values["provenance"]).read_text())
                self.assertEqual(cflags, manifest["build"]["cflags"])
                self.assertEqual("", manifest["build"]["dlldflags"])

    def test_output_write_failure_cleans_install(self):
        result = self.run_action(GITHUB_OUTPUT=str(self.root))
        self.assertNotEqual(0, result.returncode)
        self.assert_not_exposed()

    def test_unknown_platform_fails_before_commands(self):
        result = self.run_action("latest", RUNNER_OS="Other")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual([], self.commands())

    def test_bad_checksum_never_extracts_or_builds(self):
        result = self.run_action(BAD_CHECKSUM="1")
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn("tar", [c[0] for c in self.commands()])
        self.assert_not_exposed()

    def test_release_relocation_keeps_the_exact_version_and_digest(self):
        result = self.run_action(MOVED_RELEASE="1")
        self.assertEqual(0, result.returncode, result.stderr)
        downloads = [c[-1] for c in self.commands() if c[0] == "curl"]
        self.assertEqual(
            [
                "https://www.zsh.org/pub/zsh-5.9.2.tar.xz",
                "https://www.zsh.org/pub/old/zsh-5.9.2.tar.xz",
            ],
            downloads,
        )
        self.assertEqual(1, sum(c[0] == "sha256sum" for c in self.commands()))

    def test_download_failure_never_extracts(self):
        result = self.run_action(FAIL_TOOL="curl")
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn("sha256sum", [c[0] for c in self.commands()])
        self.assert_not_exposed()

    def test_build_failure_never_exposes_an_install(self):
        result = self.run_action(FAIL_TOOL="make")
        self.assertNotEqual(0, result.returncode)
        self.assert_not_exposed()

    def test_version_mismatch_never_exposes_an_install(self):
        result = self.run_action(MOCK_ACTUAL_VERSION="5.9")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("does not match", result.stderr)
        self.assert_not_exposed()

    def test_package_failure_is_not_hidden_by_version_print(self):
        result = self.run_action("latest", FAIL_TOOL="sudo")
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn("zsh", [c[0] for c in self.commands()])

    def test_path_write_failure_cleans_install(self):
        result = self.run_action(GITHUB_PATH=str(self.root))
        self.assertNotEqual(0, result.returncode)
        self.assert_not_exposed()


if __name__ == "__main__":
    unittest.main()
