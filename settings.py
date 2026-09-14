"""Shared settings for all codelabs.

Set `CONDUCTOR_AGENT_LLM_MODEL` as an environment variable to override the
default model used by all child modules, for example:

    export CONDUCTOR_AGENT_LLM_MODEL=anthropic/claude-sonnet-4-6
    export CONDUCTOR_AGENT_LLM_MODEL=google_gemini/gemini-2.0-flash
"""

import os
from dataclasses import dataclass


@dataclass
class Settings:
    llm_model: str = "openai/gpt-5-nano"  # Replace with your preferred LLM model.
    integration_name: str = (
        "OpenAi_Key"  # Replace with the name of your preferred Orkes integration.
    )
    webhook_id: str = (
        "r8ai01be9743-ac95-11f1-9216-4224b94c0a5f"  # Replace with your own webhook ID.
    )
    webhook_endpoint_url: str = f"https://developer.orkescloud.com/webhook/{webhook_id}"
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

    @classmethod
    def from_env(self) -> "Settings":
        return self(
            llm_model=(os.environ.get("CONDUCTOR_AGENT_LLM_MODEL") or self.llm_model),
            integration_name=(
                os.environ.get("CONDUCTOR_INTEGRATION_NAME") or self.integration_name
            ),
            webhook_id=self.webhook_id,
            webhook_endpoint_url=self.webhook_endpoint_url,
            source_header=self.source_header,
            user_ids=self.user_ids,
        )


settings = Settings.from_env()
