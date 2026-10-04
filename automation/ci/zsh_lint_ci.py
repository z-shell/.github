#!/usr/bin/env python3
"""Run the pinned analyzer over explicitly reviewed Zsh source roots."""

from __future__ import annotations

import argparse
import collections
import json
import os
import subprocess  # nosec B404 - fixed analyzer/test executable with argv, no shell.
import sys
from pathlib import Path


def contained(root: Path, name: str) -> Path:
    """Reject ambiguous, missing, linked, or external inputs."""
    relative = Path(name)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError(f"expected a repository-relative path: {name!r}")
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink() or part == ".git":
            raise ValueError(f"symlinks and Git metadata are not lint inputs: {name!r}")
    current.resolve(strict=True).relative_to(root)
    return current


def inventory(root: Path, paths: str) -> list[str]:
    files: set[str] = set()
    for name in paths.splitlines():
        if not name.strip():
            continue
        pending = [contained(root, name)]
        while pending:
            candidate = pending.pop()
            relative = candidate.relative_to(root).as_posix()
            checked = contained(root, relative)
            if checked.is_file():
                files.add(relative)
            elif checked.is_dir():
                # iterdir propagates scan failures; glob can silently omit them.
                pending.extend(checked.iterdir())
            else:
                raise ValueError(f"not a regular source file: {relative!r}")
    if not files:
        raise ValueError("source selection is empty")
    return sorted(files)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def validate_report(report: dict, files: list[str], returncode: int) -> None:
    if (
        not isinstance(report, dict)
        or type(report.get("version")) is not int
        or report["version"] != 1
    ):
        raise ValueError("unsupported diagnostic envelope version")
    diagnostics = report.get("diagnostics")
    summary = report.get("summary")
    if not isinstance(diagnostics, list) or not isinstance(summary, dict):
        raise ValueError("missing diagnostic array or summary")
    counts = collections.Counter()
    for diagnostic in diagnostics:
        if not isinstance(diagnostic, dict):
            raise ValueError("invalid diagnostic")
        for key in ("rule", "severity", "message", "file"):
            if not isinstance(diagnostic.get(key), str) or not diagnostic[key]:
                raise ValueError(f"invalid diagnostic {key}")
        severity = diagnostic["severity"]
        if severity not in ("error", "warning", "info", "hint"):
            raise ValueError("unknown diagnostic severity")
        name = diagnostic["file"]
        if name.startswith("./"):
            name = name[2:]
        if name not in files:
            raise ValueError("diagnostic references a file outside the inventory")
        if "range" in diagnostic:
            span = diagnostic["range"]
            if not isinstance(span, dict):
                raise ValueError("invalid diagnostic range")
            for bound in ("start", "end"):
                position = span.get(bound)
                if not isinstance(position, dict):
                    raise ValueError("invalid diagnostic position")
                for key, minimum in (("line", 1), ("column", 1), ("offset", 0)):
                    value = position.get(key)
                    if type(value) is not int or value < minimum:
                        raise ValueError("invalid diagnostic coordinates")
        counts[severity] += 1
    expected = {"files": len(files), "diagnostics": len(diagnostics)}
    expected.update(
        {key + "s": counts[key] for key in ("error", "warning", "info", "hint")}
    )
    if any(
        type(summary.get(key)) is not int or summary[key] != value
        for key, value in expected.items()
    ):
        raise ValueError(
            "diagnostic summary does not match inspected files and findings"
        )
    if returncode != int(bool(counts["error"] or counts["warning"])):
        raise ValueError("analyzer exit status does not match its diagnostics")


def escape(value: str, *, property_value: bool = False) -> str:
    value = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if property_value:
        value = value.replace(":", "%3A").replace(",", "%2C")
    return value


def run(args) -> int:
    root = args.root.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "status": "failed",
        "mode": args.mode,
        "analyzer_revision": os.environ.get("ZSH_LINT_REF", "unknown"),
        "workflow_revision": os.environ.get("ZSH_LINT_WORKFLOW_SHA", "unknown"),
    }
    try:
        files = inventory(root, os.environ.get("ZSH_LINT_PATHS", ""))
        (output / "inventory.json").write_text(json.dumps(files, indent=2) + "\n")
        command = [str(args.analyzer.resolve(strict=True)), "--format=json"]
        if args.config:
            config = contained(root, args.config)
            if not config.is_file():
                raise ValueError("configuration must be a regular file")
            command += ["--config", "./" + config.relative_to(root).as_posix()]
        command += ["./" + name for name in files]
        with (output / "diagnostics.json").open("wb") as stdout, (
            output / "stderr.txt"
        ).open("wb") as stderr:
            process = subprocess.run(
                command,
                cwd=root,
                stdout=stdout,
                stderr=stderr,
                timeout=args.timeout,
                check=False,
            )  # nosec B603 - pinned analyzer, argv only.
        result["analyzer_exit"] = process.returncode
        if process.returncode not in (0, 1):
            raise ValueError(f"analyzer failed with exit status {process.returncode}")
        if (output / "stderr.txt").stat().st_size:
            raise ValueError(
                "analyzer wrote failure diagnostics to stderr; see artifact"
            )
        report = json.loads(
            (output / "diagnostics.json").read_text(), object_pairs_hook=unique_object
        )
        validate_report(report, files, process.returncode)
        parser_errors = 0
        for diagnostic in report["diagnostics"]:
            parser_errors += diagnostic["rule"].startswith("parse/")
            level = {"warning": "warning", "error": "error"}.get(
                diagnostic["severity"], "notice"
            )
            name = diagnostic["file"].removeprefix("./")
            properties = "file=" + escape(name, property_value=True)
            if "range" in diagnostic:
                start = diagnostic["range"]["start"]
                properties += f",line={start['line']},col={start['column']}"
            message = escape(f"[{diagnostic['rule']}] {diagnostic['message']}")
            print(f"::{level} {properties}::{message}")
        failed = bool(parser_errors or (process.returncode and args.mode == "strict"))
        result.update(
            status="failed" if failed else "passed",
            summary=report["summary"],
            parser_errors=parser_errors,
        )
        summary = report["summary"]
        result["message"] = (
            f"Inspected {len(files)} files: {summary['errors']} errors, {summary['warnings']} warnings, {summary['infos']} infos, {summary['hints']} hints. Parser failures: {parser_errors}."
        )
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        result["message"] = str(error)
        print("::error::" + escape(str(error)))
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    # Only JSON-encoded text enters Markdown: use an indented block to prevent
    # paths or tool failures from injecting HTML, links, or fenced code blocks.
    summary_text = (
        f"Zsh lint: {result['status']} ({args.mode})\n\n    "
        + json.dumps(result["message"], ensure_ascii=True)
        + "\n"
    )
    (output / "summary.md").write_text(summary_text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
            stream.write(summary_text)
    return int(result["status"] != "passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--analyzer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", default="")
    parser.add_argument("--mode", choices=("strict", "observe"), default="strict")
    parser.add_argument("--timeout", type=int, default=300)
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
