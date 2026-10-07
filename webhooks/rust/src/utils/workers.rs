//! Worker tasks used by the webhook workflow.

use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

use conductor::worker;
use conductor::worker::{FnWorker, WorkerOutput};
use serde_json::{Map, Value, json};

// These shared names keep the worker's output synchronized with the workflow definition that reads
// it in the deploy-workflow step.
pub const DYNAMIC_TASKS_PARAM: &str = "dynamicTasks";
pub const DYNAMIC_TASKS_INPUTS_PARAM: &str = "dynamicTasksInputs";
pub const SEND_EMAIL_TASK_NAME: &str = "send_email";

/// Return a worker for each task that the workflow runs, for the deploy-workflow step's
/// `TaskHandler` to poll. `#[worker]` turns each function below into one whose name ends in
/// `_worker`, which creates that function's worker.
pub fn workers() -> Vec<FnWorker> {
    vec![get_user_emails_worker(), send_email_worker()]
}

/// Return one `send_email` task per user's email address, for the workflow's dynamic fork.
#[worker(name = "get_user_emails")]
async fn get_user_emails(user_ids: Vec<String>, subject: String, body: String) -> WorkerOutput {
    // With no user IDs the fork would send no emails, but the workflow would still wait for its
    // webhook, so fail instead. #[worker] passes an empty list if user_ids is missing or malformed.
    if user_ids.is_empty() {
        return WorkerOutput::failed("At least one user ID is required");
    }

    let mut dynamic_tasks = Vec::new();
    let mut dynamic_tasks_inputs = Map::new();
    for (index, user_id) in user_ids.iter().enumerate() {
        // A blank ID would produce an invalid address such as "@example.com".
        if user_id.trim().is_empty() {
            return WorkerOutput::failed(format!("Invalid user ID at index {index}"));
        }

        // The index keeps each reference name unique, even when a user ID repeats.
        let task_reference_name = format!("send_email_{index}");
        dynamic_tasks.push(json!({
            "name": SEND_EMAIL_TASK_NAME,
            "taskReferenceName": task_reference_name,
            "type": "SIMPLE",
        }));
        dynamic_tasks_inputs.insert(
            task_reference_name,
            json!({
                "recipients": format!("{user_id}@example.com"),
                "subject": subject,
                "body": body,
            }),
        );
    }
    WorkerOutput::completed(HashMap::from([
        (DYNAMIC_TASKS_PARAM.to_owned(), Value::Array(dynamic_tasks)),
        (
            DYNAMIC_TASKS_INPUTS_PARAM.to_owned(),
            Value::Object(dynamic_tasks_inputs),
        ),
    ]))
}

// A thread count above the default of 1 lets this worker send the forked emails in parallel.
// #[worker] only accepts a literal name, so this repeats SEND_EMAIL_TASK_NAME.
/// Simulate sending an email.
#[worker(name = "send_email", thread_count = 10)]
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
