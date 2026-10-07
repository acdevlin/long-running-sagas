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

| Step                | Command                                      |
| ------------------- | -------------------------------------------- |
| **create-db**       | `python -m utils.create_sqlite_db`           |
| **deploy-workflow** | `python deploy_wait_for_webhook_workflow.py` |
| **serve-agent**     | `python serve_webhook_agent.py`              |
| **send-webhook**    | `python send_webhook_payload.py`             |
| **query-db**        | `python -m utils.query_sqlite_db`            |

The **deploy-workflow** step registers the workflow as
`wait_for_webhook_demo_python` and the agent as
`webhook_customer_service_python`. Select `wait_for_webhook_demo_python` when
you set up your webhook.

## Where to Find Each Part

Comments beginning with `# Exercise N:` mark each place you will change for that
exercise.

| Codelab part                                                         | File                                  | Exercises |
| -------------------------------------------------------------------- | ------------------------------------- | --------- |
| Recipient user IDs                                                   | `settings.py`                         | 2, 3      |
| Workflow definition, readiness check, and storing email records      | `deploy_wait_for_webhook_workflow.py` | 1, 2      |
| `get_user_email` and `send_email` workers                            | `utils/workers.py`                    | 1, 2      |
| Webhook payload and `agent_input`                                    | `send_webhook_payload.py`             | 2, 3      |
| `webhook_customer_service_python` agent and its tools                | `utils/webhook_agent.py`              | 3         |
| Read-only database queries                                           | `utils/query_sqlite_db.py`            | 3         |
| Database setup, using [`../shared/schema.sql`](../shared/schema.sql) | `utils/create_sqlite_db.py`           |           |
| Local database file, created by **create-db**                        | `utils/webhook_codelab_storage.db`    |           |
| Helper for the `AGENT` task                                          | `utils/agent_task.py`                 |           |

## Python Notes

- **Exercise 1:** Python's built-in
  [`sqlite3` module](https://docs.python.org/3/library/sqlite3.html) is all you
  need to write to the database, and `DATABASE_PATH` in
  `utils/query_sqlite_db.py` gives the location of the database file. A worker
  function's return value becomes the task's output: the SDK sends a dict as it
  is, and stores any other value under a `result` key.
- **Exercise 2:** The Python SDK provides the `DYNAMIC_FORK` and `JOIN` tasks as
  `DynamicForkTask` and `JoinTask`. Pass the `JoinTask` to the fork as its
  `join_task`, rather than adding it to the workflow yourself, and connect the
  fork's inputs to the `get_user_emails` output with its `input_parameter`
  method. A worker runs one task at a time unless you raise its `thread_count`,
  for example `@worker_task(task_definition_name="send_email", thread_count=10)`.
- **Exercise 3:** Declare each agent tool with the `@tool` decorator from
  `conductor.ai.agents`. The function's docstring becomes the tool's
  description, which the LLM reads to decide when and how to call it, so
  describe the tool's parameters there too. The agent receives each tool's
  result as JSON. A returned dict becomes that JSON as it is, so turn each
  `sqlite3.Row` from the query helpers into a plain dict first.

## SDK Notes

This version uses version 2.0.0 of the Conductor Python SDK
(`conductor-python`), which includes the agent SDK as `conductor.ai.agents`. A
few of its behaviors shape the code, so leave these parts as they are:

- **Agent tasks:** The SDK's `TaskType` has no `AGENT` member, so
  `utils/agent_task.py` creates the task with a placeholder type, then sets its
  type to `AGENT` in the definition sent to the server.
- **Connection settings:** The SDK reads `CONDUCTOR_SERVER_URL`,
  `CONDUCTOR_AUTH_KEY` and `CONDUCTOR_AUTH_SECRET` from the environment.
  `settings.py` adds the values from `.env` to the environment as soon as it is
  imported, before any step creates a `Configuration`.
