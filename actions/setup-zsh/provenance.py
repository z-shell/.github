#!/usr/bin/env python3
"""Record only explicit build inputs, never the caller's environment."""

import hashlib
import json
import os
import platform
import subprocess  # nosec B404 - fixed local compiler query.
import sys
from pathlib import Path


def main():
    (
        install,
        version,
        profile,
        url,
        digest,
        patch_commit,
        patch_digest,
        cpp,
        ld,
        cflags,
        dllflags,
    ) = sys.argv[1:]
    root = Path(__file__).resolve().parent
    source_hashes = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in ("action.yml", "install.sh", "provenance.py")
    }
    compiler = subprocess.check_output(  # nosec B603 B607 - runner toolchain.
        ["cc", "--version"], text=True
    ).splitlines()[0]
    result = {
        "schema": "z-shell/setup-zsh/v1",
        "version": version,
        "profile": profile,
        "archive": {"url": url, "sha256": digest},
        "patch": {"commit": patch_commit, "sha256": patch_digest},
        "action": {
            "repository": os.environ.get("SETUP_ZSH_ACTION_REPOSITORY", ""),
            "ref": os.environ.get("SETUP_ZSH_ACTION_REF", ""),
            "files_sha256": source_hashes,
        },
        "os": os.environ["RUNNER_OS"],
        "architecture": platform.machine(),
        "compiler": compiler,
        "build": {
            "cc": "cc",
            "cflags": cflags,
            "cppflags": cpp,
            "ldflags": ld,
            "dlldflags": dllflags,
        },
        "configure": ["--enable-multibyte", "--with-tcsetpgrp"],
        "executable_sha256": hashlib.sha256(
            (Path(install) / "bin/zsh").read_bytes()
        ).hexdigest(),
    }
    (Path(install) / "provenance.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
