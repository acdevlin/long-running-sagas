# Webhooks Codelab: Java

This folder contains the Java version of the
[webhooks codelab](../README.md). The walkthrough and exercises are in that
README; this page covers setup, the command for each step, and where to find
each part of the code.

## Setup

This version requires a Java Development Kit (JDK), version 21 or newer, such
as [Eclipse Temurin](https://adoptium.net/). If `java -version` shows an older
version, or no Java at all, point the `JAVA_HOME` variable at your JDK. Complete
the [Setup section of the top-level README](../../README.md#setup) first.

There is nothing else to install. The first command you run downloads the
version of Gradle that this project uses, through the Gradle wrapper
(`gradlew`), and Gradle then downloads the libraries listed in
`build.gradle.kts`. That first command takes a minute or two.

`Settings.java` loads your settings from the `.env` file at the top level of the
repository, so there is nothing to configure in this folder. It finds that file
by searching upward from the current folder, so run every command from this
folder.

Then follow the [Preparation steps in the codelab README](../README.md#preparation)
to configure your Orkes account and webhook.

## Commands

Run every command from this folder (`webhooks/java`). On Windows, use
`gradlew.bat` in place of `./gradlew`.

| Step                | Command                     |
| ------------------- | --------------------------- |
| **create-db**       | `./gradlew create-db`       |
| **deploy-workflow** | `./gradlew deploy-workflow` |
| **serve-agent**     | `./gradlew serve-agent`     |
| **send-webhook**    | `./gradlew send-webhook`    |
| **query-db**        | `./gradlew query-db`        |

Each command compiles any code you have changed before it runs the step. If a
step fails, its own error message comes first, followed by Gradle's
`FAILURE: Build failed` report.

The **deploy-workflow** step registers the workflow as
`wait_for_webhook_demo_java` and the agent as `webhook_customer_service_java`.
Select `wait_for_webhook_demo_java` when you set up your webhook.

## Where to Find Each Part

Comments beginning with `// Exercise N:` mark each place you will change for
that exercise. The Java files below are in
`src/main/java/io/orkes/codelab/webhooks`.

| Codelab part                                                         | File                                | Exercises |
| -------------------------------------------------------------------- | ----------------------------------- | --------- |
| Recipient user IDs                                                   | `Settings.java`                     | 2, 3      |
| Workflow definition, readiness check, and storing email records      | `DeployWaitForWebhookWorkflow.java` | 1, 2      |
| `get_user_email` and `send_email` workers                            | `utils/Workers.java`                | 1, 2      |
| Webhook payload and `agent_input`                                    | `SendWebhookPayload.java`           | 2, 3      |
| `webhook_customer_service_java` agent and its tools                  | `utils/WebhookAgent.java`           | 3         |
| Read-only database queries                                           | `utils/QuerySqliteDb.java`          | 3         |
| Database setup, using [`../shared/schema.sql`](../shared/schema.sql) | `utils/CreateSqliteDb.java`         |           |
| Local database file, created by **create-db** in this folder         | `webhook_codelab_storage.db`        |           |
| Adapter that adds a `WAIT_FOR_WEBHOOK` task to the workflow          | `utils/WaitForWebhookTask.java`     |           |
| Adapter that adds an `AGENT` task to the workflow                    | `utils/AgentTask.java`              |           |
| Step names used by `./gradlew <step>`                                | `Main.java` and `build.gradle.kts`  |           |

## Java Notes

- **Exercise 1:** Use JDBC with the SQLite driver that the project already
  includes, for example
  `DriverManager.getConnection("jdbc:sqlite:" + QuerySqliteDb.DATABASE_PATH)`,
  to write to the database. A worker method can return a `Map<String, Object>`
  or a record; the SDK turns a record into the task's output, keeping its
  component names as written.
- **Exercise 2:** The SDK's `DynamicFork` creates the `DYNAMIC_FORK` task and
  the `JOIN` after it. Build it from the `get_user_emails` task, whose worker
  then returns a `DynamicForkInput` holding one `SimpleTask` per email and each
  task's input. Its task list must be a `List<Task<?>>`, which a stream's
  `toList()` of `SimpleTask`s is not, so collect the stream with
  `collect(Collectors.toList())` instead. A `@WorkerTask` method runs one task
  at a time unless you raise its `threadCount`.
- **Exercise 3:** Declare each agent tool as a public method with the `@Tool`
  annotation from `org.conductoross.conductor.ai.annotations`, on a class of its
  own. `ToolRegistry.fromInstance(new YourTools())` turns those methods into the
  list for the agent builder's `tools(...)`. The agent receives each tool's
  result as JSON: map keys stay exactly as you wrote them, and a record's
  components keep their names unless you rename them with Jackson's
  `@JsonProperty`.

## SDK Notes

This version uses version 6.0.1 of the Conductor Java SDK
(`conductor-client-ai`, which includes `conductor-client`). A few of its
behaviors shape the code, so leave these parts as they are:

- **Task types:** The SDK has no classes for the `WAIT_FOR_WEBHOOK` and `AGENT`
  tasks, and its `TaskType` enum has no members for them.
  `utils/WaitForWebhookTask.java` and `utils/AgentTask.java` create them, and
  set each type through the `updateWorkflowTask` method that task subclasses
  can override.
- **Connection settings:** The SDK reads `CONDUCTOR_SERVER_URL`,
  `CONDUCTOR_AUTH_KEY` and `CONDUCTOR_AUTH_SECRET` only from the process
  environment, which a Java program cannot add `.env` values to.
  `Settings.createApiClient()` builds the connection from them instead.
- **Agent runtime:** Closing an `AgentRuntime` also shuts down the client it was
  given, so the **deploy-workflow** step gives the runtime a client of its own.
- **Parameter names:** An agent tool's input schema uses the names of its
  method's parameters, which Java only keeps when it compiles with the
  `-parameters` option. `build.gradle.kts` turns that option on.
- **Logging:** The SDK logs through SLF4J, and
  `src/main/resources/simplelogger.properties` shows only its warnings and
  errors. Change the level there to `info` to see more of what the SDK does.
