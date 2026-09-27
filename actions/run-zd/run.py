#!/usr/bin/env python3
"""Thin Actions adapter for the canonical zd executor, Python 3.10+."""

import json
import os
import re
import subprocess  # nosec B404 - argv-only execution of reviewed tools.
import sys
import tempfile
import urllib.request
from pathlib import Path


def configuration(env):
    revision = env.get("ZD_REF", "")
    image = env.get("ZD_IMAGE", "")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("zd-ref must be a full lowercase commit SHA")
    if not re.fullmatch(
        r"(?:[A-Za-z0-9][A-Za-z0-9._:/-]*@)?sha256:[0-9a-f]{64}", image
    ):
        raise ValueError("image must be an immutable registry digest or local image ID")
    profile = env.get("ZD_PROFILE", "")
    mode = env.get("ZD_MODE", "test")
    pull = env.get("ZD_PULL", "true")
    if profile not in ("runtime", "module-build") or mode not in ("test", "benchmark"):
        raise ValueError("unknown execution profile or mode")
    if pull not in ("true", "false") or (pull == "true" and "@sha256:" not in image):
        raise ValueError("pull must be true/false; pulling requires a registry digest")
    command = json.loads(env.get("ZD_COMMAND", "[]"))
    if (
        not isinstance(command, list)
        or not command
        or any(not isinstance(v, str) or not v or "\0" in v for v in command)
    ):
        raise ValueError("command must be a nonempty JSON array of nonempty arguments")
    fixtures = json.loads(env.get("ZD_FIXTURES", "{}"))
    if not isinstance(fixtures, dict) or any(
        not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", k)
        or not isinstance(v, str)
        or not v
        or "\0" in v
        for k, v in fixtures.items()
    ):
        raise ValueError("fixtures must map safe names to prepared Git paths")
    source = Path(env.get("ZD_SOURCE", "")).resolve(strict=True)
    if not env.get("ZD_SOURCE") or not source.is_dir():
        raise ValueError("source must name a Git checkout directory")
    cpuset = env.get("ZD_CPUSET", "")
    if cpuset and not re.fullmatch(
        r"[0-9]+(?:-[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?)*", cpuset
    ):
        raise ValueError("invalid CPU affinity list")
    timeout = env.get("ZD_TIMEOUT", "900")
    if not re.fullmatch(r"[0-9]+", timeout) or not 1 <= int(timeout) <= 3600:
        raise ValueError("timeout must be between 1 and 3600 seconds")
    return {
        "revision": revision,
        "image": image,
        "profile": profile,
        "mode": mode,
        "pull": pull == "true",
        "source": str(source),
        "fixtures": fixtures,
        "command": command,
        "cpuset": cpuset,
        "timeout": timeout,
    }


def execute(config, runner, output):
    command = [
        sys.executable,
        str(runner),
        "run",
        "--image",
        config["image"],
        "--profile",
        config["profile"],
        "--source",
        config["source"],
        "--output",
        str(output),
        "--mode",
        config["mode"],
        "--timeout",
        config["timeout"],
    ]
    if config["cpuset"]:
        command += ["--cpuset", config["cpuset"]]
    for name, path in sorted(config["fixtures"].items()):
        command += ["--input", name + "=" + path]
    return subprocess.run(
        command + ["--", *config["command"]]
    ).returncode  # nosec B603 - pinned runner; repository-owned argv, no shell.


def main():
    if sys.platform != "linux":
        raise ValueError("run-zd requires a Linux runner with Docker and Python 3.10+")
    directory = Path(
        tempfile.mkdtemp(prefix="zd-action-", dir=os.environ["RUNNER_TEMP"])
    )
    output = directory / "execution"
    output.mkdir()
    with open(os.environ["GITHUB_OUTPUT"], "a") as handle:
        handle.write("directory=" + str(directory) + "\n")
    try:
        config = configuration(os.environ)
        runner = directory / "zd.py"
        url = (
            "https://raw.githubusercontent.com/z-shell/zd/"
            + config["revision"]
            + "/scripts/zd.py"
        )
        with urllib.request.urlopen(
            url, timeout=30
        ) as response:  # nosec B310 - fixed HTTPS host and validated full SHA.
            runner.write_bytes(response.read())
        if config["pull"]:
            pull_argv = ["docker", "pull", config["image"]]
            subprocess.run(
                pull_argv, check=True, timeout=300
            )  # nosec B603 - validated digest; argv only.
        status = execute(config, runner, output)
        (directory / "action.json").write_text(
            json.dumps(
                {
                    "zd_revision": config["revision"],
                    "profile": config["profile"],
                    "mode": config["mode"],
                    "image": config["image"],
                    "exit_code": status,
                },
                indent=2,
            )
            + "\n"
        )
        return status
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        (directory / "preparation-failure.json").write_text(
            json.dumps({"status": "unavailable", "reason": str(error)}) + "\n"
        )
        print("run-zd preparation failed:", error, file=sys.stderr)
        return 125


if __name__ == "__main__":
    sys.exit(main())
