import sqlite3


def main():
    # Implicicly creates a new DB by connecting to it
    conn = sqlite3.connect("saga_storage.db")

    # Use a cursor to create a new table
    c = conn.cursor()
    c.execute("""
        CREATE TABLE employees (
            id INT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL,
            age INT NOT NULL
        )
        """)

    # Save the changes
    conn.commit()

    # Close the connection
    conn.close()


if __name__ == "__main__":
    main()
