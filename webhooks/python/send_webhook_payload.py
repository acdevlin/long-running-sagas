#!/usr/bin/env python3
"""Send a webhook payload to the specified Orkes webhook endpoint."""

import requests
from settings import settings


def main():
    """
    Send a webhook payload to the Orkes webhook endpoint.
    """
    headers = {
        "Accept": "application/json",
        "source": settings.source_header,
    }

    payload = {
        # Exercise 2: Send user_ids instead, the same list as the workflow's input,
        # to match the WAIT_FOR_WEBHOOK task's rule in the deploy-workflow step.
        "user_id": settings.user_id,
        "type": "customer",
        # Exercise 3: Replace this prompt with a request to summarize stored email
        # activity, inspect the busiest recipient's history, and return a digest.
        "agent_input": (
            "Introduce yourself, then inform the user that their email has been sent."
        ),
        # Every language version shares one webhook; this key selects this
        # language's workflow (see the matches in the deploy-workflow step).
        "language": settings.language,
    }

    response = requests.post(
        settings.webhook_endpoint_url,
        headers=headers,
        json=payload,
        timeout=30,
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

    # Raise an exception for HTTP error responses (e.g.:4xx and 5xx).
    response.raise_for_status()

    print("Webhook was accepted by Orkes Conductor.")


if __name__ == "__main__":
    main()
