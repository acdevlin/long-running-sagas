package io.orkes.codelab.webhooks.utils;

import io.orkes.codelab.webhooks.Settings;

import org.conductoross.conductor.ai.Agent;

// Exercise 3: Define two tools as public @Tool methods on a class of their own:
// summarize_email_activity (total and per-recipient counts, making an empty database clear)
// and get_recipient_email_history (one recipient's email records).
// Exercise 3: @Tool names a tool after its method as written, so set name to the snake_case
// name. Also set description, which the LLM reads to decide when and how to call the tool.

/**
 * Agent definition that is used in the wait-for-webhook example workflow. The agent uses the LLM
 * model and integration from {@link Settings}, and processes customer service requests concisely.
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
                // Exercise 3: Tell the agent to call summarize_email_activity first, and return a
                // no-activity digest if it is empty. Otherwise, it should call
                // get_recipient_email_history for the busiest recipient, then write a final digest.
                .instructions(
                        "You are a customer-service agent. Process the user's request "
                                + "concisely, professionally, and safely without running any "
                                + "code or making any external API calls.")
                // Exercise 3: Pass .tools(ToolRegistry.fromInstance(new YourTools())), and set
                // .maxTurns high enough for both tool calls and the final response.
                .temperature(0.2)
                .build();
    }
}
