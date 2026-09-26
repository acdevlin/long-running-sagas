/** Prints emails stored by the DB for the webhook codelab. */

import { statSync } from "node:fs";
import path from "node:path";
import { DatabaseSync, type SQLOutputValue } from "node:sqlite";

/** The local database file, created by the create-db step next to this file. */
export const DATABASE_PATH = path.join(import.meta.dirname, "webhook_codelab_storage.db");

/** One database row, keyed by column name. */
export type Row = Record<string, SQLOutputValue>;

/**
 * Open a read-only connection to the codelab database. Checking the path first gives a clear error
 * when the database has not been created yet.
 */
function openReadOnlyDatabase(): DatabaseSync {
  if (!statSync(DATABASE_PATH, { throwIfNoEntry: false })?.isFile()) {
    throw new Error(
      `Database not found at ${DATABASE_PATH}. Run the create-db step (npm run create-db) first.`,
    );
  }

  // Read-only mode prevents this query helper and the agent tools that use it from modifying the
  // codelab database.
  return new DatabaseSync(DATABASE_PATH, { readOnly: true });
}

// Exercise 3: Use the recipient argument in get_recipient_email_history to
// retrieve only the selected recipient's records.
/** Return stored emails in insertion order, optionally for one recipient. */
export function fetchEmails(recipient?: string): Row[] {
  let query = `
    SELECT *
    FROM emails
    `;
  const parameters: string[] = [];
  if (recipient !== undefined) {
    query += "WHERE recipients = ?\n";
    parameters.push(recipient);
  }
  query += "ORDER BY id";

  const database = openReadOnlyDatabase();
  try {
    return database.prepare(query).all(...parameters);
  } finally {
    database.close();
  }
}

// Exercise 3: Use these rows in summarize_email_activity to total the emails and return each
// recipient's activity. Each row's email_count is a number, although its type is SQLOutputValue.
/** Return one email-count row per recipient, ordered by activity. */
export function fetchEmailActivity(): Row[] {
  const query = `
    SELECT
      recipients AS recipient,
      COUNT(*) AS email_count
    FROM emails
    GROUP BY recipients
    ORDER BY email_count DESC, recipient
    `;

  const database = openReadOnlyDatabase();
  try {
    return database.prepare(query).all();
  } finally {
    database.close();
  }
}

/** Print email rows in an aligned table with database field headings. */
export function printEmails(emails: Row[]): void {
  const fieldNames = Object.keys(emails[0] ?? {});
  const rows = emails.map((email) => fieldNames.map((field) => String(email[field])));
  // Each column is as wide as its longest value, counting the heading as a value.
  const columnWidths = fieldNames.map((field) =>
    Math.max(field.length, ...emails.map((email) => String(email[field]).length)),
  );

  const formatRow = (values: string[]): string =>
    values.map((value, index) => value.padEnd(columnWidths[index] ?? 0)).join(" | ");

  console.log(formatRow(fieldNames));
  console.log(columnWidths.map((width) => "-".repeat(width)).join("-+-"));
  for (const row of rows) {
    console.log(formatRow(row));
  }
}

/** Query the codelab database and print readable email records. */
function main(): number {
  let emails: Row[];
  try {
    emails = fetchEmails();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`Unable to query stored emails: ${message}`);
    return 1;
  }

  if (emails.length === 0) {
    console.log(`No emails found in ${DATABASE_PATH}`);
  } else {
    printEmails(emails);
  }
  return 0;
}

// Run only as the query-db step, not when the agent's tools import this file.
if (import.meta.main) {
  process.exitCode = main();
}
