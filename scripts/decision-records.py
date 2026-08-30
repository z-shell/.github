#!/usr/bin/env python3
"""Validate ADR header blocks and render the decision index.

Why this exists:

`decisions/` had no index and no machine-checked header contract. A decision
record whose status went stale, or whose header used a different shape from its
neighbours, was discoverable only by reading every file. That is exactly the
class of drift the organization asks to catch with an executable check rather
than prose.

This script owns two related outputs so they cannot disagree:

1. the header contract for every `decisions/NNNN-*.md` record, and
2. the generated index at `decisions/README.md`.

Usage:

    python3 scripts/decision-records.py            # write the index
    python3 scripts/decision-records.py --check    # verify, change nothing
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

DECISIONS_DIRECTORY = "decisions"
INDEX_PATH = f"{DECISIONS_DIRECTORY}/README.md"
RECORD_PATTERN = re.compile(r"^(\d{4})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
TITLE_PATTERN = re.compile(r"^# (\d+)\. (.+)$")
FIELD_PATTERN = re.compile(r"^- \*\*(?P<field>[^:*]+):\*\*(?P<value>.*)$")

REQUIRED_FIELDS = (
    "Status",
    "Date",
    "Deciders",
    "Supersedes",
    "Superseded by",
)
ALLOWED_STATUSES = (
    "PROPOSED",
    "ACCEPTED",
    "REJECTED",
    "SUPERSEDED",
)
UNRESOLVED_DECIDERS = ("TBD", "None", "")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

INDEX_HEADER = """<!--
GENERATED FILE. DO NOT EDIT DIRECTLY.
Regenerate: python3 scripts/decision-records.py
Check: python3 scripts/decision-records.py --check
-->

# Architecture decision records

Durable organization decisions. Draft new records with `runbooks/adr.md`; only
a maintainer moves a record from `PROPOSED` to `ACCEPTED`.

"""


def error(path: str, rule: str, fix: str) -> str:
    return f"{path}: {rule}; fix: {fix}"


class Record:
    """One parsed decision record."""

    def __init__(self, path: str, number: int, title: str, fields: dict[str, str]):
        self.path = path
        self.number = number
        self.title = title
        self.fields = fields

    @property
    def filename(self) -> str:
        return Path(self.path).name

    @property
    def file_number(self) -> int:
        """The number encoded in the filename, which orders the index."""
        match = RECORD_PATTERN.match(self.filename)
        if match is None:  # pragma: no cover - filenames are filtered on collection
            raise ValueError(f"{self.path} is not a decision record filename")
        return int(match.group(1))

    @property
    def status(self) -> str:
        return self.fields.get("Status", "")

    @property
    def date(self) -> str:
        return self.fields.get("Date", "")

    @property
    def deciders(self) -> str:
        return self.fields.get("Deciders", "")


def _record_paths(root: Path) -> list[Path]:
    directory = root / DECISIONS_DIRECTORY
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and RECORD_PATTERN.match(path.name)
    )


def _parse_header(text: str) -> tuple[int | None, str, dict[str, str], list[str]]:
    """Return the record number, title, header fields, and structural problems."""
    lines = text.splitlines()
    problems: list[str] = []

    if not lines:
        return None, "", {}, ["file is empty"]

    title_match = TITLE_PATTERN.match(lines[0])
    if title_match is None:
        return None, "", {}, ["first line must be '# <number>. <title>'"]
    number = int(title_match.group(1))
    title = title_match.group(2).strip()

    if len(lines) < 2 or lines[1].strip() != "":
        problems.append("the title must be followed by one blank line")

    fields: dict[str, str] = {}
    order: list[str] = []
    for line in lines[2:]:
        if line.strip() == "":
            break
        field_match = FIELD_PATTERN.match(line)
        if field_match is None:
            if order:
                # A continuation line belongs to the field opened above it.
                fields[order[-1]] = f"{fields[order[-1]]} {line.strip()}".strip()
                continue
            problems.append("the header block must start at line 3")
            break
        field = field_match.group("field").strip()
        if field in fields:
            problems.append(f"duplicate header field {field!r}")
            continue
        fields[field] = field_match.group("value").strip()
        order.append(field)

    if order and tuple(order) != REQUIRED_FIELDS:
        expected = ", ".join(REQUIRED_FIELDS)
        problems.append(f"header fields must be exactly, and in order: {expected}")

    return number, title, fields, problems


def _validate_record(
    path: str, number: int | None, record: Record | None, problems: list[str]
) -> list[str]:
    fix = (
        "match the header block used by the other records in decisions/ "
        "and rerun python3 scripts/decision-records.py --check"
    )
    errors = [error(path, problem, fix) for problem in problems]
    if record is None:
        return errors

    filename_number = record.file_number
    if record.number != filename_number:
        errors.append(
            error(
                path,
                f"title number {record.number} does not match filename number "
                f"{filename_number}",
                f"renumber the title heading to '# {filename_number}. ...'",
            )
        )

    if record.status not in ALLOWED_STATUSES:
        allowed = ", ".join(ALLOWED_STATUSES)
        errors.append(
            error(
                path,
                f"status {record.status!r} is not a recognized status",
                f"set Status to one of: {allowed}",
            )
        )

    if record.status == "ACCEPTED" and record.deciders in UNRESOLVED_DECIDERS:
        errors.append(
            error(
                path,
                "an ACCEPTED record must name the accepting maintainer",
                "record the accepting maintainer's handle in Deciders "
                "(see runbooks/adr.md)",
            )
        )

    if not DATE_PATTERN.match(record.date):
        errors.append(
            error(
                path,
                f"date {record.date!r} is not an ISO 8601 calendar date",
                "set Date to a YYYY-MM-DD value",
            )
        )

    return errors


def collect(root: Path) -> tuple[list[Record], list[str]]:
    records: list[Record] = []
    errors: list[str] = []
    seen_numbers: dict[int, str] = {}

    for record_path in _record_paths(root):
        display_path = f"{DECISIONS_DIRECTORY}/{record_path.name}"
        try:
            text = record_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(
                error(
                    display_path,
                    f"cannot read decision record: {exc}",
                    f"restore a readable UTF-8 file at {display_path}",
                )
            )
            continue

        number, title, fields, problems = _parse_header(text)
        record = (
            Record(display_path, number, title, fields) if number is not None else None
        )
        errors.extend(_validate_record(display_path, number, record, problems))
        if record is None:
            continue

        filename_number = record.file_number
        if filename_number in seen_numbers:
            errors.append(
                error(
                    display_path,
                    f"decision number {filename_number} is already used by "
                    f"{seen_numbers[filename_number]!r}",
                    "give every decision record a unique number",
                )
            )
        else:
            seen_numbers[filename_number] = display_path
        records.append(record)

    records.sort(key=lambda item: item.file_number)
    return records, errors


def render_index(records: list[Record]) -> str:
    """Render the index table.

    Columns are padded to the widest cell so the generated file is already in
    the repository formatter's preferred shape. Without this, `trunk fmt` would
    rewrite the table and `--check` would then report the freshly generated
    index as out of date.
    """
    headings = ("ADR", "Title", "Status", "Date", "Deciders")
    rows: list[tuple[str, ...]] = []
    for record in records:
        rows.append(
            (
                f"[{record.file_number:04d}]({record.filename})",
                record.title,
                record.status,
                record.date,
                record.deciders or "TBD",
            )
        )

    widths = [
        max(len(heading), *(len(row[column]) for row in rows)) if rows else len(heading)
        for column, heading in enumerate(headings)
    ]

    def render_row(cells: tuple[str, ...]) -> str:
        padded = (cell.ljust(widths[column]) for column, cell in enumerate(cells))
        return f"| {' | '.join(padded)} |"

    separator = f"| {' | '.join('-' * width for width in widths)} |"
    lines = [render_row(headings), separator]
    lines.extend(render_row(row) for row in rows)
    return INDEX_HEADER + "\n".join(lines) + "\n"


def run(root: Path, check_only: bool) -> tuple[int, list[str]]:
    root = root.resolve()
    records, errors = collect(root)
    if errors:
        return 1, sorted(set(errors))

    if not records:
        return 0, []

    expected = render_index(records)
    index_path = root / INDEX_PATH

    if check_only:
        try:
            current = index_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            current = None
        if current != expected:
            return 1, [
                error(
                    INDEX_PATH,
                    "the decision index is missing or out of date",
                    "run python3 scripts/decision-records.py and commit the result",
                )
            ]
        return 0, []

    index_path.write_text(expected, encoding="utf-8")
    return 0, []


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate decision records and render the decision index"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to the script's repository)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify records and the index without writing anything",
    )
    arguments = parser.parse_args()

    status, errors = run(arguments.root, arguments.check)
    for message in errors:
        print(f"ERROR: {message}")
    if status == 0:
        print(
            "decision record validation passed"
            if arguments.check
            else f"wrote {INDEX_PATH}"
        )
    return status


if __name__ == "__main__":
    raise SystemExit(main())
