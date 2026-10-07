/**
 * Agent definition that is used in the wait-for-webhook example workflow. The agent is configured
 * to use the LLM model and integration from settings.ts, and summarizes stored email activity
 * with its tools.
 */

import { Agent, TerminalToolError, tool } from "@io-orkes/conductor-javascript/agents";
import { settings } from "../settings.ts";
import { fetchEmailActivity, fetchEmails } from "./querySqliteDb.ts";

// Read-only database tools for the agent. The serve-agent step runs each tool as a Conductor
// worker task, and the agent receives the tool's result as JSON.
const summarizeEmailActivity = tool(
  async () => {
    const recipientActivity = fetchEmailActivity();
    // Each row's email_count is a number, although its type is SQLOutputValue.
    const totalEmails = recipientActivity.reduce(
      (total, row) => total + (row["email_count"] as number),
      0,
    );
    // has_activity tells the agent whether there is any recipient history to look up.
    return {
      total_emails: totalEmails,
      has_activity: recipientActivity.length > 0,
      recipient_activity: recipientActivity,
    };
  },
  {
    name: "summarize_email_activity",
    description:
      "Return the total number of stored emails and the number sent to each recipient. " +
      "Call this first.",
    inputSchema: { type: "object", properties: {} },
  },
);

const getRecipientEmailHistory = tool(
  async ({ recipient }: { recipient: string }) => {
    // Trim so a padded address still matches. A missing or blank one can never succeed, so fail
    // at once instead of letting Conductor retry the task.
    if (typeof recipient !== "string" || recipient.trim() === "") {
      throw new TerminalToolError("A recipient email address is required");
    }
    const trimmedRecipient = recipient.trim();
    const emails = fetchEmails(trimmedRecipient);
    return { recipient: trimmedRecipient, email_count: emails.length, emails };
  },
  {
    name: "get_recipient_email_history",
    description:
      "Return every stored email for one recipient. Pass the exact recipient email address " +
      "from summarize_email_activity.",
    inputSchema: {
      type: "object",
      properties: { recipient: { type: "string" } },
      required: ["recipient"],
    },
  },
);

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
  instructions:
    "You are an email activity analyst. First call summarize_email_activity. If has_activity " +
    "is false, do not call get_recipient_email_history; return a concise digest stating that " +
    "there is no stored email activity. Otherwise, identify the recipient with the greatest " +
    "email_count, breaking ties by choosing the alphabetically first recipient. Then call " +
    "get_recipient_email_history with that exact recipient. Base every factual claim on the " +
    "tool results and return a concise, multi-line activity digest.",
  tools: [summarizeEmailActivity, getRecipientEmailHistory],
  // Enough turns for both tool calls and the final digest, with two to spare.
  maxTurns: 5,
  temperature: 0.2,
});
