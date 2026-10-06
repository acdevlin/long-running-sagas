//! Worker tasks used by the webhook workflow.

use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

use conductor::worker;
use conductor::worker::{FnWorker, WorkerOutput};
use serde_json::json;

/// Return a worker for each task that the workflow runs, for the deploy-workflow step's
/// `TaskHandler` to poll. `#[worker]` turns each function below into one whose name ends in
/// `_worker`, which creates that function's worker.
pub fn workers() -> Vec<FnWorker> {
    // Exercise 2: Return get_user_emails_worker() instead.
    vec![get_user_email_worker(), send_email_worker()]
}

// Exercise 2: Change to "get_user_emails", taking `user_ids: Vec<String>`. Return the fork's
// send_email tasks, each of type "SIMPLE" with a unique taskReferenceName (Exercise 3 repeats a
// user ID), and a map from each taskReferenceName to that task's input (see dynamic_fork_task.rs).
/// Return the email address associated with a user, which `#[worker]` stores as the task output
/// "result".
#[worker(name = "get_user_email")]
async fn get_user_email(user_id: String) -> String {
    format!("{user_id}@example.com")
}

// Exercise 2: Set thread_count in #[worker], which is 1 by default, so this worker sends the
// forked emails in parallel.
/// Simulate sending an email.
#[worker(name = "send_email")]
async fn send_email(recipients: String, subject: String, body: String) -> WorkerOutput {
    println!("Sending email\nTo: {recipients}\nSubject: {subject}\nBody: {body}");
    let sent_time = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    WorkerOutput::completed(HashMap::from([
        ("sent_time".to_owned(), json!(sent_time)),
        ("subject".to_owned(), json!(subject)),
        ("recipients".to_owned(), json!(recipients)),
    ]))
}
