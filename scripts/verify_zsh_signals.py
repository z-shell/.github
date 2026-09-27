#!/usr/bin/env python3
"""Native Zsh test fixtures, isolated standalone profile, floor 5.8.1."""

import os
import subprocess  # nosec B404 - explicitly selected test runtime.
import tempfile


def main():
    executable = os.environ["ZSH_EXECUTABLE"]
    with tempfile.TemporaryDirectory() as home:
        env = {"PATH": os.environ["PATH"], "HOME": home, "ZDOTDIR": home}
        for signal in ("999", "9999", "SIG999"):
            result = subprocess.run(  # nosec B603 - selected runtime and fixed script.
                [executable, "-f", "-c", 'trap "" "$1"', "zsh", signal],
                env=env,
                capture_output=True,
                timeout=10,
                check=False,
            )
            if result.returncode != 1:
                raise SystemExit(f"invalid signal {signal}: status {result.returncode}")
        result = subprocess.run(  # nosec B603 - selected runtime and fixed script.
            [executable, "-f", "-c", "trap 999"],
            env=env,
            capture_output=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 1:
            raise SystemExit("trap without signal was not rejected")
        script = """
            emulate -R zsh
            for sig in 0 1 2 15 TERM EXIT; do
              trap '' "$sig" && trap - "$sig" || exit 1
            done
            if [[ $1 == Linux ]]; then
              for sig in RTMIN RTMAX; do
                trap '' "$sig" && trap - "$sig" || exit 1
              done
            fi
        """
        subprocess.run(  # nosec B603 - fixed signal contract.
            [executable, "-f", "-c", script, "zsh", os.environ.get("RUNNER_OS", "")],
            env=env,
            check=True,
            timeout=10,
        )
    print("Signal bounds and valid trap contract passed")


if __name__ == "__main__":
    main()
