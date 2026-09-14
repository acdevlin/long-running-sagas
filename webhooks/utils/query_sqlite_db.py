#!/usr/bin/env python3
"""Print every email stored by the webhook codelab."""

import sqlite3
import sys
from collections.abc import Generator
from contextlib import closing, contextmanager
from pathlib import Path

DATABASE_PATH = Path(__file__).with_name("webhook_codelab_storage.db")


@contextmanager
def _open_read_only_database(
    database_path: Path = DATABASE_PATH,
) -> Generator[sqlite3.Connection]:
    """Helper function that opens a read-only connection to a specified database."""
    if not database_path.is_file():
        raise FileNotFoundError(
            f"Database not found at {database_path}. Run create_sqlite_db.py first."
        )

    # URI mode prevents this query helper and the agent tools that use it from
    # modifying the codelab database.
    database_uri = f"{database_path.resolve().as_uri()}?mode=ro"
    with closing(sqlite3.connect(database_uri, uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        yield connection


@contextmanager
def _open_read_only_database(
    database_path: Path = DATABASE_PATH,
) -> Generator[sqlite3.Connection]:
    """Helper function that opens a read-only connection to a specified database."""
    if not database_path.is_file():
        raise FileNotFoundError(
            f"Database not found at {database_path}. Run create_sqlite_db.py first."
        )

    # URI mode prevents this query helper and the agent tools that use it from
    # modifying the codelab database.
    database_uri = f"{database_path.resolve().as_uri()}?mode=ro"
    with closing(sqlite3.connect(database_uri, uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        yield connection


# Exercise 3: Reuse this read-only query for the recipient-history tool. The
# optional recipient argument limits the result to that recipient's records.
def fetch_emails(
    database_path: Path = DATABASE_PATH,
    recipient: str | None = None,
) -> list[sqlite3.Row]:
    """Return stored emails in insertion order, optionally for one recipient.

    Checking the path first prevents ``sqlite3.connect`` from silently creating
    an empty database when the codelab database has not been initialized.
    """
    query = """
        SELECT *
        FROM emails
        """
    parameters: tuple[str, ...] = ()
    if recipient is not None:
        query += "WHERE recipients = ?\n"
        parameters = (recipient,)
    query += "ORDER BY id"

    with _open_read_only_database(database_path) as connection:
        return connection.execute(query, parameters).fetchall()


def fetch_email_activity(
    database_path: Path = DATABASE_PATH,
) -> list[sqlite3.Row]:
    """Return one email-count row per recipient, ordered by activity."""
    query = """
        SELECT
            recipients AS recipient,
            COUNT(*) AS email_count
        FROM emails
        GROUP BY recipients
        ORDER BY email_count DESC, recipient
        """

    with _open_read_only_database(database_path) as connection:
        return connection.execute(query).fetchall()


def fetch_email_activity(
    database_path: Path = DATABASE_PATH,
) -> list[sqlite3.Row]:
    """Return one email-count row per recipient, ordered by activity."""
    query = """
        SELECT
            recipients AS recipient,
            COUNT(*) AS email_count
        FROM emails
        GROUP BY recipients
        ORDER BY email_count DESC, recipient
        """

    with _open_read_only_database(database_path) as connection:
        return connection.execute(query).fetchall()


# Exercise 3: Add a read-only query helper here that groups stored emails by
# recipient and returns each recipient with its email count for the summary tool.
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
            value.ljust(column_widths[index]) for index, value in enumerate(values)
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
    else:
        print_emails(emails)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
