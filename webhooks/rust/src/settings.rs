//! Settings for the Rust version of the webhooks codelab.
//!
//! Account-specific values are read from environment variables so that every language version of
//! this codelab shares one configuration. Copy `.env.example` at the repository root to `.env` and
//! fill it in; [`load_env_file`] reads it. Variables already exported in your shell take precedence
//! over the ones in `.env`, for example:
//!
//! ```text
//! export CONDUCTOR_AGENT_LLM_MODEL=anthropic/claude-sonnet-4-6
//! export CONDUCTOR_INTEGRATION_NAME=my_anthropic_integration
//! ```

use std::env;
use std::io::ErrorKind;

use anyhow::{Context, Result};

/// Identifies this language version in its workflow and agent names and in the webhook payload,
/// so every language version can share one webhook.
pub const LANGUAGE: &str = "rust";

/// The workflow sends an email to each user ID in this list. Repeating "alex" gives the agent a
/// clear most-active recipient to identify from the stored email activity.
pub const USER_IDS: &[&str] = &["alex", "alex", "alex", "user_1", "user_2", "user_555"];

/// The `.env` file at the repository root, two folders above this project's `Cargo.toml`.
const ENV_PATH: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../../.env");

/// Add the values in `.env` to the environment, skipping any variable the shell already sets. The
/// SDK reads `CONDUCTOR_SERVER_URL`, `CONDUCTOR_AUTH_KEY` and `CONDUCTOR_AUTH_SECRET` from the
/// environment, so call this before creating any Conductor client.
pub fn load_env_file() -> Result<()> {
    match dotenvy::from_path(ENV_PATH) {
        Err(dotenvy::Error::Io(error)) if error.kind() == ErrorKind::NotFound => Ok(()),
        result => result.with_context(|| format!("load {ENV_PATH}")),
    }
}

/// The account-specific values, read from the shell or `.env`.
#[derive(Debug)]
pub struct Settings {
    /// Set by `CONDUCTOR_SERVER_URL`; the webhook URL is derived from it.
    pub conductor_server_url: String,
    /// Set by `CONDUCTOR_AGENT_LLM_MODEL`, in 'provider/model' format.
    pub llm_model: String,
    /// Set by `CONDUCTOR_INTEGRATION_NAME`.
    pub integration_name: String,
    /// Set by `WEBHOOK_ID`.
    pub webhook_id: String,
    /// Set by `WEBHOOK_SOURCE_HEADER`.
    pub source_header: String,
}

impl Settings {
    /// Read the settings from the environment, after [`load_env_file`] has added `.env` to it.
    pub fn from_env() -> Self {
        Self {
            conductor_server_url: read(
                "CONDUCTOR_SERVER_URL",
                "https://developer.orkescloud.com/api",
            ),
            llm_model: read("CONDUCTOR_AGENT_LLM_MODEL", "openai/gpt-5-nano"),
            integration_name: read("CONDUCTOR_INTEGRATION_NAME", "your_integration_name_here"),
            webhook_id: read("WEBHOOK_ID", "your_webhook_id_here"),
            source_header: read("WEBHOOK_SOURCE_HEADER", "your_source_header_here"),
        }
    }

    /// The Conductor cluster URL without its /api suffix, which the UI and webhooks share.
    pub fn server_base_url(&self) -> &str {
        let url = self.conductor_server_url.trim_end_matches('/');
        url.strip_suffix("/api").unwrap_or(url)
    }

    /// The webhook endpoint on the same Conductor cluster as the API.
    pub fn webhook_endpoint_url(&self) -> String {
        format!("{}/webhook/{}", self.server_base_url(), self.webhook_id)
    }
}

/// Return a variable from the shell or `.env`, treating an empty value as unset.
fn read(name: &str, default_value: &str) -> String {
    env::var(name)
        .ok()
        .map(|value| value.trim().to_owned())
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| default_value.to_owned())
}
