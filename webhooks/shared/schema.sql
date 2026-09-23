-- Schema for the webhooks codelab's local SQLite database.
-- Every language's create-db step runs this file.
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    sent_time INTEGER NOT NULL,
    subject TEXT NOT NULL,
    recipients TEXT NOT NULL
);
