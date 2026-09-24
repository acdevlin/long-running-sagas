"""Settings for the Python version of the webhooks codelab.

Account-specific values are read from environment variables so that every
language version of this codelab shares one configuration. Copy
``.env.example`` at the repository root to ``.env`` and fill it in; it is
loaded automatically below. Variables already exported in your shell take
precedence over the ones in ``.env``, for example:

    export CONDUCTOR_AGENT_LLM_MODEL=anthropic/claude-sonnet-4-6
    export CONDUCTOR_AGENT_LLM_MODEL=google_gemini/gemini-2.0-flash
    export CONDUCTOR_INTEGRATION_NAME=my_anthropic_integration
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

# Load before any Conductor Configuration is created so the SDK also picks up
# CONDUCTOR_SERVER_URL, CONDUCTOR_AUTH_KEY and CONDUCTOR_AUTH_SECRET from .env.
load_dotenv(REPOSITORY_ROOT / ".env")


@dataclass
class Settings:
    # Set CONDUCTOR_SERVER_URL in .env; the webhook URL is derived from it.
    conductor_server_url: str = "https://developer.orkescloud.com/api"
    # Set CONDUCTOR_AGENT_LLM_MODEL in .env to use a different model.
    llm_model: str = "openai/gpt-5-nano"
    # Set CONDUCTOR_INTEGRATION_NAME in .env.
    integration_name: str = "your_integration_name_here"
    # Identifies this language version in its workflow and agent names and in
    # the webhook payload, so every language version can share one webhook.
    language: str = "python"
    # Set WEBHOOK_ID in .env.
    webhook_id: str = "your_webhook_id_here"
    # Set WEBHOOK_SOURCE_HEADER in .env.
    source_header: str = "your_source_header_here"
    # Exercise 2: Add more user_ids to simulate multiple email recipients.
    # The workflow will send an email to each user_id in this list.
    # Exercise 3: Repeat one user ID so the agent has a clear most-active
    # recipient to identify from the stored email activity.
    user_id: str = "user_12345"

    @property
    def webhook_endpoint_url(self) -> str:
        """Webhook endpoint on the same Conductor cluster as the API."""
        base_url = self.conductor_server_url.rstrip("/").removesuffix("/api")
        return f"{base_url}/webhook/{self.webhook_id}"

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from the defaults above, applying any env overrides."""
        return cls(
            conductor_server_url=(
                os.environ.get("CONDUCTOR_SERVER_URL") or cls.conductor_server_url
            ),
            llm_model=(os.environ.get("CONDUCTOR_AGENT_LLM_MODEL") or cls.llm_model),
            integration_name=(
                os.environ.get("CONDUCTOR_INTEGRATION_NAME") or cls.integration_name
            ),
            webhook_id=(os.environ.get("WEBHOOK_ID") or cls.webhook_id),
            source_header=(
                os.environ.get("WEBHOOK_SOURCE_HEADER") or cls.source_header
            ),
        )


settings = Settings.from_env()
