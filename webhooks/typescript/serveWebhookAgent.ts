/** Serve the local database tools used by the post-webhook agent. */

import { AgentRuntime } from "@io-orkes/conductor-javascript/agents";
import { webhookAgent } from "./utils/webhookAgent.ts";

/** Deploy the agent and serve its tool workers until interrupted. */
async function main(): Promise<void> {
  const runtime = new AgentRuntime();
  try {
    console.log("Serving the agent's tool workers. Press Ctrl+C to stop.");
    // Resolves once Ctrl+C has stopped the workers.
    await runtime.serve(webhookAgent);
  } finally {
    // Also stops the background token refresh of the client the runtime created, which would
    // otherwise keep this process running.
    await runtime.client.close();
  }
}

await main();
