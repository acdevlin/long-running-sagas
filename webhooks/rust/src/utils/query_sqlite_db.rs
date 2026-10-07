//! Prints emails stored by the DB for the webhook codelab.

use std::path::Path;

use anyhow::{Context, Result, bail};
use rusqlite::{Connection, OpenFlags, Row, params_from_iter};
use serde::Serialize;

/// The local database file, which the create-db step creates in this project's folder.
pub const DATABASE_PATH: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/webhook_codelab_storage.db");

/// One row of the emails table.
#[derive(Debug, Serialize)]
pub struct Email {
    pub id: i64,
    pub sent_time: i64,
    pub subject: String,
    pub recipients: String,
}

/// The number of stored emails sent to one recipient.
#[derive(Debug, Serialize)]
pub struct EmailActivity {
    pub recipient: String,
    pub email_count: i64,
}

/// Open a connection to the codelab database, read-only unless `writable` is true. Opening a
/// missing file would create an empty database, so check the path first and open without creating
/// it.
pub fn open_database(writable: bool) -> Result<Connection> {
    if !Path::new(DATABASE_PATH).is_file() {
        bail!(
            "database not found at {DATABASE_PATH}; run the create-db step \
             (cargo run -- create-db) first"
        );
    }

    // Read-only mode prevents this query helper and the agent tools that use it from modifying the
    // codelab database. Neither mode creates the file.
    let flags = if writable {
        OpenFlags::SQLITE_OPEN_READ_WRITE
    } else {
        OpenFlags::SQLITE_OPEN_READ_ONLY
    };
    Ok(Connection::open_with_flags(DATABASE_PATH, flags)?)
}

/// Return the stored emails in insertion order, or only those sent to `recipient` if it is given.
pub fn fetch_emails(recipient: Option<&str>) -> Result<Vec<Email>> {
    let mut query = String::from(
        "
        SELECT id, sent_time, subject, recipients
        FROM emails
        ",
    );
    if recipient.is_some() {
        query += "WHERE recipients = ?\n";
    }
    query += "ORDER BY id";

    let connection = open_database(false)?;
    let mut statement = connection.prepare(&query)?;
    // The recipient, if any, is the query's only parameter.
    let emails = statement.query_map(params_from_iter(recipient), |row: &Row| {
        Ok(Email {
            id: row.get("id")?,
            sent_time: row.get("sent_time")?,
            subject: row.get("subject")?,
            recipients: row.get("recipients")?,
        })
    })?;
    Ok(emails.collect::<rusqlite::Result<_>>()?)
}

/// Return the number of emails sent to each recipient, ordered by activity.
pub fn fetch_email_activity() -> Result<Vec<EmailActivity>> {
    let query = "
        SELECT
            recipients AS recipient,
            COUNT(*) AS email_count
        FROM emails
        GROUP BY recipients
        ORDER BY email_count DESC, recipient
        ";

    let connection = open_database(false)?;
    let mut statement = connection.prepare(query)?;
    let activity = statement.query_map([], |row: &Row| {
        Ok(EmailActivity {
            recipient: row.get("recipient")?,
            email_count: row.get("email_count")?,
        })
    })?;
    Ok(activity.collect::<rusqlite::Result<_>>()?)
}

/// Print email rows in an aligned table with database field headings.
pub fn print_emails(emails: &[Email]) {
    let mut table = vec![vec![
        "id".to_owned(),
        "sent_time".to_owned(),
        "subject".to_owned(),
        "recipients".to_owned(),
    ]];
    for email in emails {
        table.push(vec![
            email.id.to_string(),
            email.sent_time.to_string(),
            email.subject.clone(),
            email.recipients.clone(),
        ]);
    }

    // Each column is as wide as its longest value, counting the heading as a value.
    let column_widths: Vec<usize> = (0..table[0].len())
        .map(|index| {
            table
                .iter()
                .map(|row| row[index].chars().count())
                .max()
                .unwrap_or(0)
        })
        .collect();

    let format_row = |values: &[String]| {
        values
            .iter()
            .zip(&column_widths)
            .map(|(value, &width)| format!("{value:<width$}"))
            .collect::<Vec<_>>()
            .join(" | ")
    };
    let dashes: Vec<String> = column_widths
        .iter()
        .map(|&width| "-".repeat(width))
        .collect();

    println!("{}", format_row(&table[0]));
    println!("{}", dashes.join("-+-"));
    for row in &table[1..] {
        println!("{}", format_row(row));
    }
}

/// Run the query-db step, which prints the stored emails as a table.
pub fn run() -> Result<()> {
    let emails = fetch_emails(None).context("unable to query stored emails")?;

    if emails.is_empty() {
        println!("No emails found in {DATABASE_PATH}");
    } else {
        print_emails(&emails);
    }
    Ok(())
}
