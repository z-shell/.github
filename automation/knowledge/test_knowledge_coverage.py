import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("knowledge_coverage", Path(__file__).with_name("knowledge-coverage.py"))
coverage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coverage)


class KnowledgeCoverageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = "knowledge/domains/agents/policy.md"
        (self.root / self.source).parent.mkdir(parents=True)
        (self.root / self.source).write_text("# Policy\n")
        (self.root / "AGENTS.md").write_text("# Delivery\n")
        (self.root / "config.json").write_text("{}\n")
        (self.root / "knowledge/delivery.json").write_text(json.dumps({"version": 1, "entries": [{"source": self.source, "target": "AGENTS.md"}]}))
        self.records = [
            {"path": "AGENTS.md", "domain": "agents", "disposition": "imported", "knowledge": self.source, "reason": "Complete policy delivery."},
            {"path": "config.json", "domain": "agents", "disposition": "referenced", "knowledge": "knowledge/domains/agents/repository-resources.md", "reason": "Runtime configuration."},
        ]
        self.write_inventory()

    def write_inventory(self):
        (self.root / coverage.MANIFEST).write_text(json.dumps({"version": 1, "files": self.records}))

    def run_check(self, write=False):
        with contextlib.redirect_stdout(io.StringIO()):
            return coverage.run(self.root, write)

    def test_standalone_coverage_and_generated_reference_drift(self):
        self.assertEqual(self.run_check(True), 0)
        self.assertEqual(self.run_check(), 0)
        page = self.root / self.records[1]["knowledge"]
        self.assertIn("../../../config.json", page.read_text())
        page.write_text(page.read_text() + "Unmanaged copy\n")
        with self.assertRaisesRegex(ValueError, "stale domain"):
            self.run_check()

    def test_added_and_removed_files_require_dispositions(self):
        self.run_check(True)
        new_file = self.root / "new.txt"
        new_file.write_text("New knowledge\n")
        with self.assertRaisesRegex(ValueError, "unclassified=.*new.txt"):
            self.run_check()
        new_file.unlink()
        (self.root / "config.json").unlink()
        with self.assertRaisesRegex(ValueError, "missing inventoried file"):
            self.run_check()

    def test_imports_must_match_declared_editable_source(self):
        self.records[0]["knowledge"] = "knowledge/domains/agents/other.md"
        self.write_inventory()
        with self.assertRaisesRegex(ValueError, "matching delivery owner"):
            self.run_check(True)

    def test_duplicate_and_escaping_paths_are_rejected_before_rendering(self):
        self.records.append(dict(self.records[1]))
        self.write_inventory()
        with self.assertRaisesRegex(ValueError, "duplicate file disposition"):
            self.run_check(True)
        self.records[-1]["path"] = "../outside.txt"
        self.write_inventory()
        with self.assertRaisesRegex(ValueError, "invalid repository-relative path"):
            self.run_check(True)
        self.assertFalse((self.root / self.records[1]["knowledge"]).exists())

    def test_git_discovery_keeps_tracked_and_nonignored_files_and_omits_deleted(self):
        (self.root / ".git").write_text("gitdir: registered-worktree\n")
        (self.root / "ignored.txt").write_text("Ignored local state\n")
        result = mock.Mock(stdout=b"AGENTS.md\0config.json\0deleted.txt\0knowledge/delivery.json\0")
        with mock.patch.object(coverage.subprocess, "run", return_value=result) as command:
            self.assertEqual(coverage.repository_files(self.root), {"AGENTS.md", "config.json"})
        self.assertIn("--cached", command.call_args.args[0])
        self.assertIn("--exclude-standard", command.call_args.args[0])

    def test_retired_allocation_directory_cannot_be_approved_in_inventory(self):
        path = self.root / "scripts/new.py"
        path.parent.mkdir()
        path.write_text("print('new')\n")
        self.records.append(dict(self.records[1], path="scripts/new.py"))
        self.write_inventory()
        with self.assertRaisesRegex(ValueError, "retired allocation directory"):
            self.run_check(True)


if __name__ == "__main__":
    unittest.main()
