package io.orkes.codelab.webhooks;

import io.orkes.codelab.webhooks.utils.WebhookAgent;

import org.conductoross.conductor.ai.AgentRuntime;

/** Serve the local database tools used by the post-webhook agent. */
public final class ServeWebhookAgent {

    private ServeWebhookAgent() {}

    /** Deploy the agent and serve its tool workers until interrupted. */
    public static int run() {
        try (var runtime = new AgentRuntime(Settings.current().createApiClient())) {
            System.out.println("Serving the agent's tool workers. Press Ctrl+C to stop.");
            // Blocks until the process is stopped; the SDK stops the workers cleanly on Ctrl+C.
            runtime.serve(WebhookAgent.create());
        }
        return 0;
    }
}
