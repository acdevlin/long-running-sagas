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
        "your_integration_name_here"  # Replace with the name of your preferred Orkes integration.
    )
    webhook_id: str = "your_webhook_id_here"  # Replace with your own webhook ID.
    webhook_endpoint_url: str = f"https://developer.orkescloud.com/webhook/{webhook_id}"
    source_header: str = (
        "your_source_header_here"  # Replace with your own source header.
    )
    user_id: str = "user_12345"

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
            user_id=self.user_id,
        )


settings = Settings.from_env()
