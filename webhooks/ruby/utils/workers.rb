# frozen_string_literal: true

# Worker tasks used by the webhook workflow. Requiring this file registers each worker_task method,
# and the deploy-workflow step's TaskHandler then polls for their tasks.

require 'conductor'

# The workflow's workers. The SDK fills each method's keyword arguments from the task input of the
# same name.
module Workers
  extend Conductor::Worker::Annotatable

  worker_task 'get_user_email'
  # Exercise 2: Change to "get_user_emails", taking a list of user_ids. Return the fork's
  # send_email tasks, each of type "SIMPLE" with a unique taskReferenceName (Exercise 3
  # repeats a user_id), and a Hash mapping each taskReferenceName to that task's input.
  # Return the email address associated with a user, which the SDK stores as the output "result".
  def self.get_user_email(user_id:)
    "#{user_id}@example.com"
  end

  # Exercise 2: Pass thread_count to worker_task, which is 1 by default, so this worker sends the
  # forked emails in parallel.
  worker_task 'send_email'
  # Simulate sending an email.
  def self.send_email(recipients:, subject:, body:)
    puts "Sending email\nTo: #{recipients}\nSubject: #{subject}\nBody: #{body}"
    # Exercise 1: Return this email's fields for the emails table as a Hash, with sent_time as a
    # Unix timestamp in seconds.
    nil
  end
end
