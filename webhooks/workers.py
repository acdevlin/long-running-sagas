"""Worker tasks used by the webhook workflow."""

from conductor.client.worker.worker_task import worker_task


@worker_task(task_definition_name="get_user_email")
def get_user_email(userid: str) -> str:
    """Return the email address associated with a user."""
    return f"{userid}@example.com"


@worker_task(task_definition_name="send_email")
def send_email(
    email: str,
    subject: str,
    body: str,
) -> None:
    """Simulate sending an email."""
    print(f"Sending email\n" f"To: {email}\n" f"Subject: {subject}\n" f"Body: {body}")
