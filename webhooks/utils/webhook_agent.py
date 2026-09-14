"""Email activity agent and its read-only database tools."""

from typing import Any

from conductor.ai.agents import Agent, tool
from settings import settings

from .query_sqlite_db import fetch_email_activity, fetch_emails


@tool
def summarize_email_activity() -> dict[str, Any]:
    """Return total email activity and per-recipient counts; call this first."""
    # SQLite has already grouped and sorted these rows, so calculating the total
    # does not require loading every stored email into the agent worker.
    recipient_activity = [dict(row) for row in fetch_email_activity()]

    return {
        "total_emails": sum(row["email_count"] for row in recipient_activity),
        # The agent uses this flag to avoid requesting a nonexistent recipient.
        "has_activity": bool(recipient_activity),
        "recipient_activity": recipient_activity,
    }


@tool
def get_recipient_email_history(recipient: str) -> dict[str, Any]:
    """Return stored emails for a recipient selected from the activity summary."""
    recipient = recipient.strip()
    if not recipient:
        raise ValueError("A recipient email address is required")

    emails = [dict(email) for email in fetch_emails(recipient=recipient)]
    return {
        "recipient": recipient,
        "email_count": len(emails),
        "emails": emails,
    }


from .query_sqlite_db import fetch_email_activity, fetch_emails


@tool
def summarize_email_activity() -> dict[str, Any]:
    """Return total email activity and per-recipient counts; call this first."""
    # SQLite has already grouped and sorted these rows, so calculating the total
    # does not require loading every stored email into the agent worker.
    recipient_activity = [dict(row) for row in fetch_email_activity()]

    return {
        "total_emails": sum(row["email_count"] for row in recipient_activity),
        # The agent uses this flag to avoid requesting a nonexistent recipient.
        "has_activity": bool(recipient_activity),
        "recipient_activity": recipient_activity,
    }


@tool
def get_recipient_email_history(recipient: str) -> dict[str, Any]:
    """Return stored emails for a recipient selected from the activity summary."""
    recipient = recipient.strip()
    if not recipient:
        raise ValueError("A recipient email address is required")

    emails = [dict(email) for email in fetch_emails(recipient=recipient)]
    return {
        "recipient": recipient,
        "email_count": len(emails),
        "emails": emails,
    }


# Exercise 3: Define two @tool functions here, with the following uses.
# 1) summarize_email_activity: Return total and per-recipient email counts.
# Make it clear when no records exist so the agent can skip the recipient-history lookup.
# 2) get_recipient_email_history: return one recipient's email records.
_, model = settings.llm_model.split("/", 1)

webhook_agent = Agent(
    name="webhook_customer_service",
    model=f"{settings.integration_name}/{model}",
    # Exercise 3: Tell the agent to call summarize_email_activity first.
    # If the summary is empty, it should return a no-activity digest.
    # Otherwise, it should find the busiest recipient, call
    # get_recipient_email_history for that recipient, and return a final digest.
    # Register both tools and allow enough turns for both calls and the response.
    instructions=(
        "You are an email activity analyst. First call summarize_email_activity. "
        "If has_activity is false, do not call get_recipient_email_history; return "
        "a concise digest stating that there is no stored email activity. Otherwise, "
        "identify the recipient with the greatest email_count, breaking ties by "
        "choosing the alphabetically first recipient. Then call "
        "get_recipient_email_history with that exact recipient. Base every factual "
        "claim on the tool results and return a concise, multi-line activity digest."
    ),
    tools=[summarize_email_activity, get_recipient_email_history],
    max_turns=5,
    temperature=0.2,
)
