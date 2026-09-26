/**
 * Settings for the TypeScript version of the webhooks codelab.
 *
 * Account-specific values are read from environment variables so that every language version of
 * this codelab shares one configuration. Copy `.env.example` at the repository root to `.env` and
 * fill it in; it is loaded automatically below. Variables already exported in your shell take
 * precedence over the ones in `.env`, for example:
 *
 *     export CONDUCTOR_AGENT_LLM_MODEL=anthropic/claude-sonnet-4-6
 *     export CONDUCTOR_INTEGRATION_NAME=my_anthropic_integration
 */

import { existsSync } from "node:fs";
import path from "node:path";

const ENV_PATH = path.resolve(import.meta.dirname, "..", "..", ".env");

// Load before any Conductor client is created so the SDK also picks up CONDUCTOR_SERVER_URL,
// CONDUCTOR_AUTH_KEY and CONDUCTOR_AUTH_SECRET from .env.
if (existsSync(ENV_PATH)) {
  process.loadEnvFile(ENV_PATH);
}

/** Return a variable from the shell or .env, treating an empty value as unset. */
function read(name: string, defaultValue: string): string {
  return process.env[name]?.trim() || defaultValue;
}

class Settings {
  // Set CONDUCTOR_SERVER_URL in .env; the webhook URL is derived from it.
  readonly conductorServerUrl = read(
    "CONDUCTOR_SERVER_URL",
    "https://developer.orkescloud.com/api",
  );
  // Set CONDUCTOR_AGENT_LLM_MODEL in .env to use a different model.
  readonly llmModel = read("CONDUCTOR_AGENT_LLM_MODEL", "openai/gpt-5-nano");
  // Set CONDUCTOR_INTEGRATION_NAME in .env.
  readonly integrationName = read("CONDUCTOR_INTEGRATION_NAME", "your_integration_name_here");
  // Identifies this language version in its workflow and agent names and in the webhook payload,
  // so every language version can share one webhook.
  readonly language = "typescript";
  // Set WEBHOOK_ID in .env.
  readonly webhookId = read("WEBHOOK_ID", "your_webhook_id_here");
  // Set WEBHOOK_SOURCE_HEADER in .env.
  readonly sourceHeader = read("WEBHOOK_SOURCE_HEADER", "your_source_header_here");
  // Exercise 2: Replace userId with a list of user IDs, such as userIds, so that the workflow
  // sends an email to each user ID in the list.
  // Exercise 3: Repeat one user ID so the agent has a clear most-active
  // recipient to identify from the stored email activity.
  readonly userId = "user_12345";

  /** Conductor cluster URL without its /api suffix, shared by the UI and webhooks. */
  get serverBaseUrl(): string {
    const url = this.conductorServerUrl.replace(/\/+$/, "");
    return url.endsWith("/api") ? url.slice(0, -"/api".length) : url;
  }

  /** Webhook endpoint on the same Conductor cluster as the API. */
  get webhookEndpointUrl(): string {
    return `${this.serverBaseUrl}/webhook/${this.webhookId}`;
  }
}

export const settings = new Settings();
