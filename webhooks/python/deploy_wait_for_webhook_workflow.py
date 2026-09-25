#!/usr/bin/env python3
"""Register and start a durable webhook-driven workflow.

The program keeps its local workers running until the workflow reaches the
WAIT_FOR_WEBHOOK task, stores the completed email results, then exits. Conductor
keeps the workflow suspended until ``send_webhook_payload.py`` sends a callback;
``serve_webhook_agent.py`` runs the local tools needed after it resumes.
"""

import time

from conductor.client.automator.task_handler import TaskHandler
from conductor.client.configuration.configuration import Configuration
from conductor.client.http.models import StartWorkflowRequest
from conductor.client.orkes_clients import OrkesClients
from conductor.client.workflow.conductor_workflow import ConductorWorkflow
from conductor.client.workflow.task.timeout_policy import TimeoutPolicy
from conductor.client.workflow.task.wait_for_webhook_task import wait_for_webhook
from conductor.ai.agents import AgentRuntime

from settings import settings

from utils.agent_task import AgentTask
from utils.webhook_agent import webhook_agent
from utils.workers import get_user_email, send_email

WORKFLOW_NAME = f"wait_for_webhook_demo_{settings.language}"
WORKFLOW_VERSION = 1
WAIT_TASK_REF = "wait_for_webhook_ref"

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
    # Mark the execution TIMED_OUT if it runs longer than WORKFLOW_TIMEOUT_SECONDS,
    # for example because no webhook arrives. ALERT_ONLY would let it keep running.
    workflow.timeout_seconds(WORKFLOW_TIMEOUT_SECONDS)
    workflow.timeout_policy(TimeoutPolicy.TIME_OUT_WORKFLOW)

    # Exercise 2: Replace this with one get_user_emails task that resolves every address
    # in workflow.input("user_ids"), so the number of emails is decided at runtime. Pass
    # it the subject and body as well, for the forked send_email tasks.
    get_email_task = get_user_email(
        task_ref_name="get_user_email_ref",
        user_id=workflow.input("user_id"),
    )

    # Exercise 2: Send the emails with a DynamicForkTask, using input_parameter to set
    # its tasks_param and tasks_input_param_name inputs to get_user_emails's outputs.
    # Pass it a JoinTask with an empty join_on as join_task, to wait for every branch.
    send_email_task = send_email(
        task_ref_name="send_email_ref",
        recipients=get_email_task.output("result"),
        subject=f"Hello from {CODELAB_LANGUAGE}",
        body=f"Sent by the {CODELAB_LANGUAGE} version of the webhooks codelab.",
    )

    webhook_wait = wait_for_webhook(
        task_ref_name=WAIT_TASK_REF,
        matches={
            # Every language version shares one webhook, so only match payloads
            # sent by this language's send_webhook_payload.py.
            "$['language']": settings.language,
            "$['type']": "customer",
            # Exercise 2: Change to 'user_ids'. Be sure the payload sent by
            # send_webhook_payload.py matches the key you use here.
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
            # Exercise 1: Return this execution, with its tasks, so the caller can
            # read every completed send_email output.
            return None

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

        _ = wait_until_webhook_ready(workflow_client, workflow_id)
        # Exercise 1: Store a database row for each completed send_email task's
        # output_data. Match tasks on task_def_name, not reference_task_name, which
        # Exercise 2 makes unique per email.
        print(f"{WAIT_TASK_REF} is ready")
        print(
            "Before sending the webhook, start the agent tool workers with "
            "`python serve_webhook_agent.py`, or restart them if you've changed "
            "the code since they started."
        )
        print(f"Webhook URL: {settings.webhook_endpoint_url}")
    finally:
        task_handler.stop_processes()


if __name__ == "__main__":
    main()
