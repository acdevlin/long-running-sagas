# Webhooks Codelab: Ruby

This folder contains the Ruby version of the
[webhooks codelab](../README.md). The walkthrough and exercises are in that
README; this page covers setup, the command for each step, and where to find
each part of the code.

## Setup

This version requires [Ruby](https://www.ruby-lang.org/) 3.3 or newer, which
includes Bundler. macOS comes with Ruby 2.6, which is too old, so check that
`ruby -v` shows 3.3 or newer, and install a newer Ruby if it doesn't, for
example with [Homebrew](https://formulae.brew.sh/formula/ruby). Complete the
[Setup section of the top-level README](../../README.md#setup) first.

Then, from this folder, run `bundle install` to install the gems listed in
`Gemfile`, at the versions recorded in `Gemfile.lock`. One of them, `json`, is
compiled from C source, so you also need a C compiler:

- **macOS:** the Xcode Command Line Tools, which Homebrew installs, or
  `xcode-select --install`
- **Windows:** the "Ruby+Devkit" download from
  [RubyInstaller](https://rubyinstaller.org/)
- **Linux:** your distribution's build tools, such as Debian's and Ubuntu's
  `build-essential`

`settings.rb` loads your settings from the `.env` file at the top level of the
repository, so there is nothing to configure in this folder.

Then follow the [Preparation steps in the codelab README](../README.md#preparation)
to configure your Orkes account and webhook.

## Commands

Run every command from this folder (`webhooks/ruby`).

| Step                | Command                                                |
| ------------------- | ------------------------------------------------------ |
| **create-db**       | `bundle exec ruby utils/create_sqlite_db.rb`           |
| **deploy-workflow** | `bundle exec ruby deploy_wait_for_webhook_workflow.rb` |
| **serve-agent**     | `bundle exec ruby serve_webhook_agent.rb`              |
| **send-webhook**    | `bundle exec ruby send_webhook_payload.rb`             |
| **query-db**        | `bundle exec ruby utils/query_sqlite_db.rb`            |

`bundle exec` runs each step with the gem versions in `Gemfile.lock`.

The **deploy-workflow** step registers the workflow as
`wait_for_webhook_demo_ruby` and the agent as `webhook_customer_service_ruby`.
Select `wait_for_webhook_demo_ruby` when you set up your webhook.

## Where to Find Each Part

Comments beginning with `# Exercise N:` mark each place you will change for
that exercise.

| Codelab part                                                         | File                                  | Exercises |
| -------------------------------------------------------------------- | ------------------------------------- | --------- |
| Recipient user IDs                                                   | `settings.rb`                         | 2, 3      |
| Workflow definition, readiness check, and storing email records      | `deploy_wait_for_webhook_workflow.rb` | 1, 2      |
| `get_user_email` and `send_email` workers                            | `utils/workers.rb`                    | 1, 2      |
| Webhook payload and `agent_input`                                    | `send_webhook_payload.rb`             | 2, 3      |
| `webhook_customer_service_ruby` agent and its tools                  | `utils/webhook_agent.rb`              | 3         |
| Read-only database queries                                           | `utils/query_sqlite_db.rb`            | 3         |
| Helpers for the `DYNAMIC_FORK` and `JOIN` tasks                      | `utils/dynamic_fork_task.rb`          | 2         |
| Database setup, using [`../shared/schema.sql`](../shared/schema.sql) | `utils/create_sqlite_db.rb`           |           |
| Local database file, created by **create-db**                        | `utils/webhook_codelab_storage.db`    |           |
| Helper that creates the `WAIT_FOR_WEBHOOK` task                      | `utils/wait_for_webhook_task.rb`      |           |
| Helper that creates the `AGENT` task                                 | `utils/agent_task.rb`                 |           |

## Ruby Notes

- **Exercise 1:** Use the `sqlite3` gem, which the project already includes, to
  write to the database, for example with
  `SQLite3::Database.open(QuerySqliteDb::DATABASE_PATH)`. A worker method's
  return value becomes the task's output: the SDK sends a Hash as it is, and
  stores a string or number under a `result` key.
- **Exercise 2:** Use `DynamicForkTask.build` and `DynamicForkTask.join` from
  `utils/dynamic_fork_task.rb` for the `DYNAMIC_FORK` task and the `JOIN` after
  it, and add them where the hint in `build_workflow` shows. A worker runs one
  task at a time unless you raise its `thread_count`, for example
  `worker_task 'send_email', thread_count: 10`.
- **Exercise 3:** Add `extend Conductor::Agents::Tools` to the `WebhookAgent`
  module. Define each tool there as an ordinary method (`def`, not `def self.`),
  then declare it with `tool :method_name, description: '...'`. Inside the
  module, `self[:method_name]` returns the declared tool for the agent's
  `tools:` list. Give each tool parameter as a required keyword argument, such
  as `recipient:`. A tool without parameters still needs a `**` parameter, as
  in `def summarize_email_activity(**)` (see SDK Notes). The query helpers
  return Hashes, which the agent receives as JSON with their keys as they are.

## SDK Notes

This version uses version 0.1.1 of the Conductor Ruby SDK (`conductor_ruby`),
which includes the agent SDK as `conductor/agents`. A few of its behaviors shape
the code, so leave these parts as they are:

- **base64:** The SDK uses the `base64` library without listing it as a
  dependency. Ruby 3.4 moved `base64` out of the standard library, so `Gemfile`
  lists it, or the SDK would fail to load.
- **Workflow tasks:** The SDK's workflow builder has no `AGENT` task and no
  `JOIN` task of its own, and its `dynamic_fork` doesn't set up the task the way
  the server expects. The builder also has no way to add other tasks. So the
  **deploy-workflow** step builds the worker tasks with it, then adds the
  `WAIT_FOR_WEBHOOK` and `AGENT` tasks after them in the definition it
  produces, using `utils/wait_for_webhook_task.rb` and `utils/agent_task.rb`.
  Exercise 2's fork and join go in the same place.
- **Timeout policy:** The workflow builder can't set a timeout policy, so the
  **deploy-workflow** step sets the timeout and its policy on the definition
  instead.
- **Tool parameters:** The SDK reads a keyword argument's default value, such as
  `recipient: String`, to give a tool parameter a type, but from Ruby 3.4 it
  can no longer read it. The parameter then has no type and isn't required. A
  required keyword argument, such as `recipient:`, is always marked as
  required. To give it a type too, pass `tool` an `input_schema:`.
- **Tool inputs:** The SDK removes its own keys from a tool task's input, but
  not keys the server adds, such as `_createdBy`. It passes those to a tool
  without parameters as keyword arguments, so that tool fails with "wrong
  number of arguments" unless it accepts `**`. A tool with parameters receives
  only its parameters.
- **Serving tools:** `AgentRuntime#serve` normally waits for Ctrl+C itself, but
  Ruby stops it with a deadlock error when the agent has no tools, as before
  Exercise 3. So the **serve-agent** step calls it with `blocking: false` and
  waits for Ctrl+C itself.
- **Logging:** The SDK reports what its workers are doing at the `INFO` level,
  and has no setting to change that.
