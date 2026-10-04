#!/usr/bin/env python3
"""Coverage boundaries, unavailable evidence and change-impact regression tests."""

import base64
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from automation.agents.test_org_routing import OrgFixture, installed_skill, make_downstream

SPEC = importlib.util.spec_from_file_location(
    "org_policy_report", Path(__file__).with_name("org_policy_report.py")
)
assert SPEC and SPEC.loader
report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(report)


def repository(name, **kwargs):
    return {
        "full_name": f"z-shell/{name}",
        "private": False,
        "fork": False,
        "archived": False,
        **kwargs,
    }


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.fixture = OrgFixture(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_inventory_pages_preserve_exclusions_and_missing_consumers(self):
        inventory = [
            [repository("plain"), repository("new")],
            [
                repository("fork", fork=True),
                repository("old", archived=True),
                repository(".github"),
            ],
        ]
        result = report.coverage(self.fixture.root, inventory)
        states = {r["repository"]: r["classification"] for r in result["results"]}
        self.assertEqual(result["inventory_count"], 5)
        self.assertEqual(states["z-shell/new"], "unassessed")
        self.assertEqual(states["z-shell/fork"], "unassessed-fork")
        self.assertEqual(states["z-shell/old"], "excluded-archived")
        self.assertEqual(states["z-shell/tool"], "inventory-missing")
        self.assertEqual(states["z-shell/.github"], "canonical-owner")

    def test_invalid_inventory_is_not_silent_coverage(self):
        for value in (
            {},
            [repository("plain"), repository("plain")],
            [{"full_name": "z-shell/x"}],
            [repository("../x")],
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                report.inventory_rows(value)

    def test_project_source_selects_declared_complete_consumer(self):
        source = "knowledge/domains/tooling/project.md"
        record = {
            "repository": "z-shell/tool", "source": source,
            "target": ".github/instructions/go.instructions.md",
            "revision": "a" * 40, "source_blob": "b" * 40,
            "project_revision": "c" * 40, "project_source_blob": "d" * 40,
            "content_sha256": "e" * 64,
        }
        (self.fixture.root / report.delivery.PROJECT_MANIFEST).write_text(
            json.dumps({"version": 1, "consumers": [record]})
        )
        result = report.impact(self.fixture.root, [source])
        self.assertEqual(result["changes"][0]["relationship"], "delivers-approved-project-knowledge")
        self.assertEqual(result["changes"][0]["candidate_repositories"], ["z-shell/tool"])
        self.assertIn(report.delivery.PROJECT_MANIFEST, result["canonical_inputs"])

    def test_local_pass_does_not_imply_published_adoption(self):
        checkout = make_downstream(self.root, self.fixture.revision)
        org = self.fixture.load()
        entry = org.downstream[1]
        (checkout / "AGENTS.md").write_text(report.routing.render(entry, org))
        result = report.coverage(
            self.fixture.root, [repository("tool")], {"z-shell/tool": str(checkout)}
        )
        row = result["results"][0]
        self.assertEqual(row["local"]["status"], "passed")
        self.assertEqual(row["published"]["status"], "unverified")

    def test_live_failure_is_unavailable_not_missing(self):
        def unavailable(_):
            raise report.EvidenceError("read unavailable")

        row = report.coverage(
            self.fixture.root, [repository("tool")], live=True, api=unavailable
        )["results"][0]
        self.assertEqual(row["published"]["status"], "unavailable")

    def test_published_file_evidence_survives_rules_api_failure(self):
        org = self.fixture.load()
        entry = org.downstream[1]
        contents = {
            "AGENTS.md": report.routing.render(entry, org),
            ".github/skills/code-review/SKILL.md": installed_skill(
                self.fixture.revision
            ),
            ".github/workflows/check.yml": "jobs:\n  routing:\n    uses: "
            + report.CALLER
            + "a" * 40
            + " # main\n",
        }
        blobs = {str(i): text for i, text in enumerate(contents.values())}
        tree = {
            "truncated": False,
            "tree": [
                {
                    "path": path,
                    "sha": str(i),
                    "mode": "100644",
                    "type": "blob",
                    "size": len(text),
                }
                for i, (path, text) in enumerate(contents.items())
            ],
        }
        seen = []

        def api(endpoint, **kwargs):
            seen.append(endpoint)
            if endpoint.endswith("/tool"):
                return {"default_branch": "main"}
            if "/commits/" in endpoint:
                return {"sha": "b" * 40}
            if "/git/trees/" in endpoint:
                return tree
            if "/git/blobs/" in endpoint:
                return {
                    "content": base64.b64encode(
                        blobs[endpoint.rsplit("/", 1)[1]].encode()
                    ).decode()
                }
            self.assertEqual(kwargs, {"paginate": True})
            raise report.EvidenceError("rules inaccessible")

        result = report.published("z-shell/tool", entry, org, api)
        self.assertEqual(result["routing_block"], "current")
        self.assertEqual(result["skills"]["code-review"]["content"], "current")
        self.assertTrue(result["caller_references"][0]["immutable"])
        self.assertEqual(result["ruleset_required_checks"], "unverified")
        self.assertEqual(result["runtime_discovery"], "unverified")
        self.assertIn("repos/z-shell/tool/git/trees/" + "b" * 40 + "?recursive=1", seen)

    def test_truncated_tree_cannot_produce_absence_findings(self):
        responses = iter(
            [{"default_branch": "main"}, {"sha": "a" * 40}, {"truncated": True}]
        )
        with self.assertRaises(report.EvidenceError):
            report.published(
                "z-shell/tool",
                self.fixture.manifest["downstream"][1],
                self.fixture.load(),
                lambda _: next(responses),
            )

    def test_skill_impact_is_limited_to_declared_vendors(self):
        result = report.impact(
            self.fixture.root,
            [
                ".github/skills/code-review/SKILL.md",
                "runbooks/triage.md",
                "actions/example/action.yml",
                "knowledge/domains/documentation/templates/zsh-plugin.md",
                "unknown.txt",
            ],
        )
        by_path = {r["path"]: r for r in result["changes"]}
        self.assertEqual(
            by_path[".github/skills/code-review/SKILL.md"]["candidate_repositories"],
            ["z-shell/tool"],
        )
        self.assertEqual(
            by_path["runbooks/triage.md"]["candidate_repositories"],
            ["z-shell/plain", "z-shell/tool"],
        )
        self.assertEqual(
            by_path["actions/example/action.yml"]["relationship"],
            "caller-inventory-required",
        )
        self.assertEqual(
            by_path["unknown.txt"]["relationship"], "unmapped-review-required"
        )
        self.assertEqual(
            by_path["knowledge/domains/documentation/templates/zsh-plugin.md"]["relationship"],
            "caller-inventory-required",
        )
        with self.assertRaises(ValueError):
            report.impact(self.fixture.root, ["../private"])

    def test_github_pagination_is_read_only_and_flattens_pages(self):
        with patch.object(
            report,
            "command",
            return_value=json.dumps([[repository("a")], [repository("b")]]),
        ) as command:
            rows = report.github("orgs/z-shell/repos?per_page=100", paginate=True)
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            command.call_args.args[0],
            [
                "gh",
                "api",
                "--method",
                "GET",
                "orgs/z-shell/repos?per_page=100",
                "--paginate",
                "--slurp",
            ],
        )

    def test_knowledge_source_impact_matches_its_complete_consumer(self):
        entries = [
            {"source": "knowledge/domains/quality/testing.md", "target": ".github/instructions/testing.instructions.md"},
            {"source": "knowledge/domains/ci/action.md", "target": "actions/example/README.md"},
        ]
        manifest = self.fixture.root / report.delivery.MANIFEST
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({"version": 1, "entries": entries}))
        for entry in entries:
            with self.subTest(source=entry["source"]):
                result = report.impact(self.fixture.root, [entry["source"], entry["target"]])
                source, consumer = result["changes"]
                self.assertEqual(source["relationship"], consumer["relationship"])
                self.assertEqual(source["candidate_repositories"], consumer["candidate_repositories"])
                self.assertIn(report.delivery.MANIFEST, result["canonical_inputs"])
        row = report.impact(self.fixture.root, ["knowledge/domains/quality/unmapped.md"])["changes"][0]
        self.assertEqual(row["relationship"], "unmapped-review-required")
        self.assertEqual(row["candidate_repositories"], [])

    def test_invalid_delivery_map_cannot_silently_omit_impact(self):
        manifest = self.fixture.root / report.delivery.MANIFEST
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text('{"version": 1, "entries": []}')
        with self.assertRaises(ValueError):
            report.impact(self.fixture.root, ["knowledge/domains/quality/testing.md"])


if __name__ == "__main__":
    unittest.main()
