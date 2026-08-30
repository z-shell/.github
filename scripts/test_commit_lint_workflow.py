#!/usr/bin/env python3
"""Regression tests for the local commit-lint reusable-workflow caller."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALLER = ROOT / ".github/workflows/lint-commits.yml"
REUSABLE = ROOT / ".github/workflows/commit-lint.yml"


def permission_names(text: str, indent: int) -> set[str]:
    prefix = " " * indent
    block_pattern = re.compile(
        rf"(?m)^{prefix}permissions:\n"
        rf"((?:^{prefix}  [a-z-]+: (?:read|write|none)\n)+)"
    )
    permission_pattern = re.compile(r"(?m)^\s*([a-z-]+):")
    return {
        permission
        for block in block_pattern.findall(text)
        for permission in permission_pattern.findall(block)
    }


class CommitLintWorkflowTests(unittest.TestCase):
    def test_caller_grants_every_permission_requested_by_called_jobs(self) -> None:
        caller_permissions = permission_names(CALLER.read_text(), indent=0)
        called_permissions = permission_names(REUSABLE.read_text(), indent=4)

        self.assertTrue(called_permissions, "reusable workflow requests no permissions")
        self.assertEqual(called_permissions - caller_permissions, set())


if __name__ == "__main__":
    unittest.main()
