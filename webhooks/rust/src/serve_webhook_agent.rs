//! Serve the local database tools used by the post-webhook agent.

use anyhow::Result;
use conductor::agents::AgentRuntime;
use conductor::configuration::Configuration;

use crate::settings::Settings;
use crate::utils::webhook_agent::webhook_agent;

/// Run the serve-agent step, which deploys the agent and serves its tool workers until
/// interrupted.
pub async fn run() -> Result<()> {
    let agent = webhook_agent(&Settings::from_env())?;
    let mut runtime = AgentRuntime::new(Configuration::from_env())?;

    // serve only starts the tool workers, so deploy the agent first.
    runtime.deploy(&agent).await?;
    // serve returns once the workers are polling, and fails if the agent has no tools, as before
    // Exercise 3.
    if !agent.tools.is_empty() {
        runtime.serve(&agent).await?;
    }

    println!("Serving the agent's tool workers. Press Ctrl+C to stop.");
    tokio::signal::ctrl_c().await?;
    Ok(runtime.shutdown().await?)
}
