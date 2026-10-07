# frozen_string_literal: true

# Register and start a durable webhook-driven workflow.
#
# The program keeps its local workers running until the workflow reaches the WAIT_FOR_WEBHOOK
# task, then exits. Conductor keeps the workflow suspended until send_webhook_payload.rb sends a
# callback; serve_webhook_agent.rb runs the local tools needed after it resumes.

require 'conductor'
require 'conductor/agents'
require 'sqlite3'

require_relative 'settings'
require_relative 'utils/agent_task'
require_relative 'utils/dynamic_fork_task'
require_relative 'utils/query_sqlite_db'
require_relative 'utils/wait_for_webhook_task'
require_relative 'utils/webhook_agent'
# Registers the worker_task methods in this file, which the TaskHandler in main then runs.
require_relative 'utils/workers'

WORKFLOW_NAME = "wait_for_webhook_demo_#{Settings::LANGUAGE}".freeze
WORKFLOW_VERSION = 1
WAIT_TASK_REF = 'wait_for_webhook_ref'

# The class each send_email output field must have to fit the emails table.
EMAIL_OUTPUT_FIELDS = { 'sent_time' => Integer, 'subject' => String, 'recipients' => String }.freeze

WORKFLOW_TIMEOUT_SECONDS = 7 * 24 * 60 * 60
READINESS_TIMEOUT_SECONDS = 60
POLL_INTERVAL_SECONDS = 1

# Shown in the workflow's description in the Orkes Conductor UI, and in every
# email this version sends, so you can tell the language versions apart.
CODELAB_LANGUAGE = 'Ruby'

# Build the workflow definition without registering or starting it.
def build_workflow
  workflow = Conductor.workflow(
    WORKFLOW_NAME,
    version: WORKFLOW_VERSION,
    description: "Durable wait-for-webhook example (registered from #{CODELAB_LANGUAGE})"
  ) do
    # Builds every send_email task for the fork, so it takes the subject and body too.
    simple(
      :get_user_emails,
      user_ids: wf[:user_ids],
      subject: "Hello from #{CODELAB_LANGUAGE}",
      body: "Sent by the #{CODELAB_LANGUAGE} version of the webhooks codelab."
    )

    output(agent_response: '${process_webhook_ref.output.text}')
  end
  definition = workflow.to_workflow_def

  # Mark the execution TIMED_OUT if it runs longer than WORKFLOW_TIMEOUT_SECONDS,
  # for example because no webhook arrives. ALERT_ONLY would let it keep running.
  definition.timeout_seconds = WORKFLOW_TIMEOUT_SECONDS
  definition.timeout_policy = Conductor::Workflow::TimeoutPolicy::TIME_OUT_WORKFLOW
  # Lists the input that every execution needs. Conductor shows it in the workflow definition
  # but does not require it when a workflow starts.
  definition.input_parameters = ['user_ids']

  webhook_wait = WaitForWebhookTask.build(
    WAIT_TASK_REF,
    matches: {
      # Every language version shares one webhook, so only match
      # payloads sent by this language's send-webhook step.
      "$['language']" => Settings::LANGUAGE,
      "$['type']" => 'customer',
      # Only resume for a webhook about the same users this execution emailed.
      "$['user_ids']" => '${workflow.input.user_ids}'
    }
  )

  agent_task = AgentTask.build(
    'process_webhook_ref',
    agent_name: WebhookAgent::NAME,
    prompt: "${#{WAIT_TASK_REF}.output.agent_input}"
  )

  # The SDK's dynamic_fork doesn't set this task up the way the server expects, and its builder
  # has no JOIN task, so both are added to the definition below, before webhook_wait.
  send_emails_fork = DynamicForkTask.build(
    'send_emails_fork',
    tasks: "${get_user_emails_ref.output.#{Workers::DYNAMIC_TASKS_PARAM}}",
    tasks_inputs: "${get_user_emails_ref.output.#{Workers::DYNAMIC_TASKS_INPUTS_PARAM}}"
  )
  # Waits for every branch of the fork; the server fills in its empty join_on list at runtime.
  send_emails_join = DynamicForkTask.join('send_emails_join')

  # The SDK's workflow builder has no AGENT task, and no way to add one, so the tasks from
  # WAIT_FOR_WEBHOOK onward follow the builder's own tasks in the definition it built.
  definition.tasks.push(send_emails_fork, send_emails_join, webhook_wait, agent_task)
  definition
end

# Start one workflow execution and return its execution ID.
def start_workflow(workflow_executor)
  request = Conductor::Http::Models::StartWorkflowRequest.new(
    name: WORKFLOW_NAME,
    version: WORKFLOW_VERSION,
    input: { 'user_ids' => Settings::USER_IDS }
  )
  workflow_executor.start_workflow(request)
end

# Wait until the execution reaches its WAIT_FOR_WEBHOOK task.
def wait_until_webhook_ready(workflow_executor, workflow_id)
  # Unlike Time.now, the monotonic clock is unaffected by changes to the system clock.
  deadline = Process.clock_gettime(Process::CLOCK_MONOTONIC) + READINESS_TIMEOUT_SECONDS

  while Process.clock_gettime(Process::CLOCK_MONOTONIC) < deadline
    execution = workflow_executor.get_workflow(workflow_id, include_tasks: true)

    wait_task = (execution.tasks || []).find { |task| task.reference_task_name == WAIT_TASK_REF }
    return execution if wait_task&.status == 'IN_PROGRESS'

    raise "Workflow entered terminal status #{execution.status}" if execution.terminal?

    sleep POLL_INTERVAL_SECONDS
  end

  raise "Workflow did not reach #{WAIT_TASK_REF} within #{READINESS_TIMEOUT_SECONDS} seconds"
end

# Return the output of every completed send_email task, after checking its fields.
def get_completed_email_outputs(execution)
  tasks = execution.tasks.select do |task|
    task.task_def_name == Workers::SEND_EMAIL_TASK_NAME && task.completed?
  end
  # No completed send_email task means no email was sent, so fail rather than report success.
  raise "No completed #{Workers::SEND_EMAIL_TASK_NAME} task outputs were found" if tasks.empty?

  # Check every output before inserting any, so a malformed one fails with a message naming its
  # task instead of a database error.
  tasks.map do |task|
    output = task.output_data || {}
    invalid_fields = EMAIL_OUTPUT_FIELDS.reject { |field, type| output[field].is_a?(type) }.keys
    unless invalid_fields.empty?
      raise "Completed task #{task.reference_task_name} has missing or invalid fields: " \
            "#{invalid_fields.join(', ')}"
    end

    output
  end
end

# Insert all completed email outputs in one database transaction.
def store_email_outputs(emails)
  QuerySqliteDb.open_database(writable: true) do |database|
    # Use a single DB transaction to avoid partial insert failures.
    database.transaction do
      emails.each do |email|
        database.execute(
          'INSERT INTO emails (sent_time, subject, recipients) VALUES (?, ?, ?)',
          [email['sent_time'], email['subject'], email['recipients']]
        )
      end
    end
  end
  emails.size
end

def main
  config = Conductor::Configuration.new
  # Polls for the tasks of every worker_task method until stopped.
  task_handler = Conductor::Worker::TaskHandler.new(configuration: config)
  task_handler.start

  begin
    # Register the agent that the workflow's AGENT task runs.
    Conductor::Agents::AgentRuntime.new(configuration: config).deploy(WebhookAgent::AGENT)

    workflow_executor = Conductor::Orkes::OrkesClients.new(config).get_workflow_executor
    # Overwrite any earlier version of the workflow with the same name and version.
    workflow_executor.register_workflow(build_workflow, overwrite: true)
    puts "Registered workflow #{WORKFLOW_NAME}, version #{WORKFLOW_VERSION}"

    workflow_id = start_workflow(workflow_executor)
    puts "Workflow URL: #{SETTINGS.server_base_url}/execution/#{workflow_id}"

    execution = wait_until_webhook_ready(workflow_executor, workflow_id)
    stored_count = store_email_outputs(get_completed_email_outputs(execution))
    puts "Stored #{stored_count} email record(s) in #{QuerySqliteDb::DATABASE_PATH}"
    puts "#{WAIT_TASK_REF} is ready"
    puts 'Before sending the webhook, start the agent tool workers with ' \
         '`bundle exec ruby serve_webhook_agent.rb`, or restart them if you\'ve changed ' \
         'the code since they started.'
    puts "Webhook URL: #{SETTINGS.webhook_endpoint_url}"
    0
  rescue RuntimeError, QuerySqliteDb::DatabaseNotFoundError, SQLite3::Exception => e
    # Report expected failures in one line, as the query-db step does.
    warn "Deploy step failed: #{e.message}"
    1
  ensure
    task_handler.stop
  end
end

exit(main) if $PROGRAM_NAME == __FILE__
