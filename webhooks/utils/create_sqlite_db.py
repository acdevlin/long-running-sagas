import sqlite3
import os


def main():
    # Ensure the database file is created in the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "webhook_codelab_storage.db")

    # Implicicly creates a new DB by connecting to it
    conn = sqlite3.connect(db_path)

    # Use a cursor to create a new table
    c = conn.cursor()
    c.execute("""
        CREATE TABLE emails (
            id INT PRIMARY KEY NOT NULL,
            sent_time INT NOT NULL,
            subject TEXT NOT NULL,
            recipients TEXT NOT NULL
        )
        """)

    # Save the changes
    conn.commit()

    # Close the connection
    conn.close()


if __name__ == "__main__":
    main()
