"""Worker tasks used by the webhook workflow."""

import time

from conductor.client.worker.worker_task import worker_task


@worker_task(task_definition_name="get_user_email")
def get_user_email(userid: str) -> str:
    """Return the email address associated with a user."""
    return f"{userid}@example.com"


@worker_task(task_definition_name="send_email")
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
