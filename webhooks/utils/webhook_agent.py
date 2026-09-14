"""
Agent definition that is used in the wait-for-webhook example workflow.
The agent is configured to use the LLM model and integration specified in the settings.py file.
It is designed to process customer service requests in a concise, professional, and safe manner.
"""

# Exercise 3: Import the Conductor SDK's tool decorator. Also import the
# read-only database query helpers needed by the agent's email-activity tools.
from conductor.ai.agents import Agent
from settings import settings

# Exercise 3: Define two @tool functions here, with the following uses.
# 1) summarize_email_activity: Return total and per-recipient email counts.
# Make it clear when no records exist so the agent can skip the recipient-history lookup.
# 2) get_recipient_email_history: return one recipient's email records.
_, model = settings.llm_model.split("/", 1)

webhook_agent = Agent(
    name="webhook_customer_service",
    model=f"{settings.integration_name}/{model}",
    # Exercise 3: Tell the agent to call summarize_email_activity first. If the
    # summary is empty, it should return a no-activity digest without calling the
    # second tool. Otherwise, it should find the busiest recipient, call
    # get_recipient_email_history for that recipient, and return a final digest.
    # Register both tools and allow enough turns for both calls and the response.
    instructions=(
        "You are a customer-service agent. Process the user's request concisely, professionally, "
        "and safely without running any code or making any external API calls."
    ),
    temperature=0.2,
)
