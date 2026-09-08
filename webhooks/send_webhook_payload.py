#!/usr/bin/env python3

import requests
from settings import settings


def main():
    """
    Send a webhook payload to the Orkes webhook endpoint.
    """
    headers = {
        "Accept": "application/json",
        "source": "alex-local-test",
    }

    payload = {
        "id": "user_a",
        "type": "customer",
        "agent_input": (
            "Say hello and inform the user that their email has been sent."
        ),
    }

    response = requests.post(
        settings.webhook_endpoint_url,
        headers=headers,
        json=payload,
        timeout=30,
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

    # Raise an exception for HTTP errors such as 401 or 500.
    response.raise_for_status()

    print("Webhook was accepted by Orkes.")


if __name__ == "__main__":
    main()
