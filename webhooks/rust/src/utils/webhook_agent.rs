//! Agent definition that is used in the wait-for-webhook example workflow. The agent is configured
//! to use the LLM model and integration from settings.rs. It is designed to process customer
//! service requests in a concise, professional, and safe manner.

use anyhow::{Result, bail};
use conductor::agents::AgentDef;

use crate::settings::Settings;

// Exercise 3: Define two tools here with the SDK's #[tool] macro: summarize_email_activity
// (total and per-recipient counts, making an empty database clear) and
// get_recipient_email_history (one recipient's email records).
// Exercise 3: Each tool is an async fn that takes one struct of arguments, deriving Deserialize and
// JsonSchema to describe the tool's parameters. Give #[tool] a description, which the LLM reads to
// decide when and how to call the tool.

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
        // Exercise 3: Tell the agent to call summarize_email_activity first, and return a
        // no-activity digest if it is empty. Otherwise it should call
        // get_recipient_email_history for the busiest recipient, then return a final digest.
        .with_instructions(
            "You are a customer-service agent. Process the user's request concisely, \
             professionally, and safely without running any code or making any external API calls.",
        )
        // Exercise 3: Register both tools with .with_tools([...]), and set .with_max_turns(...)?
        // (it returns a Result) high enough for both tool calls and the final response.
        .with_temperature(0.2);
    Ok(agent)
}
