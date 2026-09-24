# Webhooks Codelab: C\#

This folder contains the C# version of the
[webhooks codelab](../README.md). The walkthrough and exercises are in that
README; this page covers setup, the command for each step, and where to find
each part of the code.

## Setup

This version requires the
[.NET 10 SDK](https://dotnet.microsoft.com/download/dotnet/10.0). Complete the
[Setup section of the top-level README](../../README.md#setup) first. There is
nothing else to install: the first `dotnet run` downloads the NuGet packages
listed in `WebhooksCodelab.csproj` and builds the project.

`Settings.cs` loads your settings from the `.env` file at the top level of the
repository, so there is nothing to configure in this folder. It finds that file
by searching upward from the current folder, so run every command from this
folder.

Each build warns that the `OpenTelemetry.Api` package has a known
moderate-severity vulnerability. That package is a dependency of the Conductor
C# SDK (`conductor-csharp`), not of the codelab's own code, and the warning
does not stop the build.

Then follow the [Preparation steps in the codelab README](../README.md#preparation)
to configure your Orkes account and webhook.

## Commands

Run every command from this folder (`webhooks/csharp`).

| Step | Command |
| --- | --- |
| **create-db** | `dotnet run -- create-db` |
| **deploy** | `dotnet run -- deploy` |
| **serve-agent** | `dotnet run -- serve-agent` |
| **send-webhook** | `dotnet run -- send-webhook` |
| **query-db** | `dotnet run -- query-db` |

The **deploy** step registers the workflow as `wait_for_webhook_demo_csharp`
and the agent as `webhook_customer_service_csharp`. Select
`wait_for_webhook_demo_csharp` when you set up your webhook.

## Where to Find Each Part

Comments beginning with `// Exercise N:` mark each place you will change for
that exercise.

| Codelab part | File | Exercises |
| --- | --- | --- |
| Recipient user IDs | `Settings.cs` | 2, 3 |
| Workflow definition, readiness check, and storing email records | `DeployWaitForWebhookWorkflow.cs` | 1, 2 |
| `get_user_email` and `send_email` workers | `Utils/Workers.cs` | 1, 2 |
| Webhook payload and `agent_input` | `SendWebhookPayload.cs` | 2, 3 |
| `webhook_customer_service_csharp` agent and its tools | `Utils/WebhookAgent.cs` | 3 |
| Read-only database queries | `Utils/QuerySqliteDb.cs` | 3 |
| Helper for the `DYNAMIC_FORK` task | `Utils/DynamicForkTask.cs` | 2 |
| Database setup, using [`../shared/schema.sql`](../shared/schema.sql) | `Utils/CreateSqliteDb.cs` | |
| Local database file, created by **create-db** | `Utils/webhook_codelab_storage.db` | |
| Adapter that adds an `AGENT` task to the workflow | `Utils/AgentTask.cs` | |
| Step names used by `dotnet run -- <step>` | `Program.cs` | |

## C# Notes

- **Exercise 1:** Use the
  [`Microsoft.Data.Sqlite` package](https://learn.microsoft.com/dotnet/standard/data/sqlite/),
  which the project already references, to write to the database.
  `QuerySqliteDb.DatabasePath` gives the location of the database file. Return
  each email record from `send_email` as a `Dictionary<string, object>` (see
  [SDK Workarounds](#sdk-workarounds)).
- **Exercise 2:** Use `DynamicForkTask` from `Utils/DynamicForkTask.cs` for the
  `DYNAMIC_FORK` task, and add the SDK's `JoinTask` straight after it when you
  call `WithTask`. Return the forked task definitions and their inputs from
  `get_user_emails` as a `Dictionary<string, object>` too.
- **Exercise 3:** Declare each agent tool as a public method marked with the
  `[Tool]` attribute from `Conductor.AI`, on a class you can create an instance
  of. `ToolRegistry.FromInstance` turns those methods into the list of tools for
  the agent's `Tools` property. The agent receives each tool's result as JSON:
  dictionary keys stay exactly as you wrote them, but object properties become
  camelCase, so use the resulting names in the agent's instructions.

## SDK Workarounds

This version uses version 3.0.0 of the Conductor C# SDK (`conductor-csharp`),
which has several bugs. The code works around each one, with a comment
explaining why, so leave these parts as they are:

- **Task types:** The SDK sends each task's type in a field that the server
  only accepts for standard Conductor tasks. `DeployWaitForWebhookWorkflow.cs`
  sets the `WAIT_FOR_WEBHOOK` task's type directly, and `Utils/AgentTask.cs`
  does the same for the `AGENT` task, which the SDK has no class for.
- **Webhook match rules:** `WaitForWebHookTask` puts the match rules in the
  wrong place, so the **deploy** step nests them under `matches` itself.
- **Workflow output:** `ConductorWorkflow.WithOutputParameter` throws an
  exception on a new workflow, so the **deploy** step sets `OutputParameters`
  directly.
- **Dynamic forks:** The SDK's `DynamicFork` class leaves out the settings that
  tell the server where to find the forked tasks, so use
  `Utils/DynamicForkTask.cs` instead.
- **Worker settings:** Passing arguments to the `[WorkerTask]` attribute's
  constructor sets the worker's batch size to 0, which stops it from ever
  polling for tasks. Set the task name as a property instead, for example
  `[WorkerTask(TaskType = "send_email")]`.
- **Worker return types:** A `[WorkerTask]` method must return a string, a
  number, a `List<object>` or a `Dictionary<string, object>`. Any other type,
  such as a record or an anonymous object, makes the task fail. Agent tools do
  not have this limit.
- **Connection settings:** The SDK ignores the `CONDUCTOR_SERVER_URL`,
  `CONDUCTOR_AUTH_KEY` and `CONDUCTOR_AUTH_SECRET` variables, so
  `Settings.CreateConductorConfiguration()` builds the connection from them.

The SDK also starts every worker it finds in the project, so the
**serve-agent** step runs the `get_user_email` and `send_email` workers as well
as the agent's tools. This is harmless on its own, but it is another reason to
stop it before you run another language's steps, as the
[codelab README](../README.md#choose-a-language) explains.

The missing `AGENT` task type and the `DynamicFork` bugs are tracked in the
SDK's issues [#161](https://github.com/conductor-oss/csharp-sdk/issues/161),
[#158](https://github.com/conductor-oss/csharp-sdk/issues/158) and
[#159](https://github.com/conductor-oss/csharp-sdk/issues/159).
