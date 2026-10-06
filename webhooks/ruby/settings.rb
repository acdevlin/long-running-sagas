# frozen_string_literal: true

# Settings for the Ruby version of the webhooks codelab.
#
# Account-specific values are read from environment variables so that every language version of
# this codelab shares one configuration. Copy .env.example at the repository root to .env and
# fill it in; it is loaded automatically below. Variables already exported in your shell take
# precedence over the ones in .env, for example:
#
#   export CONDUCTOR_AGENT_LLM_MODEL=anthropic/claude-sonnet-4-6
#   export CONDUCTOR_INTEGRATION_NAME=my_anthropic_integration

require 'dotenv'

REPOSITORY_ROOT = File.expand_path('../..', __dir__)

# Load before any Conductor configuration is created so the SDK also picks up
# CONDUCTOR_SERVER_URL, CONDUCTOR_AUTH_KEY and CONDUCTOR_AUTH_SECRET from .env.
Dotenv.load(File.join(REPOSITORY_ROOT, '.env'))

# The account-specific values, read from the shell or .env.
class Settings
  # Identifies this language version in its workflow and agent names and in the webhook
  # payload, so every language version can share one webhook.
  LANGUAGE = 'ruby'

  # The workflow sends an email to each user ID in this list. Repeating "alex" gives the
  # agent a clear most-active recipient to identify from the stored email activity.
  USER_IDS = %w[alex alex alex user_1 user_2 user_555].freeze

  attr_reader :conductor_server_url, :llm_model, :integration_name, :webhook_id, :source_header

  def initialize
    # Set CONDUCTOR_SERVER_URL in .env; the webhook URL is derived from it.
    @conductor_server_url = read('CONDUCTOR_SERVER_URL', 'https://developer.orkescloud.com/api')
    # Set CONDUCTOR_AGENT_LLM_MODEL in .env to use a different model.
    @llm_model = read('CONDUCTOR_AGENT_LLM_MODEL', 'openai/gpt-5-nano')
    # Set CONDUCTOR_INTEGRATION_NAME in .env.
    @integration_name = read('CONDUCTOR_INTEGRATION_NAME', 'your_integration_name_here')
    # Set WEBHOOK_ID in .env.
    @webhook_id = read('WEBHOOK_ID', 'your_webhook_id_here')
    # Set WEBHOOK_SOURCE_HEADER in .env.
    @source_header = read('WEBHOOK_SOURCE_HEADER', 'your_source_header_here')
  end

  # Conductor cluster URL without its /api suffix, shared by the UI and webhooks.
  def server_base_url
    conductor_server_url.sub(%r{/+\z}, '').delete_suffix('/api')
  end

  # Webhook endpoint on the same Conductor cluster as the API.
  def webhook_endpoint_url
    "#{server_base_url}/webhook/#{webhook_id}"
  end

  private

  # Return a variable from the shell or .env, treating an empty value as unset.
  def read(name, default_value)
    value = ENV.fetch(name, '').strip
    value.empty? ? default_value : value
  end
end

SETTINGS = Settings.new.freeze
