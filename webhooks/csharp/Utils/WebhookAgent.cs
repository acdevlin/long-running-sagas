using Conductor.AI;

namespace WebhooksCodelab.Utils;

// Exercise 3: Define two tools here as public [Tool] methods on a non-static class:
// summarize_email_activity (total and per-recipient counts, making an empty database clear)
// and get_recipient_email_history (one recipient's email records).
// Exercise 3: Tools can be async. [Tool] names each after its method in snake_case, so set
// [Tool(Name = ...)] to drop an Async suffix. Also set Description, which the LLM reads to decide
// when and how to call the tool; it is the only place to explain the tool's parameters.

/// <summary>
/// Agent definition that is used in the wait-for-webhook example workflow. The
/// agent is configured to use the LLM model and integration from
/// <see cref="Settings"/>. It is designed to process customer service requests
/// in a concise, professional, and safe manner.
/// </summary>
public static class WebhookAgent
{
    // Built on first use rather than in a static initializer, which would wrap
    // Create's error about a malformed model setting in a TypeInitializationException.
    private static readonly Lazy<Agent> LazyAgent = new(Create);

    public static Agent Agent => LazyAgent.Value;

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
            // Exercise 3: Tell the agent to call summarize_email_activity first, and return a
            // no-activity digest if it is empty. Otherwise it should call get_recipient_email_history
            // for the busiest recipient, then return a final digest.
            Instructions =
                "You are a customer-service agent. Process the user's request concisely, professionally, " +
                "and safely without running any code or making any external API calls.",
            // Exercise 3: Set Tools with ToolRegistry.FromInstance, which builds them from your class,
            // and MaxTurns high enough for both tool calls and the final response.
            Temperature = 0.2,
        };
    }
}
