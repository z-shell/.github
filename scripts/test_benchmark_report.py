"""Adversarial and observable behavior tests for shared benchmark evidence."""

import copy
import json
import os
import subprocess  # nosec B404 - local validator, argv only.
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import benchmark_report as validator


def fixture(slow=False):
    def identity(label):
        return dict(
            label=label,
            source_revision="a" * 40,
            environment=dict(
                zsh_version="5.9.2",
                architecture="x86_64",
                cpu="fixture",
                runner_image="fixture-v1",
            ),
            workload=dict(samples=4, warmups=1),
        )

    def stats(n):
        return dict(median=n, p95=n, min=n, count=4, samples=[n] * 4)

    def row(after):
        return dict(
            results=dict(baseline=stats(10), candidate=stats(after)),
            change=dict(
                median_delta_ms=after - 10,
                median_delta_percent=(after - 10) * 10,
                p95_delta_ms=after - 10,
                p95_delta_percent=(after - 10) * 10,
            ),
            flag=after > 11,
        )

    return dict(
        schema_version=1,
        baseline=identity("baseline"),
        candidate=identity("candidate"),
        control_identity=identity("control"),
        comparable=True,
        cases={"fixture": row(12 if slow else 10)},
        control={"fixture": row(10)},
        thresholds=dict(median_percent=10, p95_percent=15),
        flagged=["fixture"] if slow else [],
        failed=[],
    )


class BenchmarkTests(unittest.TestCase):
    def test_control_and_slowdown(self):
        self.assertEqual(validator.validate_report(fixture()), ([], []))
        self.assertEqual(validator.validate_report(fixture(True)), (["fixture"], []))
        report = fixture(True)
        report["control"]["fixture"] = copy.deepcopy(report["cases"]["fixture"])
        self.assertEqual(validator.validate_report(report), (["fixture"], ["fixture"]))

    def test_raw_statistics_are_verified(self):
        for variant in ("baseline", "candidate"):
            for section in ("cases", "control"):
                for key, value in (
                    ("median", 9),
                    ("p95", 11),
                    ("min", 0),
                    ("count", True),
                    ("samples", [10]),
                    ("samples", [True] * 4),
                    ("samples", [float("nan")] * 4),
                    ("samples", [-1] * 4),
                ):
                    with self.subTest(
                        variant=variant, section=section, key=key, value=value
                    ):
                        report = fixture()
                        report[section]["fixture"]["results"][variant][key] = value
                        with self.assertRaises(ValueError):
                            validator.validate_report(report)

    def test_median_serialization_precision(self):
        validator.validate_stats(
            dict(samples=[1, 1.001], count=2, median=1.001, p95=1.001, min=1), 2
        )
        with self.assertRaises(ValueError):
            validator.validate_stats(
                dict(samples=[1, 1.001], count=2, median=1.002, p95=1.001, min=1), 2
            )

    def test_every_environment_and_workload_field_matters(self):
        for variant in ("candidate", "control_identity"):
            for group, keys in (
                ("environment", validator.ENVIRONMENT),
                ("workload", ("samples", "warmups")),
            ):
                for key in keys:
                    with self.subTest(variant=variant, group=group, key=key):
                        report = fixture()
                        report[variant][group][key] = (
                            "different" if group == "environment" else 5
                        )
                        with self.assertRaises(ValueError):
                            validator.validate_report(report)
        report = fixture()
        report["control_identity"]["source_revision"] = "b" * 40
        with self.assertRaises(ValueError):
            validator.validate_report(report)

    def test_control_provenance_for_zi_shape(self):
        report = fixture()
        control = report.pop("control_identity")
        control["schema_version"] = 1
        control["cases"] = {
            "fixture": copy.deepcopy(
                report["control"]["fixture"]["results"]["candidate"]
            )
        }
        self.assertEqual(validator.validate_report(report, control), ([], []))
        with self.assertRaises(ValueError):
            validator.validate_report(report)
        control["cases"]["fixture"]["samples"][0] = 11
        with self.assertRaises(ValueError):
            validator.validate_report(report, control)

    def test_failed_incomplete_and_unsupported_are_not_evidence(self):
        for section in ("cases", "control"):
            report = fixture()
            report[section]["fixture"] = {
                "failure": {"baseline": None, "candidate": "broken workload"}
            }
            report["failed"] = ["fixture"]
            with self.assertRaisesRegex(ValueError, "functional failures"):
                validator.validate_report(report)
        for key, value in (
            ("status", "incomplete"),
            ("comparable", False),
            ("schema_version", True),
            ("control", None),
            ("cases", {}),
            ("flagged", ["fixture"]),
        ):
            report = fixture()
            report[key] = value
            with self.assertRaises(ValueError):
                validator.validate_report(report)
        report = fixture()
        report["cases"]["fixture"] = {
            "unsupported": {"baseline": "missing API", "candidate": None}
        }
        with self.assertRaises(ValueError):
            validator.validate_report(report)

    def test_deltas_flags_and_policy_are_verified(self):
        for key, value in (("flag", True), ("change", {})):
            report = fixture()
            report["cases"]["fixture"][key] = value
            with self.assertRaises(ValueError):
                validator.validate_report(report)
        report = fixture()
        report["thresholds"]["median_percent"] = 20
        with self.assertRaises(ValueError):
            validator.validate_report(report)
        report = fixture(True)
        report["cases"]["fixture"]["change"]["p95_delta_percent"] = 15
        with self.assertRaises(ValueError):
            validator.validate_report(report)

    def test_cli_preserves_rejected_input_and_escapes_annotations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = fixture(True)
            hostile = "x|`[link](https://example.invalid)<img>\n::error::injected%"
            report["cases"][hostile] = report["cases"].pop("fixture")
            report["control"][hostile] = report["control"].pop("fixture")
            report["flagged"] = [hostile]
            path = root / "input.json"
            path.write_text(json.dumps(report))
            command = [
                sys.executable,
                str(Path(validator.__file__).resolve()),
                "--root",
                str(root),
                "--report",
                "input.json",
                "--output",
                str(root / "out"),
            ]
            result = subprocess.run(
                command,
                env={**os.environ, "GITHUB_STEP_SUMMARY": str(root / "summary.md")},
                capture_output=True,
                text=True,
                check=False,
            )  # nosec B603
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(len(result.stdout.splitlines()), 1)
            self.assertIn("%0A::error::injected%25", result.stdout)
            summary = (root / "summary.md").read_text()
            self.assertNotIn("<img>", summary)
            self.assertNotIn("[link]", summary)
            self.assertEqual((root / "out/report.json").read_bytes(), path.read_bytes())
            path.write_text('{"schema_version":1,"schema_version":1}')
            result = subprocess.run(
                command, capture_output=True, text=True, check=False
            )  # nosec B603
            self.assertEqual(result.returncode, 1)
            self.assertEqual(
                json.loads((root / "out/validation.json").read_text())["status"],
                "failed",
            )
            self.assertIn("No timings accepted", (root / "out/summary.md").read_text())

    def test_zero_baseline_and_exact_threshold(self):
        row = fixture()["cases"]["fixture"]
        for variant in row["results"].values():
            variant.update(median=0, p95=0, min=0, samples=[0] * 4)
        row["change"].update(median_delta_percent=None, p95_delta_percent=None)
        self.assertEqual(
            validator.validate_row(row, 4, validator.LIMITS), (False, False)
        )
        row = fixture()["cases"]["fixture"]
        row["results"]["candidate"].update(median=11, p95=11, min=11, samples=[11] * 4)
        row["change"].update(
            median_delta_ms=1,
            p95_delta_ms=1,
            median_delta_percent=10,
            p95_delta_percent=10,
        )
        self.assertEqual(
            validator.validate_row(row, 4, validator.LIMITS), (False, False)
        )

    def test_nonfinite_json_even_in_unknown_metadata_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for value in ("NaN", "Infinity", "-Infinity", "1e9999"):
                (root / "input.json").write_text('{"metadata":' + value + "}")
                with self.assertRaises(ValueError):
                    validator.read_report(root, "input.json", root / "copy")

    def test_paths_cannot_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "link").symlink_to(root / "missing")
            for name in ("", "../outside", "/outside", "link", ".git/config", "."):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    validator.read_report(root, name, root / "copy")


if __name__ == "__main__":
    unittest.main()
