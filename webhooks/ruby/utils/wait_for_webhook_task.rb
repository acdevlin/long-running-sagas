# frozen_string_literal: true

require 'conductor'

# WAIT_FOR_WEBHOOK task, which suspends the workflow until a webhook payload arrives that meets
# every match rule. Each rule maps a JSONPath into the payload to the value it must have.
module WaitForWebhookTask
  # @return [Conductor::Http::Models::WorkflowTask]
  def self.build(task_reference_name, matches:)
    Conductor::Http::Models::WorkflowTask.new(
      name: task_reference_name,
      task_reference_name: task_reference_name,
      type: Conductor::Workflow::TaskType::WAIT_FOR_WEBHOOK,
      input_parameters: { 'matches' => matches }
    )
  end
end
