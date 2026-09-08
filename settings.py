"""Shared settings for all examples.

Set ``CONDUCTOR_AGENT_LLM_MODEL`` as an environment variable to override the
default model used by all examples::

    export CONDUCTOR_AGENT_LLM_MODEL=anthropic/claude-sonnet-4-6
    export CONDUCTOR_AGENT_LLM_MODEL=google_gemini/gemini-2.0-flash

If unset, defaults to ``openai/gpt-4o``.

``CONDUCTOR_AGENT_SECONDARY_LLM_MODEL`` provides a second model for multi-model examples
(e.g., cheap triage vs capable specialist). Defaults to ``openai/gpt-4o``.
"""

import os
from dataclasses import dataclass


@dataclass
class Settings:
    llm_model: str = ""
    webhook_id: str = "r8ai5a8a9d05-a8c0-11f1-b02f-6295aa77ab9a"
    webhook_endpoint_url: str = f"https://developer.orkescloud.com/webhook/{webhook_id}"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            llm_model=(
                os.environ.get("CONDUCTOR_AGENT_LLM_MODEL") or "openai/gpt-5-nano"
            ),
            webhook_id=cls.webhook_id,
            webhook_endpoint_url=cls.webhook_endpoint_url,
        )


settings = Settings.from_env()
