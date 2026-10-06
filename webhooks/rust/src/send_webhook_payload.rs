//! Send a webhook payload to the specified Orkes webhook endpoint.

use std::time::Duration;

use anyhow::{Result, bail};
use serde_json::json;

use crate::settings::{self, LANGUAGE, Settings};

/// Run the send-webhook step.
pub async fn run() -> Result<()> {
    let settings = Settings::from_env();

    let payload = json!({
        // The same list as the workflow's input, which the WAIT_FOR_WEBHOOK task matches on.
        "user_ids": settings::USER_IDS,
        "type": "customer",
        // Exercise 3: Replace this prompt with a request to summarize stored email
        // activity, inspect the busiest recipient's history, and return a digest.
        "agent_input": "Introduce yourself, then inform the user that their email has been sent.",
        // Every language version shares one webhook; this key selects this
        // language's workflow (see the matches in the deploy-workflow step).
        "language": LANGUAGE,
    });

    let response = reqwest::Client::builder()
        .timeout(Duration::from_secs(30))
        .build()?
        .post(settings.webhook_endpoint_url())
        .header("Accept", "application/json")
        .header("source", &settings.source_header)
        .json(&payload)
        .send()
        .await?;

    let status = response.status();
    println!("Status: {}", status.as_u16());
    println!("Response: {}", response.text().await?);

    // Return an error for HTTP error responses (for example, 4xx and 5xx).
    if !status.is_success() {
        bail!("webhook request failed with status {}", status.as_u16());
    }

    println!("Webhook was accepted by Orkes Conductor.");
    Ok(())
}
