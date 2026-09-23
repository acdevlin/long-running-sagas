"""Worker tasks used by the webhook workflow."""

import time
from typing import Any

from conductor.client.worker.worker_task import worker_task

# These shared keys keep the worker's output synchronized with the parameters
# that DynamicForkTask reads in the workflow definition.
DYNAMIC_TASKS_PARAM = "dynamicTasks"
DYNAMIC_TASKS_INPUTS_PARAM = "dynamicTasksInputs"
SEND_EMAIL_TASK_NAME = "send_email"


@worker_task(task_definition_name="get_user_emails")
def get_user_emails(
    user_ids: list[str],
    subject: str,
    body: str,
) -> dict[str, Any]:
    """Resolve user emails and prepare one dynamic send task per address."""
    if not user_ids:
        raise ValueError("At least one user ID is required")

    dynamic_tasks = []
    dynamic_task_inputs = {}

    for index, user_id in enumerate(user_ids):
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError(f"Invalid user ID at index {index}")

        # The index keeps references unique even when user_ids contains duplicates.
        task_ref_name = f"send_email_{index}"
        dynamic_tasks.append(
            {
                "name": SEND_EMAIL_TASK_NAME,
                "taskReferenceName": task_ref_name,
                "type": "SIMPLE",
                "inputParameters": {},
            }
        )
        dynamic_task_inputs[task_ref_name] = {
            "recipients": f"{user_id}@example.com",
            "subject": subject,
            "body": body,
        }

    return {
        DYNAMIC_TASKS_PARAM: dynamic_tasks,
        DYNAMIC_TASKS_INPUTS_PARAM: dynamic_task_inputs,
    }


# Conductor schedules forked tasks in parallel; additional worker threads allow
# this local process to execute more than one send at a time.
@worker_task(task_definition_name=SEND_EMAIL_TASK_NAME, thread_count=10)
def send_email(
    recipients: str,
    subject: str,
    body: str,
) -> dict[str, int | str]:
    """Simulate sending an email."""
    print(
        f"Sending email\n" f"To: {recipients}\n" f"Subject: {subject}\n" f"Body: {body}"
    )
    return {
        "sent_time": int(time.time()),
        "subject": subject,
        "recipients": recipients,
    }
