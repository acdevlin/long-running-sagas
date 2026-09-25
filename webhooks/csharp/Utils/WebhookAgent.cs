using System.Text.Json.Serialization;
using Conductor.AI;

namespace WebhooksCodelab.Utils;

/// <summary>The email activity agent, using the LLM model and integration from <see cref="Settings"/>.</summary>
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
            // The field names here are the JSON names of the tools' results, which match
            // the Python version's, so both languages give the agent the same instructions.
            Instructions =
                "You are an email activity analyst. First call summarize_email_activity. " +
                "If has_activity is false, do not call get_recipient_email_history; return " +
                "a concise digest stating that there is no stored email activity. Otherwise, " +
                "identify the recipient with the greatest email_count, breaking ties by " +
                "choosing the alphabetically first recipient. Then call " +
                "get_recipient_email_history with that exact recipient. Base every factual " +
                "claim on the tool results and return a concise, multi-line activity digest.",
            // Turns each [Tool] method into a tool the agent can call. FromInstance needs an
            // object, but it also registers static methods such as these stateless tools.
            Tools = ToolRegistry.FromInstance(new EmailActivityTools()),
            // Enough turns for both tool calls and the final digest, with two to spare.
            MaxTurns = 5,
            Temperature = 0.2,
        };
    }
}

/// <summary>
/// Read-only database tools for the agent. The serve-agent step runs each tool as a
/// Conductor worker task, and the agent receives the tool's result as JSON.
/// </summary>
public sealed class EmailActivityTools
{
    // Named explicitly because [Tool] would otherwise derive each name from the
    // method's name, which would include its Async suffix.
    [Tool(
        Name = "summarize_email_activity",
        Description = "Return the total number of stored emails and the number sent to each recipient. Call this first.")]
    public static async Task<EmailActivitySummary> SummarizeEmailActivityAsync()
    {
        // SQLite has already grouped and sorted these rows, so the summary only needs
        // to add up their counts, without loading every stored email.
        return new EmailActivitySummary(await QuerySqliteDb.FetchEmailActivityAsync());
    }

    [Tool(
        Name = "get_recipient_email_history",
        Description = "Return every stored email for one recipient. Pass the exact recipient email address from summarize_email_activity.")]
    public static async Task<RecipientEmailHistory> GetRecipientEmailHistoryAsync(string recipient)
    {
        // A blank recipient can never succeed, so fail at once instead of letting
        // Conductor retry the task, as it does for other exceptions.
        if (string.IsNullOrWhiteSpace(recipient))
        {
            throw new TerminalToolException("A recipient email address is required");
        }

        recipient = recipient.Trim();
        return new RecipientEmailHistory(recipient, await QuerySqliteDb.FetchEmailsAsync(recipient));
    }
}

/// <summary>
/// Result of summarize_email_activity. Its JSON names and field order match the
/// Python version's, instead of the camelCase names that the SDK uses by default.
/// </summary>
public sealed record EmailActivitySummary(
    [property: JsonPropertyName("recipient_activity"), JsonPropertyOrder(1)]
    IReadOnlyList<Dictionary<string, object?>> RecipientActivity)
{
    // SQLite returns each COUNT(*) as a long.
    [JsonPropertyName("total_emails")]
    public long TotalEmails => RecipientActivity.Sum(row => (long)row["email_count"]!);

    // Tells the agent whether there is any recipient history to look up.
    [JsonPropertyName("has_activity")]
    public bool HasActivity => RecipientActivity.Count > 0;
}

/// <summary>Result of get_recipient_email_history, with JSON like <see cref="EmailActivitySummary"/>'s.</summary>
public sealed record RecipientEmailHistory(
    [property: JsonPropertyName("recipient")] string Recipient,
    [property: JsonPropertyName("emails"), JsonPropertyOrder(1)] IReadOnlyList<Dictionary<string, object?>> Emails)
{
    [JsonPropertyName("email_count")]
    public int EmailCount => Emails.Count;
}
