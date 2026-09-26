# Webhooks Codelab: TypeScript

This folder contains the TypeScript version of the
[webhooks codelab](../README.md). The walkthrough and exercises are in that
README; this page covers setup, the command for each step, and where to find
each part of the code.

## Setup

This version requires [Node.js](https://nodejs.org/) 24 or newer, which
includes npm. Complete the
[Setup section of the top-level README](../../README.md#setup) first. Then,
from this folder, run `npm install` to install the packages listed in
`package.json`, at the versions recorded in `package-lock.json`.

`package.json` also tells npm which of those packages may run a script when
they are installed: esbuild, which tsx uses to read TypeScript, may, and
fsevents, which tsx does not use here, may not. Newer versions of npm ask
about each such package, so this keeps `npm install` from printing warnings.

`settings.ts` loads your settings from the `.env` file at the top level of the
repository, so there is nothing to configure in this folder.

Then follow the [Preparation steps in the codelab README](../README.md#preparation)
to configure your Orkes account and webhook.

## Commands

Run every command from this folder (`webhooks/typescript`).

| Step                | Command                   |
| ------------------- | ------------------------- |
| **create-db**       | `npm run create-db`       |
| **deploy-workflow** | `npm run deploy-workflow` |
| **serve-agent**     | `npm run serve-agent`     |
| **send-webhook**    | `npm run send-webhook`    |
| **query-db**        | `npm run query-db`        |

Each command runs the step's file with [tsx](https://tsx.is/), which runs
TypeScript without a separate build step, so every step runs your latest code.
tsx does not check types, though. Your editor shows type errors as you work,
and `npm run typecheck` checks the whole project.

The **deploy-workflow** step registers the workflow as
`wait_for_webhook_demo_typescript` and the agent as
`webhook_customer_service_typescript`. Select
`wait_for_webhook_demo_typescript` when you set up your webhook.

## Where to Find Each Part

Comments beginning with `// Exercise N:` mark each place you will change for
that exercise.

| Codelab part                                                         | File                               | Exercises |
| -------------------------------------------------------------------- | ---------------------------------- | --------- |
| Recipient user IDs                                                   | `settings.ts`                      | 2, 3      |
| Workflow definition, readiness check, and storing email records      | `deployWaitForWebhookWorkflow.ts`  | 1, 2      |
| `get_user_email` and `send_email` workers                            | `utils/workers.ts`                 | 1, 2      |
| Webhook payload and `agent_input`                                    | `sendWebhookPayload.ts`            | 2, 3      |
| `webhook_customer_service_typescript` agent and its tools            | `utils/webhookAgent.ts`            | 3         |
| Read-only database queries                                           | `utils/querySqliteDb.ts`           | 3         |
| Helper for the `DYNAMIC_FORK` task                                   | `utils/dynamicForkTask.ts`         | 2         |
| Database setup, using [`../shared/schema.sql`](../shared/schema.sql) | `utils/createSqliteDb.ts`          |           |
| Local database file, created by **create-db**                        | `utils/webhook_codelab_storage.db` |           |
| Helper that adds a `WAIT_FOR_WEBHOOK` task to the workflow           | `utils/waitForWebhookTask.ts`      |           |
| Helper that adds an `AGENT` task to the workflow                     | `utils/agentTask.ts`               |           |
| Step names used by `npm run <step>`                                  | `package.json`                     |           |

## TypeScript Notes

- **Exercise 1:** Node.js's built-in
  [`node:sqlite` module](https://nodejs.org/api/sqlite.html) is all you need to
  write to the database, and `DATABASE_PATH` in `utils/querySqliteDb.ts` gives
  the location of the database file. A worker method returns the task's
  `status` and its output, as `outputData`. Keep its `Promise<WorkerResult>`
  return type: without it, TypeScript reports a confusing error on the
  `@worker` decorator instead of on the method.
- **Exercise 2:** Use `dynamicForkTask` from `utils/dynamicForkTask.ts` for the
  `DYNAMIC_FORK` task, and the SDK's `joinTask` for the `JOIN` after it. To pass
  part of one task's output to another, use the **deploy-workflow** step's
  `taskOutput` function, which builds an expression such as
  `${get_user_email_ref.output.result}`.
- **Exercise 3:** Create each agent tool with the `tool` function from
  `@io-orkes/conductor-javascript/agents`. Pass it an async function that takes
  the tool's arguments as one object, then its `name`, its `description` and an
  `inputSchema`: a JSON Schema object that describes those arguments. The agent
  receives each tool's result as JSON. A returned object becomes that JSON as it
  is, with its keys exactly as you wrote them, but the SDK nests any other
  return value, such as an array, under a `result` key.

## SDK Notes

This version uses version 4.0.0 of the Conductor JavaScript SDK
(`@io-orkes/conductor-javascript`), which includes the agent SDK as
`@io-orkes/conductor-javascript/agents`. A few of its behaviors shape the code,
so leave these parts as they are:

- **Webhook match rules:** The SDK's `waitForWebhookTask` puts the match rules
  in the wrong place, so `utils/waitForWebhookTask.ts` creates the task with
  the rules under `matches`, where the server reads them.
- **Dynamic forks:** The SDK's `dynamicForkTask` only accepts a list of tasks
  that is fixed when the workflow is built. `utils/dynamicForkTask.ts` takes
  the list from another task's output when the workflow runs instead.
- **Agent tasks:** The SDK has no builder for the `AGENT` task, so
  `utils/agentTask.ts` creates it.
- **Decorators:** Node.js can run TypeScript files by itself, but not the
  SDK's `@worker` decorator, which is why each step runs with tsx.
  `tsconfig.json` turns on `verbatimModuleSyntax`: without it, tsx would drop
  the import that registers the workers, because none of its names are used.
- **Worker methods:** The SDK calls each `@worker` method without creating an
  instance of its class, so the methods in `utils/workers.ts` are `static` and
  cannot use `this`.
- **Stopping cleanly:** The SDK's client keeps refreshing its access token in
  the background, which would stop a step from ever exiting. The
  **deploy-workflow** and **serve-agent** steps stop it before they finish.
- **Logging:** The SDK reports what its workers are doing at the `INFO` level.
  To see only its warnings and errors, set `CONDUCTOR_LOG_LEVEL=WARN` in your
  shell or in `.env`.
