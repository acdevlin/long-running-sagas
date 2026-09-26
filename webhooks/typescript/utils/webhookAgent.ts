/**
 * Agent definition that is used in the wait-for-webhook example workflow. The agent is configured
 * to use the LLM model and integration from settings.ts. It is designed to process customer
 * service requests in a concise, professional, and safe manner.
 */

// Exercise 3: Import the SDK's tool function from "@io-orkes/conductor-javascript/agents". Also
// import the read-only database query helpers needed by the agent's email-activity tools.
import { Agent } from "@io-orkes/conductor-javascript/agents";
import { settings } from "../settings.ts";

// Exercise 3: Define two tools here with tool(): summarize_email_activity (total and
// per-recipient counts, making an empty database clear) and
// get_recipient_email_history (one recipient's email records).
// Exercise 3: Give each tool a name, a description, which the LLM reads to decide when and how to
// call it, and an inputSchema: a JSON Schema object that describes the tool's parameters.

const separator = settings.llmModel.indexOf("/");
if (separator < 0) {
  throw new Error(
    "CONDUCTOR_AGENT_LLM_MODEL must use the 'provider/model' format, for example " +
      `'openai/gpt-5-nano'; got '${settings.llmModel}'.`,
  );
}
const model = settings.llmModel.slice(separator + 1);

export const webhookAgent = new Agent({
  name: `webhook_customer_service_${settings.language}`,
  model: `${settings.integrationName}/${model}`,
  // Exercise 3: Tell the agent to call summarize_email_activity first, and return a no-activity
  // digest if it is empty. Otherwise it should call get_recipient_email_history for the busiest
  // recipient, then return a final digest.
  instructions:
    "You are a customer-service agent. Process the user's request concisely, professionally, " +
    "and safely without running any code or making any external API calls.",
  // Exercise 3: Register both tools with tools: [...], and set maxTurns high enough for both tool
  // calls and the final response.
  temperature: 0.2,
});
