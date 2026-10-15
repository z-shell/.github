"""Check Lychee's immutable-cache key lifecycle across workflow executions."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/lychee.yml"


def cache_inputs():
    source = WORKFLOW.read_text()
    restore = source.split("        id: restore-cache\n", 1)[1].split(
        '      - name: "📊 Lychee Link Checker"', 1
    )[0]
    save = source.split('      - name: "📥 Save cache"', 1)[1].split(
        '      - name: "🔖 Create Issue From File"', 1
    )[0]

    def value(block, name):
        match = re.search(r"^          " + name + r": (.+)$", block, re.MULTILINE)
        if not match:
            raise AssertionError("Missing cache input: " + name)
        return match.group(1)

    return value(restore, "key"), value(restore, "restore-keys"), value(save, "key")


def expand(expression, context):
    def replace(match):
        return context[match.group(1).strip()]

    return re.sub(r"\$\{\{\s*(.*?)\s*\}\}", replace, expression)


class LycheeCacheTests(unittest.TestCase):
    def test_unchanged_commit_can_refresh_and_restore_an_expired_cache(self):
        restore_key, restore_prefix, save_key = cache_inputs()
        service = {}
        sha = "a" * 40
        executions = [("100", "1"), ("101", "1"), ("101", "2")]
        for number, (run_id, attempt) in enumerate(executions):
            with self.subTest(run_id=run_id, attempt=attempt):
                context = {
                    "github.sha": sha,
                    "github.run_id": run_id,
                    "github.run_attempt": attempt,
                    "runner.os": "Linux",
                }
                primary = expand(restore_key, context)
                prefix = expand(restore_prefix, context)
                matched = next(
                    (key for key in reversed(service) if key.startswith(prefix)), None
                )
                if number:
                    self.assertIsNotNone(matched, "Previous execution must be reusable")
                context["steps.restore-cache.outputs.cache-primary-key"] = primary
                destination = expand(save_key, context)
                # The real service cannot replace an existing key. The second
                # execution represents Lychee discarding an expired cache.
                self.assertNotIn(
                    destination, service, "Refreshed cache needs a new key"
                )
                service[destination] = "refreshed links"


if __name__ == "__main__":
    unittest.main()
