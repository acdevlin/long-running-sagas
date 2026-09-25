"""Worker tasks used by the webhook workflow."""

from conductor.client.worker.worker_task import worker_task


@worker_task(task_definition_name="get_user_email")
# Exercise 2: Change to "get_user_emails", taking a list of user_ids. Return the fork's
# send_email tasks, each of type "SIMPLE" with a unique taskReferenceName (Exercise 3
# repeats a user_id), and a dict mapping each taskReferenceName to that task's input.
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
    # Exercise 1: Return this email's fields for the emails table, with sent_time as a
    # Unix timestamp in seconds.
    return None
