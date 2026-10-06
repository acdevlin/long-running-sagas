/** Send a webhook payload to the specified Orkes webhook endpoint. */

import { settings } from "./settings.ts";

async function main(): Promise<void> {
  const payload = {
    // The same list as the workflow's input, which the WAIT_FOR_WEBHOOK task matches on.
    user_ids: settings.userIds,
    type: "customer",
    // The WAIT_FOR_WEBHOOK task passes this to the AGENT task as its prompt.
    agent_input:
      "Create an email activity digest. First summarize all stored email activity. If there " +
      "is no stored activity, return a concise no-activity digest. Otherwise, inspect the " +
      "history of the recipient with the greatest number of emails before returning your " +
      "final analysis.",
    // Every language version shares one webhook; this key selects this
    // language's workflow (see the matches in the deploy-workflow step).
    language: settings.language,
  };

  const response = await fetch(settings.webhookEndpointUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      source: settings.sourceHeader,
    },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(30_000),
  });

  console.log(`Status: ${response.status}`);
  console.log(`Response: ${await response.text()}`);

  // Throw an error for HTTP error responses (for example, 4xx and 5xx).
  if (!response.ok) {
    throw new Error(`Webhook request failed with status ${response.status}`);
  }

  console.log("Webhook was accepted by Orkes Conductor.");
}

await main();
