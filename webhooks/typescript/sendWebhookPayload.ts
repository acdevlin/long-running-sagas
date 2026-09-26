/** Send a webhook payload to the specified Orkes webhook endpoint. */

import { settings } from "./settings.ts";

async function main(): Promise<void> {
  const payload = {
    // Exercise 2: Send user_ids instead, the same list as the workflow's input,
    // to match the WAIT_FOR_WEBHOOK task's rule in the deploy-workflow step.
    user_id: settings.userId,
    type: "customer",
    // Exercise 3: Replace this prompt with a request to summarize stored email
    // activity, inspect the busiest recipient's history, and return a digest.
    agent_input: "Introduce yourself, then inform the user that their email has been sent.",
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
