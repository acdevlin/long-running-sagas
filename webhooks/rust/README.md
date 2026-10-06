# Webhooks Codelab: Rust

This folder contains the Rust version of the
[webhooks codelab](../README.md). The walkthrough and exercises are in that
README; this page covers setup, the command for each step, and where to find
each part of the code.

## Setup

This version requires [Rust](https://rustup.rs/) 1.85 or newer, which includes
Cargo. Complete the [Setup section of the top-level README](../../README.md#setup)
first.

There is nothing else to install. The first command you run downloads the
crates listed in `Cargo.toml`, at the versions recorded in `Cargo.lock`, and
compiles them, which takes a minute or so. That includes SQLite, which the
`rusqlite` crate compiles with the same C tools that Rust uses to link
programs. Later commands only compile the code you change.

`src/settings.rs` loads your settings from the `.env` file at the top level of
the repository, so there is nothing to configure in this folder.

Then follow the [Preparation steps in the codelab README](../README.md#preparation)
to configure your Orkes account and webhook.

## Commands

Run every command from this folder (`webhooks/rust`).

| Step                | Command                        |
| ------------------- | ------------------------------ |
| **create-db**       | `cargo run -- create-db`       |
| **deploy-workflow** | `cargo run -- deploy-workflow` |
| **serve-agent**     | `cargo run -- serve-agent`     |
| **send-webhook**    | `cargo run -- send-webhook`    |
| **query-db**        | `cargo run -- query-db`        |

Each command compiles any code you have changed, then runs the step. If the
code doesn't compile, Cargo shows the compiler's errors instead. Cargo also
prints a line or two about its own work before the step's output; add `-q`, as
in `cargo run -q -- deploy-workflow`, to hide them. If a step fails, it prints
its name followed by the error.

The **deploy-workflow** step registers the workflow as
`wait_for_webhook_demo_rust` and the agent as `webhook_customer_service_rust`.
Select `wait_for_webhook_demo_rust` when you set up your webhook.

## Where to Find Each Part

Comments beginning with `// Exercise N:` mark each place you will change for
that exercise.

| Codelab part                                                         | File                                      | Exercises |
| -------------------------------------------------------------------- | ----------------------------------------- | --------- |
| Recipient user IDs                                                   | `src/settings.rs`                         | 2, 3      |
| Workflow definition, readiness check, and storing email records      | `src/deploy_wait_for_webhook_workflow.rs` | 1, 2      |
| `get_user_email` and `send_email` workers                            | `src/utils/workers.rs`                    | 1, 2      |
| Webhook payload and `agent_input`                                    | `src/send_webhook_payload.rs`             | 2, 3      |
| `webhook_customer_service_rust` agent and its tools                  | `src/utils/webhook_agent.rs`              | 3         |
| Read-only database queries                                           | `src/utils/query_sqlite_db.rs`            | 3         |
| Helper for the `DYNAMIC_FORK` task                                   | `src/utils/dynamic_fork_task.rs`          | 2         |
| Database setup, using [`../shared/schema.sql`](../shared/schema.sql) | `src/utils/create_sqlite_db.rs`           |           |
| Local database file, created by **create-db** in this folder         | `webhook_codelab_storage.db`              |           |
| Helper that creates the `AGENT` task                                 | `src/utils/agent_task.rs`                 |           |
| Step names used by `cargo run -- <step>`                             | `src/main.rs`                             |           |

The steps' code is a library, listed in `src/lib.rs`, that `src/main.rs` runs.
Rust warns about unused functions in a program, but not about a library's
public ones, so the helpers that only later exercises use don't cause warnings.

## Rust Notes

- **Exercise 1:** Use `rusqlite`, which the project already includes, to write
  to the database, for example with `Connection::open(DATABASE_PATH)`, where
  `DATABASE_PATH` comes from `src/utils/query_sqlite_db.rs`. The `#[worker]`
  macro stores whatever a worker function returns under a `result` key in the
  task's output. To choose the output's keys yourself, return a
  `conductor::worker::WorkerOutput`, such as `WorkerOutput::completed(output)`
  with a `HashMap<String, serde_json::Value>`. A task's `output_data` is that
  same kind of map, so read `sent_time` with `as_i64()`.
- **Exercise 2:** Use `dynamic_fork_task` from `src/utils/dynamic_fork_task.rs`
  for the `DYNAMIC_FORK` task, and the SDK's `WorkflowTask::join` for the `JOIN`
  after it. As in Exercise 1, return a `WorkerOutput` from `get_user_emails`,
  so that the fork finds `dynamicTasks` and `dynamicTasksInputs` at the top
  level of its output. A worker runs one task at a time unless you raise its
  `thread_count`, for example `#[worker(name = "send_email", thread_count = 10)]`.
- **Exercise 3:** Declare each agent tool with the SDK's `#[tool]` macro
  (`use conductor::tool;`) on an async function that takes one struct of
  arguments and returns `conductor::Result<serde_json::Value>`. The struct
  derives serde's `Deserialize` and schemars' `JsonSchema`, from which the
  macro builds the tool's input schema, so a tool without arguments takes an
  empty struct. Use the `schemars` version in `Cargo.toml`: the SDK doesn't
  work with newer ones. The macro names the tool after its function and adds a
  function such as `summarize_email_activity_tool()`, which returns the tool
  for `with_tools`. `with_max_turns` returns a `Result`, so add `?` after it
  before calling the next method in the chain. The SDK only accepts its own
  errors from a tool, so convert the query helpers' errors, for example with
  `.map_err(|error| ConductorError::agent(format!("{error:#}")))`. The agent
  receives each tool's result as JSON. A JSON object stays as it is, but the
  SDK nests any other result, such as a list, under a `result` key.

## SDK Notes

This version uses version 0.2.0 of the Conductor Rust SDK (`conductor-sdk`),
which includes the agent SDK behind its `agents` feature. A few of its behaviors
shape the code, so leave these parts as they are:

- **Installation:** Version 0.2.0 isn't on crates.io yet, so `Cargo.toml`
  downloads it from its `v0.2.0` tag on GitHub, and `Cargo.lock` records the
  exact commit. The dependency is renamed to `conductor` because the SDK's
  `#[worker]` and `#[tool]` macros refer to it by that name.
- **Agent tasks:** The SDK's `WorkflowTask` can only have one of the task types
  that its `TaskType` enum lists, and `AGENT` isn't one of them. So the
  **deploy-workflow** step converts the definition built with the SDK to JSON,
  adds the `AGENT` task from `src/utils/agent_task.rs`, and sends it with the
  SDK's general-purpose API client.
- **Dynamic forks:** The SDK has no builder for the `DYNAMIC_FORK` task, so
  `src/utils/dynamic_fork_task.rs` creates it.
- **Worker inputs:** `#[worker]` fills each parameter from the task input of
  the same name. If that input is missing or has the wrong type, the parameter
  gets its type's default value, such as an empty string or list, rather than
  an error.
- **Serving tools:** `AgentRuntime::serve` doesn't deploy the agent, returns as
  soon as its tool workers are polling, and fails if the agent has no tools. So
  the **serve-agent** step deploys the agent itself, only calls `serve` once
  the agent has tools, and waits for Ctrl+C.
- **Logging:** The SDK logs through the `tracing` crate, and `src/main.rs`
  shows only its warnings and errors. To see what its workers are doing, set
  `RUST_LOG=info` in your shell or in `.env`.
