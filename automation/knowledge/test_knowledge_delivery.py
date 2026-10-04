import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import hashlib

spec = importlib.util.spec_from_file_location("knowledge_delivery", Path(__file__).with_name("knowledge-delivery.py"))
delivery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)


class KnowledgeDeliveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.entry = {"source": "knowledge/domains/ci/contract.md", "target": ".github/instructions/ci/contract.instructions.md"}
        self.source = self.root / self.entry["source"]
        self.source.parent.mkdir(parents=True)
        self.source.write_text('---\napplyTo: "**"\n---\n\n# Contract\n\n[policy](../../../AGENTS.md#policy)\n')
        self.write_manifest([self.entry])

    def write_manifest(self, entries):
        (self.root / delivery.MANIFEST).write_text(json.dumps({"version": 1, "entries": entries}))

    def run_delivery(self, check):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return delivery.run(self.root, check)

    def test_generation_preserves_frontmatter_links_and_full_content(self):
        self.assertEqual(self.run_delivery(False), 0)
        target = self.root / self.entry["target"]
        text = target.read_text()
        self.assertTrue(text.startswith('---\napplyTo: "**"\n---\n'))
        self.assertIn('# Contract', text)
        self.assertIn('[policy](../../../AGENTS.md#policy)', text)
        self.assertIn('GENERATED from knowledge/domains/ci/contract.md', text)
        self.assertEqual(self.run_delivery(True), 0)
        self.assertEqual(self.run_delivery(False), 0)
        self.assertEqual(target.read_text(), text)

    def test_source_change_and_manual_consumer_edit_both_fail_check(self):
        self.run_delivery(False)
        self.source.write_text(self.source.read_text() + '\nNew rule.\n')
        self.assertEqual(self.run_delivery(True), 1)
        self.run_delivery(False)
        target = self.root / self.entry["target"]
        target.write_text(target.read_text() + '\nUnmanaged rule.\n')
        self.assertEqual(self.run_delivery(True), 1)

    def test_invalid_later_entry_cannot_modify_an_earlier_consumer(self):
        self.run_delivery(False)
        target = self.root / self.entry["target"]
        original = target.read_bytes()
        self.source.write_text(self.source.read_text() + '\nChanged rule.\n')
        self.write_manifest([self.entry, {"source": "knowledge/domains/ci/missing.md", "target": "runbooks/missing.md"}])
        with self.assertRaises(OSError):
            self.run_delivery(False)
        self.assertEqual(target.read_bytes(), original)

    def test_duplicate_entries_and_escape_paths_are_rejected(self):
        for entries in ([self.entry, self.entry], [{"source": self.entry['source'], "target": "../outside.md"}]):
            with self.subTest(entries=entries):
                self.write_manifest(entries)
                with self.assertRaises(ValueError):
                    self.run_delivery(False)

    def test_symlinked_source_and_consumer_ancestors_are_rejected(self):
        self.source.unlink()
        external = self.root / 'external.md'
        external.write_text('Do not deliver')
        self.source.symlink_to(external)
        with self.assertRaises(ValueError):
            self.run_delivery(False)
        self.source.unlink()
        self.source.write_text('Safe source')
        (self.root / '.github').symlink_to(self.root / 'knowledge', target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_delivery(False)

    def test_link_relocation_roundtrip_preserves_fragment_query_and_definitions(self):
        source = self.root / 'runbooks/procedure.md'
        destination = self.root / 'knowledge/domains/governance/procedure.md'
        text = '[local](./other.md?q=yes#section)\n[ref]: ../AGENTS.md#policy\n[directory](../decisions/)\n[web](https://example.org/path)\n[anchor](#local)\n'
        moved = delivery.rebase_links(text, source, destination)
        self.assertIn('https://example.org/path', moved)
        self.assertIn('[anchor](#local)', moved)
        self.assertEqual(delivery.rebase_links(moved, destination, source), text)

    def test_duplicate_json_keys_are_rejected(self):
        (self.root / delivery.MANIFEST).write_text('{"version":1,"version":1,"entries":[]}')
        with self.assertRaises(ValueError):
            self.run_delivery(False)

    def project_entry(self):
        return {
            "repository": "z-shell/tool", "source": self.entry["source"],
            "target": self.entry["target"], "revision": "a" * 40,
            "source_blob": "b" * 40, "content_sha256": "c" * 64,
            "project_revision": "d" * 40, "project_source_blob": "e" * 40,
        }

    def test_project_render_preserves_frontmatter_and_rebases_both_owners(self):
        entry = self.project_entry()
        text = '---\napplyTo: "internal/**"\n---\n\n# Full contract\n[org](../../../AGENTS.md#rules)\n[project](https://github.com/z-shell/tool/blob/' + entry["project_revision"] + '/docs/rules.md?q=yes#rule)\n[ref]: ../../../runbooks/triage.md\n[local](#local)\n'
        rendered = delivery.render_project(text, entry)
        self.assertTrue(rendered.startswith('---\napplyTo: "internal/**"\n---\n'))
        self.assertIn('# Full contract', rendered)
        self.assertIn('https://github.com/z-shell/.github/blob/' + entry['revision'] + '/AGENTS.md#rules', rendered)
        self.assertIn('[project](../../../docs/rules.md?q=yes#rule)', rendered)
        self.assertIn('[local](#local)', rendered)
        self.assertIn('[ref]: https://github.com/z-shell/.github/blob/', rendered)
        self.assertIn('"source_blob":"' + entry['source_blob'] + '"', rendered)

    def test_project_manifest_rejects_undeclared_targets_unsafe_paths_and_pins(self):
        entry = self.project_entry()
        downstream = [{"repository": entry["repository"], "surfaces": [{"path": entry["target"]}]}]
        manifest = self.root / delivery.PROJECT_MANIFEST
        for field, value in [("source", "knowledge/domains/../escape.md"), ("revision", "main"), ("content_sha256", "bad"), ("target", "AGENTS.md"), ("repository", "z-shell/other")]:
            with self.subTest(field=field):
                invalid = {**entry, field: value}
                manifest.write_text(json.dumps({"version": 1, "consumers": [invalid]}))
                with self.assertRaises(ValueError):
                    delivery.load_project_entries(self.root, downstream)
        manifest.write_text(json.dumps({"version": 1, "consumers": [entry, entry]}))
        with self.assertRaises(ValueError):
            delivery.load_project_entries(self.root, downstream)

    def test_project_check_rejects_body_provenance_and_symlink_drift(self):
        entry = self.project_entry()
        rendered = delivery.render_project(self.source.read_text(), entry)
        entry['content_sha256'] = hashlib.sha256(rendered.encode()).hexdigest()
        target = self.root / entry['target']
        target.parent.mkdir(parents=True)
        target.write_text(rendered)
        self.assertEqual(delivery.check_project(self.root, entry['repository'], [entry]), [])
        for changed in (
            rendered + 'Changed rule\n',
            rendered.replace(entry['revision'], 'f' * 40),
            rendered.replace('applyTo: "**"', 'applyTo: "other/**"'),
            rendered.replace('AGENTS.md#policy', 'missing.md#policy'),
        ):
            target.write_text(changed)
            self.assertTrue(delivery.check_project(self.root, entry['repository'], [entry]))
        target.unlink()
        self.assertTrue(delivery.check_project(self.root, entry['repository'], [entry]))
        target.symlink_to(self.source)
        with self.assertRaises(ValueError):
            delivery.check_project(self.root, entry['repository'], [entry])

    def test_project_render_rejects_escaping_links_and_unterminated_frontmatter(self):
        for text in ('[escape](../../../../../outside.md)', '---\napplyTo: "**"\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                delivery.render_project(text, self.project_entry())


if __name__ == '__main__':
    unittest.main()
