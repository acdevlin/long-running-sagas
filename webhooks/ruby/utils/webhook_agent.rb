# frozen_string_literal: true

# Agent definition that is used in the wait-for-webhook example workflow.
# The agent is configured to use the LLM model and integration specified in settings.rb,
# and summarizes stored email activity with its tools.

require 'conductor/agents'
require_relative '../settings'
require_relative 'query_sqlite_db'

# The agent that the workflow's AGENT task runs.
module WebhookAgent
  # Read-only database tools for the agent. serve_webhook_agent.rb runs each tool as a Conductor
  # worker task, and the agent receives the tool's result as JSON.
  extend Conductor::Agents::Tools

  # The ** ignores extra task input, such as _createdBy, which the SDK passes to a tool that has
  # no parameters.
  def summarize_email_activity(**)
    recipient_activity = QuerySqliteDb.fetch_email_activity
    {
      'total_emails' => recipient_activity.sum { |row| row['email_count'] },
      # has_activity tells the agent whether there is any recipient history to look up.
      'has_activity' => !recipient_activity.empty?,
      'recipient_activity' => recipient_activity
    }
  end
  tool :summarize_email_activity,
       description: 'Return the total number of stored emails and the number sent to each ' \
                    'recipient. Call this first.'

  def get_recipient_email_history(recipient:)
    # Trim so a padded address still matches, and reject a missing or blank one, which can never
    # succeed. This SDK can't stop Conductor retrying a failed tool call.
    recipient = recipient.to_s.strip
    raise ArgumentError, 'A recipient email address is required' if recipient.empty?

    emails = QuerySqliteDb.fetch_emails(recipient: recipient)
    { 'recipient' => recipient, 'email_count' => emails.size, 'emails' => emails }
  end
  tool :get_recipient_email_history,
       description: 'Return every stored email for one recipient. Pass the exact recipient ' \
                    'email address from summarize_email_activity.',
       # The SDK gives a required keyword argument no type in the schema, so this one states it.
       input_schema: {
         'type' => 'object',
         'properties' => { 'recipient' => { 'type' => 'string' } },
         'required' => ['recipient']
       }

  # The name the agent is deployed under, which the workflow's AGENT task refers to.
  NAME = "webhook_customer_service_#{Settings::LANGUAGE}".freeze

  unless SETTINGS.llm_model.include?('/')
    raise ArgumentError, "CONDUCTOR_AGENT_LLM_MODEL must use the 'provider/model' format, for " \
                         "example 'openai/gpt-5-nano'; got #{SETTINGS.llm_model.inspect}."
  end
  _, model = SETTINGS.llm_model.split('/', 2)

  AGENT = Conductor::Agents::Agent.new(
    name: NAME,
    model: "#{SETTINGS.integration_name}/#{model}",
    instructions: 'You are an email activity analyst. First call summarize_email_activity. If ' \
                  'has_activity is false, do not call get_recipient_email_history; return a ' \
                  'concise digest stating that there is no stored email activity. Otherwise, ' \
                  'identify the recipient with the greatest email_count, breaking ties by ' \
                  'choosing the alphabetically first recipient. Then call ' \
                  'get_recipient_email_history with that exact recipient. Base every factual ' \
                  'claim on the tool results and return a concise, multi-line activity digest.',
    tools: [self[:summarize_email_activity], self[:get_recipient_email_history]],
    # Enough turns for both tool calls and the final digest, with two to spare.
    max_turns: 5,
    temperature: 0.2
  )
end
