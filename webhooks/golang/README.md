# Webhooks Codelab: Go

This folder contains the Go version of the
[webhooks codelab](../README.md). The walkthrough and exercises are in that
README; this page covers setup, the command for each step, and where to find
each part of the code.

## Setup

This version requires [Go](https://go.dev/dl/) 1.26 or newer. Complete the
[Setup section of the top-level README](../../README.md#setup) first.

There is nothing else to install. The first command you run downloads the
modules listed in `go.mod`, checks them against `go.sum`, and compiles them,
which takes a minute or so. Later commands reuse that work.

`settings/settings.go` loads your settings from the `.env` file at the top level
of the repository, so there is nothing to configure in this folder.

Then follow the [Preparation steps in the codelab README](../README.md#preparation)
to configure your Orkes account and webhook.

## Commands

Run every command from this folder (`webhooks/golang`).

| Step                | Command                    |
| ------------------- | -------------------------- |
| **create-db**       | `go run . create-db`       |
| **deploy-workflow** | `go run . deploy-workflow` |
| **serve-agent**     | `go run . serve-agent`     |
| **send-webhook**    | `go run . send-webhook`    |
| **query-db**        | `go run . query-db`        |

Each command compiles your latest code, then runs the step. If the code doesn't
compile, `go run` shows the compiler's errors instead. If a step fails, its own
error message comes first, followed by `go run`'s `exit status 1`. `go run` also
exits with status 1 when you stop **serve-agent** with Ctrl+C, although the
step itself stops cleanly.

The **deploy-workflow** step registers the workflow as
`wait_for_webhook_demo_golang` and the agent as
`webhook_customer_service_golang`. Select `wait_for_webhook_demo_golang` when
you set up your webhook.

## Where to Find Each Part

Comments beginning with `// Exercise N:` mark each place you will change for
that exercise.

| Codelab part                                                         | File                                  | Exercises |
| -------------------------------------------------------------------- | ------------------------------------- | --------- |
| Recipient user IDs                                                   | `settings/settings.go`                | 2, 3      |
| Workflow definition, readiness check, and storing email records      | `deploy_wait_for_webhook_workflow.go` | 1, 2      |
| `get_user_email` and `send_email` workers                            | `utils/workers.go`                    | 1, 2      |
| Webhook payload and `agent_input`                                    | `send_webhook_payload.go`             | 2, 3      |
| `webhook_customer_service_golang` agent and its tools                | `utils/webhook_agent.go`              | 3         |
| Read-only database queries                                           | `utils/query_sqlite_db.go`            | 3         |
| Database setup, using [`../shared/schema.sql`](../shared/schema.sql) | `utils/create_sqlite_db.go`           |           |
| Local database file, created by **create-db**                        | `utils/webhook_codelab_storage.db`    |           |
| Helper for the `WAIT_FOR_WEBHOOK` task                               | `utils/wait_for_webhook_task.go`      |           |
| Helper for the `AGENT` task                                          | `utils/agent_task.go`                 |           |
| Step names used by `go run . <step>`                                 | `main.go`                             |           |

## Go Notes

- **Exercise 1:** Use the standard `database/sql` package to write to the
  database. The project includes a SQLite driver, `modernc.org/sqlite`, which
  registers itself under the name `sqlite`, so
  `sql.Open("sqlite", utils.DatabasePath)` opens the database file. A worker
  returns the task's output as a map or a struct, which the SDK turns into
  JSON. A task's `OutputData` is that JSON read back into a `map[string]any`,
  so its numbers are `float64`.
- **Exercise 2:** `workflow.NewDynamicForkTask(referenceName, getEmailsTask)`
  creates the `DYNAMIC_FORK` task. It adds `getEmailsTask` before itself and a
  `JOIN` after it, so add only the fork to the workflow. The fork reads its
  tasks from the `forkedTasks` and `forkedTasksInputs` keys of the
  `get_user_emails` output, so return a map with those keys. The SDK's
  `workflow.DynamicForkInput` type would produce the keys `Tasks` and
  `TaskInput` instead. A worker runs one task at a time unless you raise its
  batch size with `worker.WithBatchSize`.
- **Exercise 3:** Create each agent tool with `tool.Func` from
  `github.com/conductor-sdk/conductor-go/sdk/ai/tool`. Pass it the tool's name,
  a function that takes a `context.Context` and a struct holding the tool's
  arguments, and a description. The SDK builds the tool's input schema from
  that struct, naming each field after its `json` tag, so a tool without
  arguments takes an empty `struct{}`. The agent receives each tool's result as
  JSON. A map or a struct becomes that JSON as it is, but the SDK nests any
  other result, such as a slice, under a `result` key.

## SDK Notes

This version uses version 1.10.3 of the Conductor Go SDK
(`github.com/conductor-sdk/conductor-go`), which includes the agent SDK as its
`sdk/ai` package. A few of its behaviors shape the code, so leave these parts
as they are:

- **Task types:** The SDK's workflow builder has no `WAIT_FOR_WEBHOOK` or
  `AGENT` tasks, and code outside the SDK can't add new kinds of task to it.
  The **deploy-workflow** step builds the rest of the workflow with the
  builder, then adds those two tasks, from `utils/wait_for_webhook_task.go` and
  `utils/agent_task.go`, to the definition that the builder produces.
- **Worker results:** The SDK only keeps a worker's result as the task's output
  if it is a map or a struct, and silently drops anything else, such as a
  string. That's why `get_user_email` returns its address in a map.
- **Connection settings:** The SDK reads `CONDUCTOR_SERVER_URL`,
  `CONDUCTOR_AUTH_KEY` and `CONDUCTOR_AUTH_SECRET` from the process
  environment. `settings.Load` adds the values from `.env` to that environment,
  so each step calls it before it creates a client.
- **Stopping workers:** The SDK's `TaskRunner.Shutdown` logs misleading errors
  as it stops each worker, so the **deploy-workflow** step leaves its workers
  running until the step exits.
- **Logging:** The SDK reports what its workers are doing at the `INFO` level.
  To see only its warnings and errors, set `LOG_LEVEL=warn` in your shell, for
  example `LOG_LEVEL=warn go run . deploy-workflow`. The SDK reads this
  variable before the step loads `.env`, so setting it there has no effect.
