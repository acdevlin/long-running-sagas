# frozen_string_literal: true

# Register and start a durable webhook-driven workflow.
#
# The program keeps its local workers running until the workflow reaches the WAIT_FOR_WEBHOOK
# task, then exits. Conductor keeps the workflow suspended until send_webhook_payload.rb sends a
# callback; serve_webhook_agent.rb runs the local tools needed after it resumes.

require 'conductor'
require 'conductor/agents'

require_relative 'settings'
require_relative 'utils/agent_task'
require_relative 'utils/wait_for_webhook_task'
require_relative 'utils/webhook_agent'
# Registers the worker_task methods in this file, which the TaskHandler in main then runs.
require_relative 'utils/workers'

WORKFLOW_NAME = "wait_for_webhook_demo_#{Settings::LANGUAGE}".freeze
WORKFLOW_VERSION = 1
WAIT_TASK_REF = 'wait_for_webhook_ref'

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
    # Exercise 2: Replace this with one get_user_emails task that resolves every address in
    # wf[:user_ids], so the number of emails is decided at runtime. Pass it the subject and body
    # as well, for the forked send_email tasks.
    get_email_task = simple(:get_user_email, user_id: wf[:user_id])

    # Exercise 2: Remove this task. The DYNAMIC_FORK task from utils/dynamic_fork_task.rb, added
    # below, sends the emails instead.
    simple(
      :send_email,
      recipients: get_email_task[:result],
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

  webhook_wait = WaitForWebhookTask.build(
    WAIT_TASK_REF,
    matches: {
      # Every language version shares one webhook, so only match
      # payloads sent by this language's send-webhook step.
      "$['language']" => Settings::LANGUAGE,
      "$['type']" => 'customer',
      # Exercise 2: Change to 'user_ids'. Be sure the payload sent by
      # send_webhook_payload.rb matches the key you use here.
      "$['user_id']" => '${workflow.input.user_id}'
    }
  )

  agent_task = AgentTask.build(
    'process_webhook_ref',
    agent_name: WebhookAgent::NAME,
    prompt: "${#{WAIT_TASK_REF}.output.agent_input}"
  )

  # The SDK's workflow builder has no AGENT task, and no way to add one, so the tasks from
  # WAIT_FOR_WEBHOOK onward follow the builder's own tasks in the definition it built.
  # Exercise 2: Add the DYNAMIC_FORK and JOIN tasks here, before webhook_wait.
  definition.tasks.push(webhook_wait, agent_task)
  definition
end

# Start one workflow execution and return its execution ID.
def start_workflow(workflow_executor)
  request = Conductor::Http::Models::StartWorkflowRequest.new(
    name: WORKFLOW_NAME,
    version: WORKFLOW_VERSION,
    input: { 'user_id' => Settings::USER_ID }
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
    if wait_task&.status == 'IN_PROGRESS'
      # Exercise 1: Return this execution, with its tasks, so the caller can read every
      # completed send_email output.
      return nil
    end

    raise "Workflow entered terminal status #{execution.status}" if execution.terminal?

    sleep POLL_INTERVAL_SECONDS
  end

  raise "Workflow did not reach #{WAIT_TASK_REF} within #{READINESS_TIMEOUT_SECONDS} seconds"
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

    wait_until_webhook_ready(workflow_executor, workflow_id)
    # Exercise 1: Store a row in QuerySqliteDb::DATABASE_PATH for each completed send_email
    # task's output_data. Match tasks on task_def_name, not reference_task_name, which is
    # unique per email from Exercise 2 on.
    puts "#{WAIT_TASK_REF} is ready"
    puts 'Before sending the webhook, start the agent tool workers with ' \
         '`bundle exec ruby serve_webhook_agent.rb`, or restart them if you\'ve changed ' \
         'the code since they started.'
    puts "Webhook URL: #{SETTINGS.webhook_endpoint_url}"
  ensure
    task_handler.stop
  end
end

main if $PROGRAM_NAME == __FILE__
