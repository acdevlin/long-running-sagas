#!/usr/bin/env python3
import sqlite3
import os


def main():
    # Ensure the database file is created in the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "webhook_codelab_storage.db")

    # The schema is shared by every language version of this codelab
    schema_path = os.path.join(script_dir, "..", "..", "shared", "schema.sql")
    with open(schema_path, encoding="utf-8") as schema_file:
        schema = schema_file.read()

    # Implicitly creates a new DB by connecting to it
    conn = sqlite3.connect(db_path)

    # Create the tables defined in the shared schema
    conn.executescript(schema)

    # Save the changes
    conn.commit()

    # Close the connection
    conn.close()


if __name__ == "__main__":
    main()
