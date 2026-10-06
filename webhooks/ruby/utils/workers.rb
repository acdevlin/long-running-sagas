# frozen_string_literal: true

# Worker tasks used by the webhook workflow. Requiring this file registers each worker_task method,
# and the deploy-workflow step's TaskHandler then polls for their tasks.

require 'conductor'

# The workflow's workers. The SDK fills each method's keyword arguments from the task input of the
# same name.
module Workers
  extend Conductor::Worker::Annotatable

  # These shared names keep the worker's output synchronized with the workflow definition that
  # reads it in the deploy-workflow step.
  DYNAMIC_TASKS_PARAM = 'dynamicTasks'
  DYNAMIC_TASKS_INPUTS_PARAM = 'dynamicTasksInputs'
  SEND_EMAIL_TASK_NAME = 'send_email'

  worker_task 'get_user_emails'
  # Return one send_email task per user's email address, for the workflow's dynamic fork.
  def self.get_user_emails(user_ids:, subject:, body:)
    valid_list = user_ids.is_a?(Array) && !user_ids.empty?
    raise ArgumentError, 'At least one user ID is required' unless valid_list

    dynamic_tasks = []
    dynamic_tasks_inputs = {}
    user_ids.each_with_index do |user_id, index|
      valid_id = user_id.is_a?(String) && !user_id.strip.empty?
      raise ArgumentError, "Invalid user ID at index #{index}" unless valid_id

      # The index keeps each reference name unique, even when a user ID repeats.
      task_reference_name = "send_email_#{index}"
      dynamic_tasks << {
        'name' => SEND_EMAIL_TASK_NAME,
        'taskReferenceName' => task_reference_name,
        'type' => 'SIMPLE'
      }
      dynamic_tasks_inputs[task_reference_name] = {
        'recipients' => "#{user_id}@example.com", 'subject' => subject, 'body' => body
      }
    end
    { DYNAMIC_TASKS_PARAM => dynamic_tasks, DYNAMIC_TASKS_INPUTS_PARAM => dynamic_tasks_inputs }
  end

  # A thread count above the default of 1 lets this worker send the forked emails in parallel.
  worker_task SEND_EMAIL_TASK_NAME, thread_count: 10
  # Simulate sending an email.
  def self.send_email(recipients:, subject:, body:)
    puts "Sending email\nTo: #{recipients}\nSubject: #{subject}\nBody: #{body}"
    { 'sent_time' => Time.now.to_i, 'subject' => subject, 'recipients' => recipients }
  end
end
