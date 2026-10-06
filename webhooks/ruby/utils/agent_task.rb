# frozen_string_literal: true

require 'conductor'

# AGENT task that invokes a deployed Conductor agent. The SDK has no AGENT task, so this creates
# the task definition that the server expects.
module AgentTask
  # @return [Conductor::Http::Models::WorkflowTask]
  def self.build(task_reference_name, agent_name:, prompt:)
    Conductor::Http::Models::WorkflowTask.new(
      name: 'invoke_agent',
      task_reference_name: task_reference_name,
      type: 'AGENT',
      input_parameters: {
        # Run the agent deployed to this Conductor cluster under agent_name. The
        # default agentType, "a2a", calls an external A2A agent instead.
        'agentType' => 'conductor',
        'name' => agent_name,
        'prompt' => prompt,
        # How often, in seconds, the task checks on the agent, and how long the
        # agent may run before the task fails and Conductor cancels the agent.
        'pollIntervalSeconds' => 5,
        'maxDurationSeconds' => 300
      }
    )
  end
end
