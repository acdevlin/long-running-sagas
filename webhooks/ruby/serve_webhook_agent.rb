# frozen_string_literal: true

# Serve the local database tools used by the post-webhook agent.

require 'conductor'
require 'conductor/agents'

require_relative 'utils/webhook_agent'

# Deploy the agent and serve its tool workers until interrupted.
def main
  runtime = Conductor::Agents::AgentRuntime.new(configuration: Conductor::Configuration.new)
  # Deploys the agent and starts its tool workers without waiting. When serve waits itself, Ruby
  # reports a deadlock if the agent has no tools, as before Exercise 3, so this step waits instead.
  runtime.serve(WebhookAgent::AGENT, blocking: false)

  puts "Serving the agent's tool workers. Press Ctrl+C to stop."
  begin
    sleep
  rescue Interrupt
    # Ctrl+C stops the step.
  end
ensure
  runtime&.shutdown
end

main if $PROGRAM_NAME == __FILE__
