"""
Agent definition that is used in the wait-for-webhook example workflow.
The agent is configured to use the LLM model and integration specified in the settings.py file.
It is designed to process customer service requests in a concise, professional, and safe manner.
"""

# Exercise 3: Import the Conductor SDK's tool decorator. Also import the
# read-only database query helpers needed by the agent's email-activity tools.
from conductor.ai.agents import Agent
from settings import settings

# Exercise 3: Define two @tool functions here: summarize_email_activity (total and
# per-recipient counts, making an empty database clear) and
# get_recipient_email_history (one recipient's email records).
# Exercise 3: Each function's docstring becomes its tool description, which the LLM
# reads to decide when and how to call it, so describe any parameters there too.
# Exercise 3: Convert the sqlite3.Row results from the query helpers to plain
# dictionaries before returning them from either tool.

if "/" not in settings.llm_model:
    raise ValueError(
        "settings.llm_model must use the 'provider/model' format, for example "
        f"'openai/gpt-5-nano'; got {settings.llm_model!r}."
    )
_, model = settings.llm_model.split("/", 1)

webhook_agent = Agent(
    name=f"webhook_customer_service_{settings.language}",
    model=f"{settings.integration_name}/{model}",
    # Exercise 3: Tell the agent to call summarize_email_activity first, and return a
    # no-activity digest if it is empty. Otherwise it should call
    # get_recipient_email_history for the busiest recipient, then return a final digest.
    instructions=(
        "You are a customer-service agent. Process the user's request concisely, professionally, "
        "and safely without running any code or making any external API calls."
    ),
    # Exercise 3: Register both tools with tools=[...], and set max_turns high enough
    # for both tool calls and the final response.
    temperature=0.2,
)
