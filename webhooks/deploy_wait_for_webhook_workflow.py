#!/usr/bin/env python3
"""Register and start a durable webhook-driven workflow.

The program keeps its local workers running until the workflow reaches the
WAIT_FOR_WEBHOOK task, then exits. Conductor keeps the workflow running and
resumes it after a callback is sent by ``send_webhook_payload.py``.
"""

import sqlite3
import time
from pathlib import Path
from typing import Any

from conductor.client.automator.task_handler import TaskHandler
from conductor.client.configuration.configuration import Configuration
from conductor.client.http.models import StartWorkflowRequest, Workflow
from conductor.client.orkes_clients import OrkesClients
from conductor.client.workflow.conductor_workflow import ConductorWorkflow
from conductor.client.workflow.task.timeout_policy import TimeoutPolicy
from conductor.client.workflow.task.wait_for_webhook_task import wait_for_webhook
from conductor.ai.agents import AgentRuntime

from settings import settings

from .utils.agent_task import AgentTask
from .utils.webhook_agent import webhook_agent
from .utils.workers import get_user_email, send_email

WORKFLOW_NAME = "wait_for_webhook_demo"
WORKFLOW_VERSION = 1
SEND_EMAIL_TASK_NAME = "send_email"
SEND_EMAIL_TASK_REF = "send_email_ref"
WAIT_TASK_REF = "wait_for_webhook_ref"

DATABASE_PATH = Path(__file__).resolve().parent / "utils" / "webhook_codelab_storage.db"
EMAIL_OUTPUT_FIELDS = ("sent_time", "subject", "recipients")

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

    # Exercise 2: Iterate over all user_ids in settings.user_ids and get their email addresses.
    get_email_task = get_user_email(
        task_ref_name="get_user_email_ref",
        user_id=workflow.input("user_id"),
    )

    # Exercise 2: Use a DYNAMIC_FORK to send an email to each recipient.
    # Be sure to create a JoinTask to consolidate results after your DynamicForkTask.
    # Also ensure that your task_ref_name values are unique for each sent email, for example by
    # appending the user_id to the task_ref_name.
    send_email_task = send_email(
        task_ref_name=SEND_EMAIL_TASK_REF,
        recipients=get_email_task.output("result"),
        subject="Hello from Alex",
        body="foo bar qua",
    )

    webhook_wait = wait_for_webhook(
        task_ref_name=WAIT_TASK_REF,
        matches={
            "$['type']": "customer",
            # Exercise 2: Change to 'user_ids'
            # Be sure the payload sent by send_webhook_payload.py matches the key you use here.
            "$['user_id']": workflow.input("user_id"),
        },
    )

    agent_task = AgentTask(
        task_ref_name="process_webhook_ref",
        agent_name=webhook_agent.name,
        prompt=webhook_wait.output("agent_input"),
    )

    workflow >> get_email_task >> send_email_task >> webhook_wait >> agent_task
    workflow.output_parameter("agent_response", agent_task.output("text"))

    return workflow


def start_workflow(workflow_client) -> str:
    """Start one workflow execution and return its execution ID."""
    request = StartWorkflowRequest(input={"user_id": settings.user_id})
    request.name = WORKFLOW_NAME
    request.version = WORKFLOW_VERSION

    return workflow_client.start_workflow(start_workflow_request=request)


def wait_until_webhook_ready(workflow_client, workflow_id: str) -> Workflow:
    """Return the execution after it reaches its WAIT_FOR_WEBHOOK task."""
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
            return execution

        if execution.status in {"FAILED", "TIMED_OUT", "TERMINATED"}:
            raise RuntimeError(f"Workflow entered terminal status {execution.status}")

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(
        f"Workflow did not reach {WAIT_TASK_REF} within "
        f"{READINESS_TIMEOUT_SECONDS} seconds"
    )


def get_completed_email_outputs(
    execution: Workflow,
) -> list[dict[str, Any]]:
    """Return valid outputs from every completed send-email task."""
    email_tasks = [
        task
        for task in execution.tasks or []
        if task.task_def_name == SEND_EMAIL_TASK_NAME and task.status == "COMPLETED"
    ]
    if not email_tasks:
        raise RuntimeError(
            f"No completed {SEND_EMAIL_TASK_NAME} task outputs were found"
        )

    email_outputs = []
    for task in email_tasks:
        output = task.output_data
        if not isinstance(output, dict):
            raise RuntimeError(
                f"Completed task {task.reference_task_name} has invalid output"
            )

        missing_fields = set(EMAIL_OUTPUT_FIELDS) - output.keys()
        if missing_fields:
            fields = ", ".join(sorted(missing_fields))
            raise RuntimeError(
                f"Completed task {task.reference_task_name} is missing: {fields}"
            )

        email_outputs.append(output)

    return email_outputs


def store_email_outputs(email_outputs: list[dict[str, Any]]) -> int:
    """Insert all completed email outputs in one database transaction."""
    if not email_outputs:
        raise ValueError("At least one email output is required")

    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(
            f"Database not found at {DATABASE_PATH}. "
            "Run webhooks/utils/create_sqlite_db.py first."
        )

    email_rows = [
        tuple(email_output[field] for field in EMAIL_OUTPUT_FIELDS)
        for email_output in email_outputs
    ]

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.executemany(
            """
            INSERT INTO emails (
                sent_time,
                subject,
                recipients
            )
            VALUES (?, ?, ?)
            """,
            email_rows,
        )

    return len(email_rows)


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
        # Deploy agent definition
        with AgentRuntime(configuration=config) as runtime:
            runtime.deploy(webhook_agent)
        workflow = build_workflow(clients.get_workflow_executor())
        workflow.register(overwrite=True)
        print(f"Registered workflow {WORKFLOW_NAME}, version {WORKFLOW_VERSION}")

        workflow_client = clients.get_workflow_client()
        workflow_id = start_workflow(workflow_client)

        workflow_url = f"{config.ui_host.rstrip('/')}/execution/{workflow_id}"
        print(f"Workflow URL: {workflow_url}")

        execution = wait_until_webhook_ready(workflow_client, workflow_id)
        email_outputs = get_completed_email_outputs(execution)
        stored_count = store_email_outputs(email_outputs)
        print(f"Stored {stored_count} email record(s) in {DATABASE_PATH}")
    finally:
        task_handler.stop_processes()


if __name__ == "__main__":
    main()
