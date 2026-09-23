"""Worker tasks used by the webhook workflow."""

from conductor.client.worker.worker_task import worker_task


@worker_task(task_definition_name="get_user_email")
# Exercise 2: Change to "get_user_emails" and take a list of user_ids as input.
def get_user_email(user_id: str) -> str:
    """Return the email address associated with a user."""
    return f"{user_id}@example.com"


@worker_task(task_definition_name="send_email")
def send_email(
    recipients: str,
    subject: str,
    body: str,
) -> None:
    """Simulate sending an email."""
    print(
        f"Sending email\n" f"To: {recipients}\n" f"Subject: {subject}\n" f"Body: {body}"
    )
    # Exercise 1: Return one record from each invocation with the fields required
    # by the emails table, allowing every completed send_email output to be stored.
    return None
