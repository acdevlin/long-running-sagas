using Conductor.AI;

namespace WebhooksCodelab.Utils;

// Exercise 3: Define two tools here as public methods marked with [Tool] on a
// non-static class, with the following uses. [Tool] names each tool after its
// method in snake_case, so SummarizeEmailActivity becomes summarize_email_activity.
// 1) summarize_email_activity: Return total and per-recipient email counts.
// Make it clear when no records exist so the agent can skip the recipient-history lookup.
// 2) get_recipient_email_history: return one recipient's email records.

/// <summary>
/// Agent definition that is used in the wait-for-webhook example workflow. The
/// agent is configured to use the LLM model and integration from
/// <see cref="Settings"/>. It is designed to process customer service requests
/// in a concise, professional, and safe manner.
/// </summary>
public static class WebhookAgent
{
    public static Agent Agent { get; } = Create();

    private static Agent Create()
    {
        var llmModel = Settings.Current.LlmModel;
        var separator = llmModel.IndexOf('/');
        if (separator < 0)
        {
            throw new InvalidOperationException(
                "Settings.LlmModel must use the 'provider/model' format, for example " +
                $"'openai/gpt-5-nano'; got '{llmModel}'.");
        }
        var model = llmModel[(separator + 1)..];

        return new Agent($"webhook_customer_service_{Settings.Current.Language}")
        {
            Model = $"{Settings.Current.IntegrationName}/{model}",
            // Exercise 3: Tell the agent to call summarize_email_activity first.
            // If the summary is empty, it should return a no-activity digest.
            // Otherwise, it should find the busiest recipient, call
            // get_recipient_email_history for that recipient, and return a final digest.
            // Register both tools (ToolRegistry.FromInstance builds them from your class)
            // and allow enough turns (MaxTurns) for both calls and the response.
            Instructions =
                "You are a customer-service agent. Process the user's request concisely, professionally, " +
                "and safely without running any code or making any external API calls.",
            Temperature = 0.2,
        };
    }
}
