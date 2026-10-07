//! Register and start a durable webhook-driven workflow.
//!
//! The deploy-workflow step keeps its local workers running until the workflow reaches the
//! `WAIT_FOR_WEBHOOK` task, then exits. Conductor keeps the workflow suspended until the
//! send-webhook step sends a callback; the serve-agent step runs the local tools needed after it
//! resumes.

use std::collections::HashMap;
use std::time::{Duration, Instant};

use anyhow::{Context, Result, bail};
use conductor::agents::{AgentDef, AgentRuntime};
use conductor::client::{ConductorClient, WorkflowClient};
use conductor::configuration::Configuration;
use conductor::models::{
    StartWorkflowRequest, TaskStatus, WorkflowDef, WorkflowTask, WorkflowTimeoutPolicy,
};
use conductor::worker::TaskHandler;
use serde_json::Value;

use crate::settings::{self, LANGUAGE, Settings};
use crate::utils::agent_task::agent_task;
use crate::utils::webhook_agent::{WEBHOOK_AGENT_NAME, webhook_agent};
use crate::utils::workers;

/// Named after `LANGUAGE` in settings.rs, like every language version's workflow.
const WORKFLOW_NAME: &str = "wait_for_webhook_demo_rust";
const WORKFLOW_VERSION: i32 = 1;
const WAIT_TASK_REF: &str = "wait_for_webhook_ref";

const WORKFLOW_TIMEOUT_SECONDS: i64 = 7 * 24 * 60 * 60;
const READINESS_TIMEOUT: Duration = Duration::from_secs(60);
const READINESS_POLL_INTERVAL: Duration = Duration::from_secs(1);

// Shown in the workflow's description in the Orkes Conductor UI, and in every
// email this version sends, so you can tell the language versions apart.
const CODELAB_LANGUAGE: &str = "Rust";

/// Build the workflow definition, as JSON, without registering or starting it.
fn build_workflow() -> Result<Value> {
    // Exercise 2: Replace this with one get_user_emails task that resolves every address in
    // ${workflow.input.user_ids}, so the number of emails is decided at runtime. Pass it the
    // subject and body as well, for the forked send_email tasks.
    let get_email_task = WorkflowTask::simple("get_user_email", "get_user_email_ref")
        .with_input_param("user_id", "${workflow.input.user_id}");

    // Exercise 2: Send the emails with dynamic_fork_task from utils/dynamic_fork_task.rs, then
    // add WorkflowTask::join(reference_name, vec![]) straight after it, to wait for every branch.
    let send_email_task = WorkflowTask::simple("send_email", "send_email_ref")
        .with_input_param("recipients", "${get_user_email_ref.output.result}")
        .with_input_param("subject", format!("Hello from {CODELAB_LANGUAGE}"))
        .with_input_param(
            "body",
            format!("Sent by the {CODELAB_LANGUAGE} version of the webhooks codelab."),
        );

    let webhook_wait = WorkflowTask::wait_for_webhook(WAIT_TASK_REF).with_matches(HashMap::from([
        // Every language version shares one webhook, so only match
        // payloads sent by this language's send-webhook step.
        ("$['language']".into(), LANGUAGE.into()),
        ("$['type']".into(), "customer".into()),
        // Exercise 2: Change to 'user_ids'. Be sure the payload sent by
        // send_webhook_payload.rs matches the key you use here.
        ("$['user_id']".into(), "${workflow.input.user_id}".into()),
    ]));

    let workflow = WorkflowDef::new(WORKFLOW_NAME)
        .with_version(WORKFLOW_VERSION)
        .with_description(format!(
            "Durable wait-for-webhook example (registered from {CODELAB_LANGUAGE})"
        ))
        // Mark the execution TIMED_OUT if it runs longer than WORKFLOW_TIMEOUT_SECONDS,
        // for example because no webhook arrives. ALERT_ONLY would let it keep running.
        .with_timeout(WORKFLOW_TIMEOUT_SECONDS, WorkflowTimeoutPolicy::TimeOutWf)
        .with_task(get_email_task)
        .with_task(send_email_task)
        .with_task(webhook_wait)
        .with_output_param("agent_response", "${process_webhook_ref.output.text}");

    // The SDK's WorkflowTask can't have the AGENT type, so add that task to the JSON form of the
    // definition instead.
    let mut definition = serde_json::to_value(&workflow)?;
    definition["tasks"]
        .as_array_mut()
        .context("the workflow definition has no task list")?
        .push(agent_task(
            "process_webhook_ref",
            WEBHOOK_AGENT_NAME,
            "${wait_for_webhook_ref.output.agent_input}",
        ));
    Ok(definition)
}

/// Start one workflow execution and return its execution ID.
async fn start_workflow(workflow_client: &WorkflowClient) -> Result<String> {
    let request = StartWorkflowRequest::new(WORKFLOW_NAME)
        .with_version(WORKFLOW_VERSION)
        .with_input_value("user_id", settings::USER_ID);
    Ok(workflow_client.start_workflow(&request).await?)
}

/// Wait until the execution reaches its `WAIT_FOR_WEBHOOK` task.
async fn wait_until_webhook_ready(
    workflow_client: &WorkflowClient,
    workflow_id: &str,
) -> Result<()> {
    let deadline = Instant::now() + READINESS_TIMEOUT;

    while Instant::now() < deadline {
        let execution = workflow_client.get_workflow(workflow_id, true).await?;

        let waiting = execution.tasks.iter().any(|task| {
            task.reference_task_name == WAIT_TASK_REF && task.status == TaskStatus::InProgress
        });
        if waiting {
            // Exercise 1: Return this execution, with its tasks, so the caller can read every
            // send_email output (change the return type to Result<Workflow>).
            return Ok(());
        }

        if execution.is_terminal() {
            // WorkflowStatus has no Display, so print its name as the server sends it, such as
            // TIMED_OUT.
            let status = serde_json::to_value(execution.status)?;
            bail!(
                "workflow entered terminal status {}",
                status.as_str().unwrap_or_default()
            );
        }

        tokio::time::sleep(READINESS_POLL_INTERVAL).await;
    }

    bail!(
        "workflow did not reach {WAIT_TASK_REF} within {} seconds",
        READINESS_TIMEOUT.as_secs()
    )
}

/// Run the deploy-workflow step.
pub async fn run() -> Result<()> {
    let settings = Settings::from_env();
    // Build the agent first, so a malformed model setting fails before any worker starts.
    let agent = webhook_agent(&settings)?;

    let config = Configuration::from_env();
    // Polls for the tasks of every worker in utils/workers.rs until it is stopped below.
    let mut task_handler = TaskHandler::new(config.clone())?;
    for worker in workers::workers() {
        task_handler.add_worker(worker);
    }
    task_handler.start().await?;

    let result = deploy(config, &settings, &agent).await;
    // Stop the workers whether or not the steps above succeeded.
    let stopped = task_handler.stop().await;
    result?;
    Ok(stopped?)
}

/// Register the agent and workflow, start an execution, and wait until it reaches the
/// `WAIT_FOR_WEBHOOK` task.
async fn deploy(config: Configuration, settings: &Settings, agent: &AgentDef) -> Result<()> {
    // Register the agent that the workflow's AGENT task runs.
    AgentRuntime::new(config.clone())?.deploy(agent).await?;

    let client = ConductorClient::new(config)?;
    // The SDK's metadata client only accepts a WorkflowDef, so send the JSON definition with the
    // same request. PUT overwrites any earlier version with the same name and version.
    client
        .api_client()
        .put_no_response("/metadata/workflow", &[build_workflow()?])
        .await?;
    println!("Registered workflow {WORKFLOW_NAME}, version {WORKFLOW_VERSION}");

    let workflow_client = client.workflow_client();
    let workflow_id = start_workflow(&workflow_client).await?;
    println!(
        "Workflow URL: {}/execution/{workflow_id}",
        settings.server_base_url()
    );

    wait_until_webhook_ready(&workflow_client, &workflow_id).await?;
    // Exercise 1: Store a row in DATABASE_PATH (utils/query_sqlite_db.rs) for each completed
    // send_email task's output_data, matching on task_def_name: each task's reference_task_name
    // is unique from Exercise 2 on.
    println!("{WAIT_TASK_REF} is ready");
    println!(
        "Before sending the webhook, start the agent tool workers with \
         `cargo run -- serve-agent`, or restart them if you've changed the code since they started."
    );
    println!("Webhook URL: {}", settings.webhook_endpoint_url());
    Ok(())
}
