"""
Agent definition that is used in the wait-for-webhook example workflow.
The agent is configured to use the LLM model and integration specified in the settings.py file.
It is designed to process customer service requests in a concise, professional, and safe manner.
"""

from conductor.ai.agents import Agent
from settings import settings

_, model = settings.llm_model.split("/", 1)

webhook_agent = Agent(
    name="webhook_customer_service",
    model=f"{settings.integration_name}/{model}",
    instructions=(
        "You are a customer-service agent. Process the user's request concisely, professionally, "
        "and safely without running any code or making any external API calls."
    ),
    temperature=0.2,
)
