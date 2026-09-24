# Webhooks Codelab: Python

This folder contains the Python version of the
[webhooks codelab](../README.md). The walkthrough and exercises are in that
README; this page covers setup, the command for each step, and where to find
each part of the code.

## Setup

This version requires Python 3.13 or newer. Complete the
[Setup section of the top-level README](../../README.md#setup) first. Then, from
this folder, be sure to
[create a virtual environment](https://docs.python.org/3/library/venv.html),
activate it, then `pip install -r requirements.txt` to install important
dependencies.

`settings.py` loads your settings from the `.env` file at the top level of the
repository, so there is nothing to configure in this folder.

Then follow the [Preparation steps in the codelab README](../README.md#preparation)
to configure your Orkes account and webhook.

## Commands

Run every command from this folder (`webhooks/python`).

| Step | Command |
| --- | --- |
| **create-db** | `python -m utils.create_sqlite_db` |
| **deploy** | `python deploy_wait_for_webhook_workflow.py` |
| **serve-agent** | `python serve_webhook_agent.py` |
| **send-webhook** | `python send_webhook_payload.py` |
| **query-db** | `python -m utils.query_sqlite_db` |

The **deploy** step registers the workflow as `wait_for_webhook_demo_python`
and the agent as `webhook_customer_service_python`. Select
`wait_for_webhook_demo_python` when you set up your webhook.

## Where to Find Each Part

Comments beginning with `# Exercise N:` mark each place you will change for that
exercise.

| Codelab part | File | Exercises |
| --- | --- | --- |
| Recipient user IDs | `settings.py` | 2, 3 |
| Workflow definition, readiness check, and storing email records | `deploy_wait_for_webhook_workflow.py` | 1, 2 |
| `get_user_email` and `send_email` workers | `utils/workers.py` | 1, 2 |
| Webhook payload and `agent_input` | `send_webhook_payload.py` | 2, 3 |
| `webhook_customer_service_python` agent and its tools | `utils/webhook_agent.py` | 3 |
| Read-only database queries | `utils/query_sqlite_db.py` | 3 |
| Database setup, using [`../shared/schema.sql`](../shared/schema.sql) | `utils/create_sqlite_db.py` | |
| Local database file, created by **create-db** | `utils/webhook_codelab_storage.db` | |
| Adapter that adds an `AGENT` task to the workflow | `utils/agent_task.py` | |

## Python Notes

- **Exercise 1:** Python's built-in
  [`sqlite3` module](https://docs.python.org/3/library/sqlite3.html) is all you
  need to write to the database.
- **Exercise 2:** The Python SDK provides the `DYNAMIC_FORK` and `JOIN` tasks as
  `DynamicForkTask` and `JoinTask`.
- **Exercise 3:** Declare each agent tool with the `@tool` decorator from
  `conductor.ai.agents`.
