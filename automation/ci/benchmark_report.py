#!/usr/bin/env python3
"""Validate and present ADR-0024 comparisons without executing workloads."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
from pathlib import Path

ENVIRONMENT = ("zsh_version", "architecture", "cpu", "runner_image")
LIMITS = {"median_percent": 10, "p95_percent": 15}
MAX_BYTES = 16 * 1024 * 1024


class InvalidReport(ValueError):
    """A safe, fixed validation diagnostic, without report contents."""


def require(condition, message):
    if not condition:
        raise InvalidReport(message)


def number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def finite_float(value):
    result = float(value)
    require(math.isfinite(result), "non-finite JSON number")
    return result


def invalid_constant(_value):
    raise InvalidReport("non-finite JSON constant")


def read_report(root, name, output):
    relative = Path(name)
    require(
        name and not relative.is_absolute() and ".." not in relative.parts,
        "report must be a repository-relative regular file",
    )
    current = root
    for part in relative.parts:
        current /= part
        require(
            not current.is_symlink() and part != ".git",
            "report symlinks and Git metadata are rejected",
        )
    require(current.is_file(), "report is missing or not a regular file")
    current.resolve(strict=True).relative_to(root)
    require(current.stat().st_size <= MAX_BYTES, "report exceeds 16 MiB")
    raw = current.read_bytes()
    output.write_bytes(raw)
    report = json.loads(
        raw,
        object_pairs_hook=unique_object,
        parse_float=finite_float,
        parse_constant=invalid_constant,
    )
    require(isinstance(report, dict), "report must be a JSON object")
    return report


def identity(value):
    require(isinstance(value, dict), "missing report identity")
    for key in ("label", "source_revision"):
        require(
            isinstance(value.get(key), str)
            and value[key].strip() not in ("", "unknown", "pending"),
            "incomplete source identity",
        )
    environment = value.get("environment")
    workload = value.get("workload")
    require(
        isinstance(environment, dict) and isinstance(workload, dict),
        "missing environment or workload identity",
    )
    for key in ENVIRONMENT:
        require(
            isinstance(environment.get(key), str) and bool(environment[key].strip()),
            "incomplete environment identity",
        )
    for key, minimum in (("warmups", 1), ("samples", 2)):
        require(
            type(workload.get(key)) is int and workload[key] >= minimum,
            "invalid sample or warmup count",
        )
    return tuple(environment[key] for key in ENVIRONMENT), (
        workload["warmups"],
        workload["samples"],
    )


def close(actual, expected, tolerance=1e-9):
    return (
        number(actual)
        and number(expected)
        and math.isclose(actual, expected, rel_tol=1e-9, abs_tol=tolerance)
    )


def validate_stats(value, count):
    require(isinstance(value, dict), "invalid statistics object")
    samples = value.get("samples")
    require(
        isinstance(samples, list)
        and len(samples) == count
        and all(number(x) and x >= 0 for x in samples),
        "invalid raw samples",
    )
    require(
        type(value.get("count")) is int and value["count"] == count,
        "sample count mismatch",
    )
    expected = {
        "median": statistics.median(samples),
        "p95": sorted(samples)[math.ceil(0.95 * count) - 1],
        "min": min(samples),
    }
    for key, result in expected.items():
        # Zi serializes its median to three decimal places. Permit at most
        # half that unit; p95 and min select an existing raw sample exactly.
        tolerance = 0.000500001 if key == "median" else 1e-9
        require(
            number(value.get(key))
            and value[key] >= 0
            and close(value[key], result, tolerance),
            "summary statistics disagree with raw samples",
        )


def validate_row(row, count, thresholds):
    require(isinstance(row, dict), "invalid case row")
    if "failure" in row:
        require(set(row) == {"failure"}, "failure row contains accepted timing fields")
        failure = row["failure"]
        require(
            isinstance(failure, dict) and set(failure) == {"baseline", "candidate"},
            "invalid failure row",
        )
        require(
            all(
                v is None or isinstance(v, str) and bool(v.strip())
                for v in failure.values()
            )
            and any(failure.values()),
            "empty failure row",
        )
        return False, True
    require(
        set(row) == {"results", "change", "flag"},
        "case is not a complete version 1 comparison",
    )
    results = row["results"]
    require(
        isinstance(results, dict) and set(results) == {"baseline", "candidate"},
        "missing variant statistics",
    )
    for stats in results.values():
        validate_stats(stats, count)
    before, after = results["baseline"], results["candidate"]
    change = row["change"]
    require(isinstance(change, dict), "missing comparison deltas")
    expected = {}
    for key in ("median", "p95"):
        delta = after[key] - before[key]
        expected[key + "_delta_ms"] = delta
        expected[key + "_delta_percent"] = (
            delta * 100 / before[key] if before[key] else None
        )
    require(set(change) == set(expected), "invalid delta fields")
    for key, value in expected.items():
        require(
            change[key] is None if value is None else close(change[key], value),
            "comparison deltas disagree with statistics",
        )
    flag = any(
        expected[key + "_delta_percent"] is not None
        and expected[key + "_delta_percent"] > thresholds[key + "_percent"]
        for key in ("median", "p95")
    )
    require(type(row["flag"]) is bool and row["flag"] == flag, "incorrect timing flag")
    return flag, False


def validate_report(report, control_report=None):
    require(
        isinstance(report, dict)
        and type(report.get("schema_version")) is int
        and report["schema_version"] == 1,
        "unsupported report schema",
    )
    require(
        report.get("status", "complete") == "complete", "incomplete producer report"
    )
    baseline, candidate = report.get("baseline"), report.get("candidate")
    base_identity = identity(baseline)
    require(
        identity(candidate) == base_identity and report.get("comparable") is True,
        "incompatible environment or workload identities",
    )
    control_identity = report.get("control_identity", control_report)
    require(
        identity(control_identity) == base_identity
        and control_identity["source_revision"] == baseline["source_revision"],
        "control is not the baseline measured again",
    )
    if control_report is not None:
        require(
            isinstance(control_report, dict)
            and type(control_report.get("schema_version")) is int
            and control_report["schema_version"] == 1
            and control_report.get("status", "complete") == "complete",
            "invalid raw control report schema or status",
        )
        require(
            identity(control_report) == identity(control_identity)
            and control_report["source_revision"]
            == control_identity["source_revision"],
            "control provenance disagrees",
        )
    thresholds = report.get("thresholds", LIMITS)
    require(isinstance(thresholds, dict), "invalid thresholds")
    for key, limit in LIMITS.items():
        require(
            number(thresholds.get(key)) and 0 <= thresholds[key] <= limit,
            "threshold weakens ADR-0024 policy",
        )
    cases, control = report.get("cases"), report.get("control")
    require(
        isinstance(cases, dict)
        and cases
        and all(isinstance(k, str) and k.strip() for k in cases),
        "empty or invalid case inventory",
    )
    require(
        isinstance(control, dict) and set(control) == set(cases),
        "missing or mismatched A/A control cases",
    )
    if control_report is not None:
        require(
            isinstance(control_report.get("cases"), dict)
            and set(control_report["cases"]) == set(cases),
            "control provenance case inventory differs",
        )
    flags, failed, noise = [], set(), []
    for key in cases:
        for section, rows in (("cases", cases), ("control", control)):
            flag, failure = validate_row(rows[key], base_identity[1][1], thresholds)
            if failure:
                failed.add(key)
            if flag:
                (flags if section == "cases" else noise).append(key)
        if "results" in cases[key] and "results" in control[key]:
            require(
                cases[key]["results"]["baseline"]
                == control[key]["results"]["baseline"],
                "A/A control reuses different baseline measurements",
            )
        if control_report is not None and "results" in control[key]:
            require(
                control[key]["results"]["candidate"] == control_report["cases"][key],
                "control samples disagree with provenance",
            )
    for key, expected in (("flagged", set(flags)), ("failed", failed)):
        actual = report.get(key)
        require(
            isinstance(actual, list)
            and all(isinstance(x, str) for x in actual)
            and len(actual) == len(set(actual))
            and set(actual) == expected,
            "incorrect affected-case index",
        )
    require(not failed, "functional failures invalidate benchmark evidence")
    return flags, noise


def cell(value):
    # Encode punctuation as entities so report text cannot form Markdown or HTML.
    return (
        "<code>"
        + "".join(c if c.isalnum() or c == " " else f"&#{ord(c)};" for c in str(value))
        + "</code>"
    )


def markdown(report):
    lines = [
        "## Benchmark evidence",
        "",
        "Validated comparison. Timing flags request review and never fail the job; A/A flags show noise.",
        "",
        "| Case | Baseline median / p95 ms | Candidate median / p95 ms | Median / p95 change (%) | Review | A/A median / p95 change (%) | A/A review |",
        "| --- | ---: | ---: | ---: | --- | ---: | --- |",
    ]

    def percent(value):
        return "n/a" if value is None else f"{value:+.2f}"

    for key, row in report["cases"].items():
        control = report["control"][key]
        before, after = row["results"]["baseline"], row["results"]["candidate"]

        def delta(r):
            return " / ".join(
                percent(r["change"][s + "_delta_percent"]) for s in ("median", "p95")
            )

        lines.append(
            f"| {cell(key)} | {before['median']:.6g} / {before['p95']:.6g} | {after['median']:.6g} / {after['p95']:.6g} | {delta(row)} | {row['flag']} | {delta(control)} | {control['flag']} |"
        )
    return "\n".join(lines) + "\n"


def escape(value):
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def run(args):
    args.output.mkdir(parents=True, exist_ok=True)
    result = {"status": "failed", "message": "Report not validated"}
    try:
        root = args.root.resolve(strict=True)
        report = read_report(root, args.report, args.output / "report.json")
        control = (
            read_report(root, args.control_report, args.output / "control.json")
            if args.control_report
            else None
        )
        flags, noise = validate_report(report, control)
        result.update(
            status="passed",
            message="Valid comparison",
            flagged=flags,
            control_flagged=noise,
        )
        summary = markdown(report)
        for title, names in (("Candidate timing", flags), ("A/A noise", noise)):
            for name in names:
                print("::notice::" + escape(f"{title} flagged for review: {name}"))
    except InvalidReport as error:
        result["message"] = str(error)
        summary = (
            "## Benchmark evidence rejected\n\nNo timings accepted. "
            + result["message"]
            + "\n"
        )
        print("::error::" + result["message"])
    except (OSError, ValueError, TypeError, OverflowError, RecursionError):
        # Do not echo arbitrary decoder input, host paths or exception internals.
        result["message"] = (
            "Report rejected: malformed, incomplete, incompatible or failed evidence. Inspect the retained report and run the validator tests."
        )
        summary = (
            "## Benchmark evidence rejected\n\nNo timings accepted. "
            + result["message"]
            + "\n"
        )
        print("::error::" + result["message"])
    (args.output / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    (args.output / "summary.md").write_text(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
            stream.write(summary)
    return int(result["status"] != "passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--report", required=True)
    parser.add_argument(
        "--control-report",
        default="",
        help="Raw control report when the comparison omits control_identity",
    )
    parser.add_argument("--output", type=Path, required=True)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
