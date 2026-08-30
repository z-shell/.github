from __future__ import annotations

import importlib.util
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from types import ModuleType

sys.dont_write_bytecode = True
SCRIPT_PATH = Path(__file__).with_name("decision-records.py")
PUBLIC_ROOT = SCRIPT_PATH.resolve().parent.parent


def load_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("decision_records", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load_validator()

VALID_RECORD = """# 1. A Valid Decision

- **Status:** ACCEPTED
- **Date:** 2026-05-29
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** None

## Context

Context body.
"""


class DecisionRecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)
        self.root = Path(self._temporary_directory.name)
        (self.root / "decisions").mkdir()

    def write_record(self, filename: str, text: str) -> None:
        (self.root / "decisions" / filename).write_text(text, encoding="utf-8")

    def errors(self) -> list[str]:
        _records, errors = validator.collect(self.root)
        return errors

    def test_valid_record_has_no_errors(self) -> None:
        self.write_record("0001-a-valid-decision.md", VALID_RECORD)
        self.assertEqual(self.errors(), [])

    def test_empty_directory_has_no_errors(self) -> None:
        self.assertEqual(self.errors(), [])

    def test_rejects_legacy_section_header(self) -> None:
        self.write_record(
            "0001-legacy.md",
            textwrap.dedent("""\
                # 1. Legacy Shape

                Date: 2026-05-29

                ## Status

                ACCEPTED
                """),
        )
        errors = self.errors()
        self.assertTrue(any("header block must start at line 3" in e for e in errors))

    def test_rejects_accepted_record_without_deciders(self) -> None:
        self.write_record("0001-no-decider.md", VALID_RECORD.replace("ss-o", "TBD"))
        errors = self.errors()
        self.assertTrue(
            any("must name the accepting maintainer" in e for e in errors), errors
        )

    def test_allows_proposed_record_without_deciders(self) -> None:
        text = VALID_RECORD.replace("ACCEPTED", "PROPOSED").replace("ss-o", "TBD")
        self.write_record("0001-proposed.md", text)
        self.assertEqual(self.errors(), [])

    def test_rejects_ai_agent_decider(self) -> None:
        for identity in (
            "Claude Code",
            "Gemini CLI",
            "Copilot",
            "Codex",
            "renovate[bot]",
        ):
            with self.subTest(identity=identity):
                self.write_record(
                    "0001-agent-decider.md",
                    VALID_RECORD.replace("ss-o", f"ss-o, {identity}"),
                )
                errors = self.errors()
                self.assertTrue(any("automation identity" in e for e in errors), errors)

    def test_allows_human_deciders(self) -> None:
        self.write_record(
            "0001-humans.md", VALID_RECORD.replace("ss-o", "ss-o, wicoop")
        )
        self.assertEqual(self.errors(), [])

    def test_rejects_unknown_status(self) -> None:
        self.write_record("0001-unknown.md", VALID_RECORD.replace("ACCEPTED", "MAYBE"))
        errors = self.errors()
        self.assertTrue(any("is not a recognized status" in e for e in errors), errors)

    def test_rejects_non_iso_date(self) -> None:
        self.write_record(
            "0001-bad-date.md", VALID_RECORD.replace("2026-05-29", "29 May 2026")
        )
        errors = self.errors()
        self.assertTrue(any("ISO 8601 calendar date" in e for e in errors), errors)

    def test_rejects_title_number_mismatch(self) -> None:
        self.write_record("0002-mismatch.md", VALID_RECORD.replace("# 1.", "# 7."))
        errors = self.errors()
        self.assertTrue(any("does not match filename number" in e for e in errors))

    def test_rejects_out_of_order_header_fields(self) -> None:
        text = textwrap.dedent("""\
            # 1. Reordered

            - **Date:** 2026-05-29
            - **Status:** ACCEPTED
            - **Deciders:** ss-o
            - **Supersedes:** None
            - **Superseded by:** None

            ## Context
            """)
        self.write_record("0001-reordered.md", text)
        errors = self.errors()
        self.assertTrue(any("must be exactly, and in order" in e for e in errors))

    def test_ignores_non_record_filenames(self) -> None:
        self.write_record("0001-a-valid-decision.md", VALID_RECORD)
        self.write_record("README.md", "# Not a record\n")
        self.assertEqual(self.errors(), [])

    def test_check_reports_missing_index(self) -> None:
        self.write_record("0001-a-valid-decision.md", VALID_RECORD)
        status, errors = validator.run(self.root, check_only=True)
        self.assertEqual(status, 1)
        self.assertTrue(any("out of date" in e for e in errors), errors)

    def test_write_then_check_is_stable(self) -> None:
        self.write_record("0001-a-valid-decision.md", VALID_RECORD)
        self.assertEqual(validator.run(self.root, check_only=False), (0, []))
        self.assertEqual(validator.run(self.root, check_only=True), (0, []))

    def test_index_lists_records_in_numeric_order(self) -> None:
        self.write_record("0002-second.md", VALID_RECORD.replace("# 1.", "# 2."))
        self.write_record("0010-tenth.md", VALID_RECORD.replace("# 1.", "# 10."))
        self.write_record("0001-a-valid-decision.md", VALID_RECORD)
        validator.run(self.root, check_only=False)
        index = (self.root / "decisions/README.md").read_text(encoding="utf-8")
        self.assertLess(index.index("[0001]"), index.index("[0002]"))
        self.assertLess(index.index("[0002]"), index.index("[0010]"))


class PublicRepositoryTests(unittest.TestCase):
    """The real repository must satisfy its own decision-record contract."""

    def test_public_records_and_index_are_valid(self) -> None:
        status, errors = validator.run(PUBLIC_ROOT, check_only=True)
        self.assertEqual(errors, [])
        self.assertEqual(status, 0)

    def test_index_is_declared_in_the_manifest(self) -> None:
        manifest = (PUBLIC_ROOT / ".github/instruction-surfaces.json").read_text()
        self.assertIn("decisions/README.md", manifest)
        self.assertIn("scripts/decision-records.py", manifest)


if __name__ == "__main__":
    unittest.main()
