//! Agent definition that is used in the wait-for-webhook example workflow. The agent is configured
//! to use the LLM model and integration from settings.rs, and summarizes stored email activity
//! with its tools.

use anyhow::{Result, bail};
use conductor::agents::AgentDef;
use conductor::error::ConductorError;
use conductor::tool;
use schemars::JsonSchema;
use serde::Deserialize;
use serde_json::json;

use crate::settings::Settings;
use crate::utils::query_sqlite_db::{fetch_email_activity, fetch_emails};

// Read-only database tools for the agent. The serve-agent step runs each tool as a Conductor worker
// task, and the agent receives the tool's result as JSON.

// The arguments of summarize_email_activity, which takes none. These aren't doc comments, because
// schemars would copy them into the tool's input schema, which the LLM reads.
#[derive(Deserialize, JsonSchema)]
struct SummarizeEmailActivityArgs {}

#[tool(
    description = "Return the total number of stored emails and the number sent to each \
                   recipient. Call this first."
)]
async fn summarize_email_activity(
    _args: SummarizeEmailActivityArgs,
) -> conductor::Result<serde_json::Value> {
    // The SDK only accepts its own error type from a tool.
    let recipient_activity =
        fetch_email_activity().map_err(|error| ConductorError::agent(format!("{error:#}")))?;
    let total_emails: i64 = recipient_activity.iter().map(|row| row.email_count).sum();
    Ok(json!({
        "total_emails": total_emails,
        // has_activity tells the agent whether there is any recipient history to look up.
        "has_activity": !recipient_activity.is_empty(),
        "recipient_activity": recipient_activity,
    }))
}

// The arguments of get_recipient_email_history.
#[derive(Deserialize, JsonSchema)]
struct GetRecipientEmailHistoryArgs {
    recipient: String,
}

#[tool(
    description = "Return every stored email for one recipient. Pass the exact recipient \
                   email address from summarize_email_activity."
)]
async fn get_recipient_email_history(
    args: GetRecipientEmailHistoryArgs,
) -> conductor::Result<serde_json::Value> {
    // An empty recipient matches no emails. A terminal error fails the call without retries, since
    // they would fail the same way.
    if args.recipient.is_empty() {
        return Err(ConductorError::terminal_tool(
            "A recipient email address is required",
        ));
    }
    let emails = fetch_emails(Some(&args.recipient))
        .map_err(|error| ConductorError::agent(format!("{error:#}")))?;
    Ok(json!({
        "recipient": args.recipient,
        "email_count": emails.len(),
        "emails": emails,
    }))
}

/// The name the agent is deployed under, which the workflow's `AGENT` task refers to. Named after
/// `LANGUAGE` in settings.rs, like every language version's agent.
pub const WEBHOOK_AGENT_NAME: &str = "webhook_customer_service_rust";

/// Build the agent definition, checking that the LLM model setting is well formed.
pub fn webhook_agent(settings: &Settings) -> Result<AgentDef> {
    let Some((_, model)) = settings.llm_model.split_once('/') else {
        bail!(
            "CONDUCTOR_AGENT_LLM_MODEL must use the 'provider/model' format, for example \
             'openai/gpt-5-nano'; got '{}'",
            settings.llm_model
        );
    };

    let agent = AgentDef::new(WEBHOOK_AGENT_NAME)?
        .with_model(format!("{}/{model}", settings.integration_name))
        .with_instructions(
            "You are an email activity analyst. First call summarize_email_activity. If \
             has_activity is false, do not call get_recipient_email_history; return a concise \
             digest stating that there is no stored email activity. Otherwise, identify the \
             recipient with the greatest email_count, breaking ties by choosing the \
             alphabetically first recipient. Then call get_recipient_email_history with that \
             exact recipient. Base every factual claim on the tool results and return a concise, \
             multi-line activity digest.",
        )
        .with_tools([
            summarize_email_activity_tool(),
            get_recipient_email_history_tool(),
        ])
        // Enough turns for both tool calls and the final digest, with two to spare.
        .with_max_turns(5)?
        .with_temperature(0.2);
    Ok(agent)
}
