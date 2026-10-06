//! The Rust version of the webhooks codelab. Run a step from this folder with
//! `cargo run -- <step>`, for example `cargo run -- deploy-workflow`.

use std::process::ExitCode;

use anyhow::Result;
use tracing_subscriber::EnvFilter;
use webhooks_codelab::utils::{create_sqlite_db, query_sqlite_db};
use webhooks_codelab::{
    deploy_wait_for_webhook_workflow, send_webhook_payload, serve_webhook_agent, settings,
};

/// The name of every step, as `cargo run -- <step>` takes it.
const STEPS: [&str; 5] = [
    "create-db",
    "deploy-workflow",
    "serve-agent",
    "send-webhook",
    "query-db",
];

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let step = match args.as_slice() {
        [step] if STEPS.contains(&step.as_str()) => step,
        _ => {
            eprintln!("Usage: cargo run -- <{}>", STEPS.join("|"));
            return ExitCode::FAILURE;
        }
    };

    if let Err(error) = run(step) {
        // {:#} also prints the errors that caused this one, separated by colons.
        eprintln!("{step}: {error:#}");
        return ExitCode::FAILURE;
    }
    ExitCode::SUCCESS
}

/// Run one step, after loading `.env` and setting up the SDK's logging.
fn run(step: &str) -> Result<()> {
    // Load .env before the async runtime below starts its threads: changing environment variables
    // while another thread might read them is unsafe.
    settings::load_env_file()?;
    // Show the SDK's warnings and errors, or what RUST_LOG asks for, such as RUST_LOG=info.
    let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("warn"));
    tracing_subscriber::fmt().with_env_filter(filter).init();

    // Runs the steps that use the Conductor SDK, which is async.
    let runtime = tokio::runtime::Runtime::new()?;
    match step {
        "create-db" => create_sqlite_db::run(),
        "deploy-workflow" => runtime.block_on(deploy_wait_for_webhook_workflow::run()),
        "serve-agent" => runtime.block_on(serve_webhook_agent::run()),
        "send-webhook" => runtime.block_on(send_webhook_payload::run()),
        "query-db" => query_sqlite_db::run(),
        _ => unreachable!("main only runs the steps in STEPS"),
    }
}
