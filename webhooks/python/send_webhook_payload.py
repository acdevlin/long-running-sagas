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

    # Both the key and list contents must conform to wait_for_webhook.matches
    payload = {
        "user_ids": list(settings.user_ids),
        "type": "customer",
        "agent_input": (
            "Create an email activity digest. First summarize all stored email "
            "activity. If there is no stored activity, return a concise no-activity "
            "digest. Otherwise, inspect the history of the recipient with the "
            "greatest number of emails before returning your final analysis."
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
