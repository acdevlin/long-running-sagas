#!/usr/bin/env python3
"""Serve the local database tools used by the post-webhook agent."""

from conductor.ai.agents import AgentRuntime
from conductor.client.configuration.configuration import Configuration

from .utils.webhook_agent import webhook_agent


def main() -> None:
    """Deploy the agent and serve its tool workers until interrupted."""
    with AgentRuntime(configuration=Configuration()) as runtime:
        runtime.serve(webhook_agent)


if __name__ == "__main__":
    main()
