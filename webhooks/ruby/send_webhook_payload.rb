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
    # The same list as the workflow's input, which the WAIT_FOR_WEBHOOK task matches on.
    'user_ids' => Settings::USER_IDS,
    'type' => 'customer',
    # The WAIT_FOR_WEBHOOK task passes this to the AGENT task as its prompt.
    'agent_input' => 'Create an email activity digest. First summarize all stored email ' \
                     'activity. If there is no stored activity, return a concise no-activity ' \
                     'digest. Otherwise, inspect the history of the recipient with the greatest ' \
                     'number of emails before returning your final analysis.',
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
