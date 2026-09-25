package io.orkes.codelab.webhooks.utils;

import io.orkes.codelab.webhooks.Settings;

import org.conductoross.conductor.ai.Agent;
import org.conductoross.conductor.ai.annotations.Tool;
import org.conductoross.conductor.ai.internal.ToolRegistry;

import java.io.IOException;
import java.sql.SQLException;
import java.util.List;
import java.util.Map;

/**
 * Agent definition that is used in the wait-for-webhook example workflow. The agent uses the LLM
 * model and integration from {@link Settings}, and summarizes stored email activity with its tools.
 */
public final class WebhookAgent {

    /** The name the agent is deployed under, which the workflow's AGENT task refers to. */
    public static final String NAME = "webhook_customer_service_" + Settings.LANGUAGE;

    private WebhookAgent() {}

    /** Build the agent definition, checking that the LLM model setting is well formed. */
    public static Agent create() {
        Settings settings = Settings.current();
        String llmModel = settings.llmModel();
        int separator = llmModel.indexOf('/');
        if (separator < 0) {
            throw new IllegalStateException(
                    "CONDUCTOR_AGENT_LLM_MODEL must use the 'provider/model' "
                            + "format, for example 'openai/gpt-5-nano'; got '"
                            + llmModel
                            + "'.");
        }
        String model = llmModel.substring(separator + 1);

        return Agent.builder()
                .name(NAME)
                .model(settings.integrationName() + "/" + model)
                .instructions(
                        "You are an email activity analyst. First call summarize_email_activity. "
                                + "If has_activity is false, do not call "
                                + "get_recipient_email_history; return a concise digest stating "
                                + "that there is no stored email activity. Otherwise, identify the "
                                + "recipient with the greatest email_count, breaking ties by "
                                + "choosing the alphabetically first recipient. Then call "
                                + "get_recipient_email_history with that exact recipient. Base "
                                + "every factual claim on the tool results and return a concise, "
                                + "multi-line activity digest.")
                // Turns each @Tool method of EmailActivityTools into a tool the agent can call.
                .tools(ToolRegistry.fromInstance(new EmailActivityTools()))
                // Enough turns for both tool calls and the final digest, with two to spare.
                .maxTurns(5)
                .temperature(0.2)
                .build();
    }

    /**
     * Read-only database tools for the agent. The serve-agent step runs each tool as a Conductor
     * worker task, and the agent receives the tool's result as JSON.
     */
    public static final class EmailActivityTools {

        // Named explicitly, because @Tool would otherwise use the camelCase method name.
        @Tool(
                name = "summarize_email_activity",
                description =
                        "Return the total number of stored emails and the number sent to each "
                                + "recipient. Call this first.")
        public Map<String, Object> summarizeEmailActivity() throws IOException, SQLException {
            List<Map<String, Object>> recipientActivity = QuerySqliteDb.fetchEmailActivity();
            int totalEmails =
                    recipientActivity.stream()
                            .mapToInt(row -> (Integer) row.get("email_count"))
                            .sum();
            // has_activity tells the agent whether there is any recipient history to look up.
            return Map.of(
                    "total_emails", totalEmails,
                    "has_activity", !recipientActivity.isEmpty(),
                    "recipient_activity", recipientActivity);
        }

        @Tool(
                name = "get_recipient_email_history",
                description =
                        "Return every stored email for one recipient. Pass the exact recipient "
                                + "email address from summarize_email_activity.")
        public Map<String, Object> getRecipientEmailHistory(String recipient)
                throws IOException, SQLException {
            List<Map<String, Object>> emails = QuerySqliteDb.fetchEmails(recipient);
            return Map.of(
                    "recipient", recipient,
                    "email_count", emails.size(),
                    "emails", emails);
        }
    }
}
