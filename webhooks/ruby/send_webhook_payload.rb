# frozen_string_literal: true

# Send a webhook payload to the specified Orkes webhook endpoint.

require 'json'
require 'net/http'

require_relative 'settings'

# Send a webhook payload to the Orkes webhook endpoint.
def main
  uri = URI(SETTINGS.webhook_endpoint_url)
  headers = {
    'Content-Type' => 'application/json',
    'Accept' => 'application/json',
    'source' => SETTINGS.source_header
  }

  payload = {
    # Exercise 2: Send user_ids instead, the same list as the workflow's input,
    # to match the WAIT_FOR_WEBHOOK task's rule in the deploy-workflow step.
    'user_id' => Settings::USER_ID,
    'type' => 'customer',
    # Exercise 3: Replace this prompt with a request to summarize stored email
    # activity, inspect the busiest recipient's history, and return a digest.
    'agent_input' => 'Introduce yourself, then inform the user that their email has been sent.',
    # Every language version shares one webhook; this key selects this
    # language's workflow (see the matches in the deploy-workflow step).
    'language' => Settings::LANGUAGE
  }

  response = Net::HTTP.start(uri.host, uri.port, use_ssl: uri.scheme == 'https',
                                                 open_timeout: 30, read_timeout: 30) do |http|
    http.post(uri.request_uri, JSON.generate(payload), headers)
  end

  puts "Status: #{response.code}"
  puts "Response: #{response.body}"

  # Raise an exception for HTTP error responses (for example, 4xx and 5xx).
  response.value

  puts 'Webhook was accepted by Orkes Conductor.'
end

main if $PROGRAM_NAME == __FILE__
