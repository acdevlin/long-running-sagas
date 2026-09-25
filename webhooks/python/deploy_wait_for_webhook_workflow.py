#!/usr/bin/env python3
"""Register and start a durable webhook-driven workflow.

The program keeps its local workers running until the workflow reaches the
WAIT_FOR_WEBHOOK task, stores the completed email results, then exits. Conductor
keeps the workflow suspended until ``send_webhook_payload.py`` sends a callback;
``serve_webhook_agent.py`` runs the local tools needed after it resumes.
"""

import sqlite3
import sys
import time
from typing import Any

from conductor.client.automator.task_handler import TaskHandler
from conductor.client.configuration.configuration import Configuration
from conductor.client.http.models import StartWorkflowRequest, Workflow
from conductor.client.orkes_clients import OrkesClients
from conductor.client.workflow.conductor_workflow import ConductorWorkflow
from conductor.client.workflow.task.dynamic_fork_task import DynamicForkTask
from conductor.client.workflow.task.join_task import JoinTask
from conductor.client.workflow.task.timeout_policy import TimeoutPolicy
from conductor.client.workflow.task.wait_for_webhook_task import wait_for_webhook
from conductor.ai.agents import AgentRuntime

from settings import settings

from utils.agent_task import AgentTask
from utils.query_sqlite_db import DATABASE_PATH, open_database
from utils.webhook_agent import webhook_agent
from utils.workers import (
    DYNAMIC_TASKS_INPUTS_PARAM,
    DYNAMIC_TASKS_PARAM,
    SEND_EMAIL_TASK_NAME,
    get_user_emails,
)

WORKFLOW_NAME = f"wait_for_webhook_demo_{settings.language}"
WORKFLOW_VERSION = 1
WAIT_TASK_REF = "wait_for_webhook_ref"

# The type each send_email output field must have to fit the emails table.
EMAIL_OUTPUT_FIELDS = {"sent_time": int, "subject": str, "recipients": str}

WORKFLOW_TIMEOUT_SECONDS = 7 * 24 * 60 * 60
READINESS_TIMEOUT_SECONDS = 60
POLL_INTERVAL_SECONDS = 1

# Shown in the workflow's description in the Orkes Conductor UI, and in every
# email this version sends, so you can tell the language versions apart.
CODELAB_LANGUAGE = "Python"


def build_workflow(workflow_executor) -> ConductorWorkflow:
    """Build the workflow definition without registering or starting it."""
    workflow = ConductorWorkflow(
        name=WORKFLOW_NAME,
        version=WORKFLOW_VERSION,
        executor=workflow_executor,
    )
    workflow.description = (
        f"Durable wait-for-webhook example (registered from {CODELAB_LANGUAGE})"
    )
    workflow.timeout_seconds(WORKFLOW_TIMEOUT_SECONDS)
    workflow.timeout_policy(TimeoutPolicy.TIME_OUT_WORKFLOW)
    workflow.input_parameters(["user_ids"])

    # Resolve every recipient's address in a single worker task, which also
    # prepares one send_email task per address for the fork below.
    get_emails_task = get_user_emails(
        task_ref_name="get_user_emails_ref",
        user_ids=workflow.input("user_ids"),
        subject=f"Hello from {CODELAB_LANGUAGE}",
        body=f"Sent by the {CODELAB_LANGUAGE} version of the webhooks codelab.",
    )

    # Dynamic branch references are unknown until runtime, so we use an empty join_on
    # to tell the Join to wait for all branches created by its Dynamic Fork.
    send_emails_join = JoinTask(
        task_ref_name="send_emails_join",
        join_on=[],
    )
    send_emails_fork = DynamicForkTask(
        task_ref_name="send_emails_fork",
        tasks_param=DYNAMIC_TASKS_PARAM,
        tasks_input_param_name=DYNAMIC_TASKS_INPUTS_PARAM,
        join_task=send_emails_join,
    )
    # The SDK emits the supplied Join immediately after the Dynamic Fork. These
    # inputs connect the lookup worker's generated definitions and branch data.
    send_emails_fork.input_parameter(
        DYNAMIC_TASKS_PARAM,
        get_emails_task.output(DYNAMIC_TASKS_PARAM),
    )
    send_emails_fork.input_parameter(
        DYNAMIC_TASKS_INPUTS_PARAM,
        get_emails_task.output(DYNAMIC_TASKS_INPUTS_PARAM),
    )

    webhook_wait = wait_for_webhook(
        task_ref_name=WAIT_TASK_REF,
        matches={
            # Every language version shares one webhook, so only match payloads
            # sent by this language's send_webhook_payload.py.
            "$['language']": settings.language,
            "$['type']": "customer",
            # Only resume for a webhook about the recipients this execution
            # emailed. send_webhook_payload.py sends the same user_ids list.
            "$['user_ids']": workflow.input("user_ids"),
        },
    )

    agent_task = AgentTask(
        task_ref_name="process_webhook_ref",
        agent_name=webhook_agent.name,
        prompt=webhook_wait.output("agent_input"),
    )

    workflow >> get_emails_task >> send_emails_fork >> webhook_wait >> agent_task
    workflow.output_parameter("agent_response", agent_task.output("text"))

    return workflow


def start_workflow(workflow_client) -> str:
    """Start one workflow execution and return its execution ID."""
    # Convert the immutable user_ids list into the JSON array expected by Conductor.
    request = StartWorkflowRequest(input={"user_ids": list(settings.user_ids)})
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
    """Return valid outputs from every completed send_email task."""
    # Task-definition names remain stable while Dynamic Fork references do not.
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

        # An exact type check, so that a missing (None) or bool value is rejected.
        invalid_fields = [
            field
            for field, field_type in EMAIL_OUTPUT_FIELDS.items()
            if type(output.get(field)) is not field_type
        ]
        if invalid_fields:
            fields = ", ".join(invalid_fields)
            raise RuntimeError(
                f"Completed task {task.reference_task_name} has missing or invalid "
                f"fields: {fields}"
            )

        email_outputs.append(output)

    return email_outputs


def store_email_outputs(email_outputs: list[dict[str, Any]]) -> int:
    """Insert all completed email outputs in one database transaction."""
    email_rows = [
        tuple(email_output[field] for field in EMAIL_OUTPUT_FIELDS)
        for email_output in email_outputs
    ]

    with open_database(writable=True) as connection:
        # Use a single DB transaction to avoid partial insert failures.
        with connection:
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


def main() -> int:
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
        print(f"{WAIT_TASK_REF} is ready")
        print(
            "Before sending the webhook, start the agent tool workers with "
            "`python serve_webhook_agent.py`."
        )
        print(f"Webhook URL: {settings.webhook_endpoint_url}")
    except (FileNotFoundError, RuntimeError, TimeoutError, sqlite3.Error) as error:
        # Report expected failures in one line, as the query-db step does.
        print(f"Deploy step failed: {error}", file=sys.stderr)
        return 1
    finally:
        task_handler.stop_processes()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
