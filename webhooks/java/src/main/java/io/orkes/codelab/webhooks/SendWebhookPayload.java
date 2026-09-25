package io.orkes.codelab.webhooks;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;

/** Send a webhook payload to the specified Orkes webhook endpoint. */
public final class SendWebhookPayload {

    private SendWebhookPayload() {}

    public static int run() throws IOException, InterruptedException {
        Settings settings = Settings.current();

        Map<String, Object> payload = new LinkedHashMap<>();
        // The same list as the workflow's input, which the WAIT_FOR_WEBHOOK task matches on.
        payload.put("user_ids", Settings.USER_IDS);
        payload.put("type", "customer");
        // The WAIT_FOR_WEBHOOK task passes this to the AGENT task as its prompt.
        payload.put(
                "agent_input",
                "Create an email activity digest. First summarize all stored email activity. If "
                        + "there is no stored activity, return a concise no-activity digest. "
                        + "Otherwise, inspect the history of the recipient with the greatest "
                        + "number of emails before returning your final analysis.");
        // Every language version shares one webhook; this key selects this
        // language's workflow (see the matches in the deploy-workflow step).
        payload.put("language", Settings.LANGUAGE);

        HttpRequest request =
                HttpRequest.newBuilder(URI.create(settings.webhookEndpointUrl()))
                        .timeout(Duration.ofSeconds(30))
                        .header("Content-Type", "application/json")
                        .header("Accept", "application/json")
                        .header("source", settings.sourceHeader())
                        .POST(
                                HttpRequest.BodyPublishers.ofString(
                                        new ObjectMapper().writeValueAsString(payload)))
                        .build();

        try (HttpClient client = HttpClient.newHttpClient()) {
            HttpResponse<String> response =
                    client.send(request, HttpResponse.BodyHandlers.ofString());

            System.out.println("Status: " + response.statusCode());
            System.out.println("Response: " + response.body());

            // Throw an exception for HTTP error responses (for example, 4xx and 5xx).
            if (response.statusCode() >= 400) {
                throw new IOException(
                        "Webhook request failed with status " + response.statusCode());
            }
        }

        System.out.println("Webhook was accepted by Orkes Conductor.");
        return 0;
    }
}
