#!/usr/bin/env python3
"""Check immutable inputs and preserve argv/failure boundaries in the adapter."""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location(
    "run_zd", Path(__file__).parents[1] / "actions/run-zd/run.py"
)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class AdapterTests(unittest.TestCase):
    def environment(self):
        return {
            "ZD_REF": "a" * 40,
            "ZD_IMAGE": "registry.example/zd@sha256:" + "b" * 64,
            "ZD_PROFILE": "runtime",
            "ZD_MODE": "benchmark",
            "ZD_SOURCE": str(Path.cwd()),
            "ZD_COMMAND": json.dumps(
                ["python3", "-c", "print('literal $(touch forbidden)')"]
            ),
        }

    def test_rejects_mutable_refs_and_images(self):
        for name, value in [
            ("ZD_REF", "main"),
            ("ZD_IMAGE", "registry.example/zd:latest"),
        ]:
            env = self.environment()
            env[name] = value
            with self.assertRaises(ValueError):
                adapter.configuration(env)

    def test_local_image_requires_no_pull(self):
        env = self.environment()
        env["ZD_IMAGE"] = "sha256:" + "b" * 64
        with self.assertRaises(ValueError):
            adapter.configuration(env)
        env["ZD_PULL"] = "false"
        self.assertFalse(adapter.configuration(env)["pull"])

    def test_arguments_and_functional_status_preserved(self):
        env = self.environment()
        env["ZD_FIXTURES"] = json.dumps({"zi": "/fixture path"})
        config = adapter.configuration(env)
        with mock.patch.object(
            adapter.subprocess, "run", return_value=mock.Mock(returncode=23)
        ) as run:
            self.assertEqual(
                adapter.execute(config, Path("runner.py"), Path("output")), 23
            )
        argv = run.call_args.args[0]
        self.assertEqual(argv[-3:], json.loads(env["ZD_COMMAND"]))
        self.assertIn("zi=/fixture path", argv)
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_invalid_json_and_timeout_fail_before_execution(self):
        for name, value in [
            ("ZD_COMMAND", '"zsh -f test.zsh"'),
            ("ZD_COMMAND", "[]"),
            ("ZD_FIXTURES", '{"../escape":"fixture"}'),
            ("ZD_FIXTURES", '{"unsupported_name":"fixture"}'),
            ("ZD_TIMEOUT", "0"),
            ("ZD_TIMEOUT", "3601"),
            ("ZD_CPUSET", "1; touch forbidden"),
        ]:
            env = self.environment()
            env[name] = value
            with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                adapter.configuration(env)

    def test_preparation_failure_retains_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "outputs"
            output.touch()
            env = self.environment() | {
                "RUNNER_TEMP": directory,
                "GITHUB_OUTPUT": str(output),
                "ZD_REF": "main",
            }
            with mock.patch.dict(os.environ, env):
                self.assertEqual(adapter.main(), 125)
            evidence = Path(output.read_text().strip().split("=", 1)[1])
            self.assertEqual(
                json.loads((evidence / "preparation-failure.json").read_text())[
                    "status"
                ],
                "unavailable",
            )


if __name__ == "__main__":
    unittest.main()
