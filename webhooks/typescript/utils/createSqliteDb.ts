/** Create the local database used from Exercise 1 onward. */

import { readFileSync } from "node:fs";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import { DATABASE_PATH } from "./querySqliteDb.ts";

// The schema is shared by every language version of this codelab.
const SCHEMA_PATH = path.join(import.meta.dirname, "..", "..", "shared", "schema.sql");

function main(): void {
  const schema = readFileSync(SCHEMA_PATH, "utf8");

  // Implicitly creates a new DB by opening it.
  const database = new DatabaseSync(DATABASE_PATH);
  try {
    // Create the tables defined in the shared schema. exec runs every statement in it.
    database.exec(schema);
  } finally {
    database.close();
  }
}

main();
