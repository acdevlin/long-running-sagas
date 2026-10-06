# frozen_string_literal: true

require 'conductor'

# DYNAMIC_FORK task, which runs one branch per task definition it receives at runtime, and the
# JOIN task that must follow it. The SDK's dynamic_fork doesn't set up the task the way the server
# expects, and its workflow builder has no JOIN task of its own.
#
# @example
#   fork = DynamicForkTask.build(
#     'send_emails_fork',
#     tasks: '${get_user_emails_ref.output.dynamicTasks}',
#     tasks_inputs: '${get_user_emails_ref.output.dynamicTasksInputs}'
#   )
#   join = DynamicForkTask.join('send_emails_join')
module DynamicForkTask
  # The input parameters that hold the forked task definitions and their inputs.
  TASKS_PARAM = 'dynamicTasks'
  TASKS_INPUTS_PARAM = 'dynamicTasksInputs'

  # @param tasks [String] expression for the list of task definitions to fork, each a Hash with
  #   a "name", a unique "taskReferenceName" and a "type" ("SIMPLE" for a worker task)
  # @param tasks_inputs [String] expression for a Hash that maps each forked task's
  #   "taskReferenceName" to that task's input
  # @return [Conductor::Http::Models::WorkflowTask]
  def self.build(task_reference_name, tasks:, tasks_inputs:)
    Conductor::Http::Models::WorkflowTask.new(
      name: task_reference_name,
      task_reference_name: task_reference_name,
      type: Conductor::Workflow::TaskType::FORK_JOIN_DYNAMIC,
      input_parameters: { TASKS_PARAM => tasks, TASKS_INPUTS_PARAM => tasks_inputs },
      dynamic_fork_tasks_param: TASKS_PARAM,
      dynamic_fork_tasks_input_param_name: TASKS_INPUTS_PARAM
    )
  end

  # A JOIN task that waits for every branch of the fork before it to finish.
  # @return [Conductor::Http::Models::WorkflowTask]
  def self.join(task_reference_name)
    Conductor::Http::Models::WorkflowTask.new(
      name: task_reference_name,
      task_reference_name: task_reference_name,
      type: Conductor::Workflow::TaskType::JOIN,
      join_on: []
    )
  end
end
