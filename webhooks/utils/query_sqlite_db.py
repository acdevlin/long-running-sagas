#!/usr/bin/env python3
"""Print every email stored by the webhook codelab."""

import sqlite3
import sys
from contextlib import closing
from pathlib import Path

DATABASE_PATH = Path(__file__).with_name("webhook_codelab_storage.db")


def fetch_emails(database_path: Path = DATABASE_PATH) -> list[sqlite3.Row]:
    """Return all stored emails in insertion order.

    Checking the path first prevents ``sqlite3.connect`` from silently creating
    an empty database when the codelab database has not been initialized.
    """
    if not database_path.is_file():
        raise FileNotFoundError(
            f"Database not found at {database_path}. " "Run create_sqlite_db.py first."
        )

    # closing() guarantees the connection is released after the rows are read.
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute("""
            SELECT *
            FROM emails
            ORDER BY id
            """).fetchall()


def print_emails(emails: list[sqlite3.Row]) -> None:
    """Print email rows in an aligned table with database field headings."""
    field_names = tuple(emails[0].keys())
    rows = [tuple(str(email[field]) for field in field_names) for email in emails]
    column_widths = [
        max(len(field), *(len(row[index]) for row in rows))
        for index, field in enumerate(field_names)
    ]

    def format_row(values: tuple[str, ...]) -> str:
        return " | ".join(
            value.ljust(column_widths[index])
            for index, value in enumerate(values)
        )

    print(format_row(field_names))
    print("-+-".join("-" * width for width in column_widths))
    for row in rows:
        print(format_row(row))


def main() -> int:
    """Query the codelab database and print readable email records."""
    try:
        emails = fetch_emails()
    except (FileNotFoundError, sqlite3.Error) as error:
        print(f"Unable to query stored emails: {error}", file=sys.stderr)
        return 1

    if not emails:
        print(f"No emails found in {DATABASE_PATH}")
        return 0

    print_emails(emails)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
