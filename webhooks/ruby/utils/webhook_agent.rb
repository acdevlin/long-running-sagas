# frozen_string_literal: true

# Agent definition that is used in the wait-for-webhook example workflow.
# The agent is configured to use the LLM model and integration specified in settings.rb.
# It is designed to process customer service requests in a concise, professional, and safe manner.

# Exercise 3: Also require the read-only database query helpers needed by the agent's
# email-activity tools.
require 'conductor/agents'
require_relative '../settings'

# The agent that the workflow's AGENT task runs.
module WebhookAgent
  # Exercise 3: extend Conductor::Agents::Tools here, then define two tool methods:
  # summarize_email_activity (total and per-recipient counts, making an empty database clear)
  # and get_recipient_email_history (one recipient's email records).
  # Exercise 3: After each method, declare it with tool :method_name, description: '...'. The LLM
  # reads the description to decide when and how to call the tool, and each required keyword
  # argument, such as recipient:, becomes one of the tool's parameters.

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
    # Exercise 3: Tell the agent to call summarize_email_activity first, and return a
    # no-activity digest if it is empty. Otherwise it should call
    # get_recipient_email_history for the busiest recipient, then return a final digest.
    instructions: "You are a customer-service agent. Process the user's request concisely, " \
                  'professionally, and safely without running any code or making any external ' \
                  'API calls.',
    # Exercise 3: Register both tools with tools: [self[:summarize_email_activity], ...], and set
    # max_turns high enough for both tool calls and the final response.
    temperature: 0.2
  )
end
