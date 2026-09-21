"""Shared settings for all codelabs.

Set `CONDUCTOR_AGENT_LLM_MODEL` or `CONDUCTOR_INTEGRATION_NAME` as environment
variables to override the defaults used by all child modules, for example:

    export CONDUCTOR_AGENT_LLM_MODEL=anthropic/claude-sonnet-4-6
    export CONDUCTOR_AGENT_LLM_MODEL=google_gemini/gemini-2.0-flash
    export CONDUCTOR_INTEGRATION_NAME=my_anthropic_integration
"""

import os
from dataclasses import dataclass


@dataclass
class Settings:
    llm_model: str = "openai/gpt-5-nano"  # Replace with your preferred LLM model.
    integration_name: str = (
        "your_integration_name_here"  # Replace with the name of your preferred Orkes integration.
    )
    webhook_id: str = "your_webhook_id_here"  # Replace with your own webhook ID.
    source_header: str = (
        "wait-for-webhook-demo-value"  # Replace with the value of your own "source" header.
    )
    # A tuple keeps the configured recipients immutable; request builders convert
    # it to a list only when producing a JSON array for Conductor.
    user_ids: tuple[str, ...] = (
        # Repeats give Exercise 3 a clear most-active recipient to identify.
        "alex",
        "alex",
        "alex",
        "user_1",
        "user_2",
        "user_555",
    )

    @property
    def webhook_endpoint_url(self) -> str:
        """Webhook endpoint derived from the current ``webhook_id``."""
        return f"https://developer.orkescloud.com/webhook/{self.webhook_id}"

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from the defaults above, applying any env overrides."""
        return cls(
            llm_model=(os.environ.get("CONDUCTOR_AGENT_LLM_MODEL") or cls.llm_model),
            integration_name=(
                os.environ.get("CONDUCTOR_INTEGRATION_NAME") or cls.integration_name
            ),
        )


settings = Settings.from_env()
