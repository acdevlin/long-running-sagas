#!/usr/bin/env python3
"""Register and start a durable webhook-driven workflow.

The program keeps its local workers running until the workflow reaches the
WAIT_FOR_WEBHOOK task, then exits. Conductor keeps the workflow running and
resumes it after a callback is sent by ``send_webhook_payload.py``.
"""

import time

from conductor.client.automator.task_handler import TaskHandler
from conductor.client.configuration.configuration import Configuration
from conductor.client.http.models import StartWorkflowRequest
from conductor.client.orkes_clients import OrkesClients
from conductor.client.workflow.conductor_workflow import ConductorWorkflow
from conductor.client.workflow.task.llm_tasks.llm_chat_complete import (
    ChatMessage,
    LlmChatComplete,
)
from conductor.client.workflow.task.timeout_policy import TimeoutPolicy
from conductor.client.workflow.task.wait_for_webhook_task import wait_for_webhook

from settings import settings

from .workers import get_user_email, send_email

WORKFLOW_NAME = "wait_for_webhook_demo"
WORKFLOW_VERSION = 1
WAIT_TASK_REF = "wait_for_webhook_ref"

WORKFLOW_TIMEOUT_SECONDS = 7 * 24 * 60 * 60
READINESS_TIMEOUT_SECONDS = 60
POLL_INTERVAL_SECONDS = 1


def build_workflow(workflow_executor) -> ConductorWorkflow:
    """Build the workflow definition without registering or starting it."""
    workflow = ConductorWorkflow(
        name=WORKFLOW_NAME,
        version=WORKFLOW_VERSION,
        executor=workflow_executor,
    )
    workflow.description = "Durable wait-for-webhook example"
    workflow.timeout_seconds(WORKFLOW_TIMEOUT_SECONDS)
    workflow.timeout_policy(TimeoutPolicy.TIME_OUT_WORKFLOW)

    get_email_task = get_user_email(
        task_ref_name="get_user_email_ref",
        userid=workflow.input("userid"),
    )

    send_email_task = send_email(
        task_ref_name="send_email_ref",
        email=get_email_task.output("result"),
        subject="Hello from Orkes",
        body="Test Email",
    )

    webhook_wait = wait_for_webhook(
        task_ref_name=WAIT_TASK_REF,
        matches={
            "$['type']": "customer",
            "$['id']": workflow.input("userid"),
        },
    )

    _, model = settings.llm_model.split("/", 1)
    agent_task = LlmChatComplete(
        task_ref_name="process_webhook_ref",
        llm_provider=settings.integration_name,
        model=model,
        messages=[
            ChatMessage(
                role="system",
                message=(
                    "You are a customer-service agent. "
                    "Process the user's request concisely, professionally, "
                    "and safely."
                ),
            ),
            ChatMessage(
                role="user",
                message=webhook_wait.output("agent_input"),
            ),
        ],
        temperature=0.2,
    )

    workflow >> get_email_task >> send_email_task >> webhook_wait >> agent_task
    workflow.output_parameter("agent_response", agent_task.output("result"))

    return workflow


def start_workflow(workflow_client) -> str:
    """Start one workflow execution and return its execution ID."""
    request = StartWorkflowRequest(input={"userid": settings.user_id})
    request.name = WORKFLOW_NAME
    request.version = WORKFLOW_VERSION

    return workflow_client.start_workflow(start_workflow_request=request)


def wait_until_webhook_ready(workflow_client, workflow_id: str) -> None:
    """Wait until the execution reaches its WAIT_FOR_WEBHOOK task."""
    deadline = time.monotonic() + READINESS_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        execution = workflow_client.get_workflow(
            workflow_id,
            include_tasks=True,
        )

        wait_task = next(
            (
                task
                for task in execution.tasks or []
                if task.reference_task_name == WAIT_TASK_REF
            ),
            None,
        )

        if wait_task and wait_task.status == "IN_PROGRESS":
            print(f"{WAIT_TASK_REF} is ready")
            print(f"Webhook URL: {settings.webhook_endpoint_url}")
            return

        if execution.status in {"FAILED", "TIMED_OUT", "TERMINATED"}:
            raise RuntimeError(f"Workflow entered terminal status {execution.status}")

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(
        f"Workflow did not reach {WAIT_TASK_REF} within "
        f"{READINESS_TIMEOUT_SECONDS} seconds"
    )


def main() -> None:
    config = Configuration()
    task_handler = TaskHandler(
        workers=[],
        configuration=config,
        scan_for_annotated_workers=True,
    )
    task_handler.start_processes()

    try:
        clients = OrkesClients(configuration=config)
        workflow = build_workflow(clients.get_workflow_executor())
        workflow.register(overwrite=True)
        print(f"Registered workflow {WORKFLOW_NAME}, version {WORKFLOW_VERSION}")

        workflow_client = clients.get_workflow_client()
        workflow_id = start_workflow(workflow_client)

        workflow_url = f"{config.ui_host.rstrip('/')}/execution/{workflow_id}"
        print(f"Workflow URL: {workflow_url}")

        wait_until_webhook_ready(workflow_client, workflow_id)
    finally:
        task_handler.stop_processes()


if __name__ == "__main__":
    main()
