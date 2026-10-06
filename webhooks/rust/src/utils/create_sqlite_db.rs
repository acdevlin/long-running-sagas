//! Create the local database used from Exercise 1 onward.

use std::fs;

use anyhow::{Context, Result};
use rusqlite::Connection;

use super::query_sqlite_db::DATABASE_PATH;

/// The schema that every language version of this codelab shares.
const SCHEMA_PATH: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../shared/schema.sql");

/// Run the create-db step, which creates the tables in the shared schema.
pub fn run() -> Result<()> {
    let schema = fs::read_to_string(SCHEMA_PATH).with_context(|| format!("read {SCHEMA_PATH}"))?;

    // Implicitly creates a new DB by opening it.
    let connection = Connection::open(DATABASE_PATH)?;

    // Create the tables defined in the shared schema. execute_batch runs every statement in it.
    connection.execute_batch(&schema)?;
    Ok(())
}
