#!/usr/bin/env python3
"""
Deploys a workflow with a WAIT_FOR_WEBHOOK task as part of a durable runtime.

After deployment, this script will exit. The workflow will continue waiting for the webhook to be
received from within the Orkes Cloud UI.

Expects a payload request similar to the following:
curl -i -X POST \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  -H 'source: {your_source_header_here}' \
  'https://developer.orkescloud.com/webhook/{your_webhook_id_here}' \
  -d '{"id":"{your_user_id_here}","type":"customer","agent_input":"Say hello!"}'

"""

import time

from conductor.client.automator.task_handler import TaskHandler
from conductor.client.configuration.configuration import Configuration
from conductor.client.http.models import StartWorkflowRequest
from conductor.client.orkes_clients import OrkesClients
from conductor.client.worker.worker_task import worker_task
from conductor.client.workflow.conductor_workflow import ConductorWorkflow
from conductor.client.workflow.task.timeout_policy import TimeoutPolicy
from conductor.client.workflow.task.wait_for_webhook_task import wait_for_webhook
from conductor.client.workflow.task.llm_tasks.llm_chat_complete import (
    ChatMessage,
    LlmChatComplete,
)

from settings import settings

WORKFLOW_NAME = "wait_for_webhook_demo"
WORKFLOW_VERSION = 1
WAIT_TASK_REF = "wait_for_webhook_ref"
TIMEOUT_SECONDS = 60


@worker_task(task_definition_name="get_user_email")
def get_user_email(userid: str) -> str:
    return f"{userid}@example.com"


@worker_task(task_definition_name="send_email")
def send_email(email: str, subject: str, body: str):
    print(
        f"sending email to: {email}\n",
        f"with subject: {subject}\n",
        f"and body: {body}\n",
    )


def main():
    api_config = Configuration()

    task_handler = TaskHandler(
        workers=[],
        configuration=api_config,
        scan_for_annotated_workers=True,
    )
    task_handler.start_processes()

    # Use a try/finally to ensure that workers are stopped even if an error occurs.
    try:
        clients = OrkesClients(configuration=api_config)
        workflow_executor = clients.get_workflow_executor()

        workflow = ConductorWorkflow(
            name=WORKFLOW_NAME,
            version=WORKFLOW_VERSION,
            executor=workflow_executor,
        )

        workflow.description = "Durable wait-for-webhook example"

        # Seven-day server-side workflow timeout.
        workflow.timeout_seconds(7 * 24 * 60 * 60)
        workflow.timeout_policy(TimeoutPolicy.TIME_OUT_WORKFLOW)

        get_email = get_user_email(
            task_ref_name="get_user_email_ref",
            userid=workflow.input("userid"),
        )

        # These email tasks will execute immediately, then the workflow will then pause at the
        # wait_for_webhook task until the webhook is received.
        sendmail = send_email(
            task_ref_name="send_email_ref",
            email=get_email.output("result"),
            subject="Hello from Orkes",
            body="Test Email",
        )

        # The workflow will pause at this task until the webhook is received.
        webhook_wait = wait_for_webhook(
            task_ref_name=WAIT_TASK_REF,
            # Provide stable correlation matches for the webhook payload.
            matches={
                "$['type']": "customer",
                "$['id']": workflow.input("userid"),
            },
        )

        # The webhook payload will be passed to the LLM task for processing.
        llm_provider, model = settings.llm_model.split("/", 1)
        agent_task = LlmChatComplete(
            task_ref_name="process_webhook_ref",
            llm_provider=settings.integration_name,
            model=model,
            messages=[
                ChatMessage(
                    role="system",
                    message=(
                        "You are a customer-service agent. "
                        "Process the user's request concisely, professionally, and safely."
                    ),
                ),
                ChatMessage(
                    role="user",
                    message=webhook_wait.output("agent_input"),
                ),
            ],
            temperature=0.2,
        )

        # Defines sequential workflow.
        workflow >> get_email >> sendmail >> webhook_wait >> agent_task

        # Display agent's response in final workflow output.
        workflow.output_parameter(
            "agent_response",
            agent_task.output("result"),
        )

        # Update workflow in the specified Orkes server.
        workflow.register(overwrite=True)
        print(f"Registered workflow {WORKFLOW_NAME}, version {WORKFLOW_VERSION}")

        request = StartWorkflowRequest(input={"userid": f"{settings.user_id}"})
        request.name = WORKFLOW_NAME
        request.version = WORKFLOW_VERSION

        # Asynchronous start: immediately returns the durable execution ID.
        workflow_client = clients.get_workflow_client()
        workflow_id = workflow_client.start_workflow(start_workflow_request=request)

        print(
            "Workflow started at the following URL:\n"
            f"{api_config.ui_host.rstrip('/')}/execution/{workflow_id}"
        )

        # Keep local workers alive until the server-side WAIT_FOR_WEBHOOK task becomes active,
        # using a timeout to avoid waiting forever in case something does goes wrong.
        deadline = time.monotonic() + TIMEOUT_SECONDS

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

            # Confirm that the workflow has reached the WAIT_FOR_WEBHOOK task and is waiting.
            if wait_task and wait_task.status == "IN_PROGRESS":
                print(f"{WAIT_TASK_REF} is IN_PROGRESS")
                print(
                    "The workflow is ready to receive webhook payloads at the following URL:\n",
                    f"{settings.webhook_endpoint_url}",
                )
                return

            # Error handling.
            if execution.status in {"FAILED", "TIMED_OUT", "TERMINATED"}:
                task_states = [
                    {
                        "reference": task.reference_task_name,
                        "status": task.status,
                        "reason": task.reason_for_incompletion,
                    }
                    for task in execution.tasks or []
                ]
                raise RuntimeError(
                    f"Workflow entered {execution.status}: {task_states}"
                )
            # Poll status every second.
            time.sleep(1)

        raise TimeoutError(
            f"Workflow did not reach {WAIT_TASK_REF} within {TIMEOUT_SECONDS} seconds"
        )

    finally:
        task_handler.stop_processes()


if __name__ == "__main__":
    main()
