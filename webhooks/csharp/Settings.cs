using Conductor.Client;
using Conductor.Client.Authentication;
using DotNetEnv;

namespace WebhooksCodelab;

/// <summary>
/// Settings for the C# version of the webhooks codelab.
///
/// Account-specific values are read from environment variables so that every
/// language version of this codelab shares one configuration. Copy
/// <c>.env.example</c> at the repository root to <c>.env</c> and fill it in; it
/// is loaded automatically below. Variables already exported in your shell take
/// precedence over the ones in <c>.env</c>.
/// </summary>
public sealed class Settings
{
    // Set CONDUCTOR_SERVER_URL in .env; the webhook URL is derived from it.
    public string ConductorServerUrl { get; init; } = "https://developer.orkescloud.com/api";
    // Set CONDUCTOR_AUTH_KEY and CONDUCTOR_AUTH_SECRET in .env. Settings is a class
    // rather than a record, because a record's generated ToString() prints the secret.
    public string? AuthKey { get; init; }
    public string? AuthSecret { get; init; }
    // Set CONDUCTOR_AGENT_LLM_MODEL in .env to use a different model.
    public string LlmModel { get; init; } = "openai/gpt-5-nano";
    // Set CONDUCTOR_INTEGRATION_NAME in .env.
    public string IntegrationName { get; init; } = "your_integration_name_here";
    // Identifies this language version in its workflow and agent names and in
    // the webhook payload, so every language version can share one webhook.
    public string Language { get; init; } = "csharp";
    // Set WEBHOOK_ID in .env.
    public string WebhookId { get; init; } = "your_webhook_id_here";
    // Set WEBHOOK_SOURCE_HEADER in .env.
    public string SourceHeader { get; init; } = "your_source_header_here";
    // The workflow sends one email to each user ID in this list, in parallel. A
    // read-only list keeps every step using the same recipients, in the same order.
    public IReadOnlyList<string> UserIds { get; init; } =
    [
        // Repeats give the agent a clear most-active recipient to identify.
        "alex", "alex", "alex",
        "user_1", "user_2", "user_555",
    ];

    public static Settings Current { get; } = FromEnv();

    /// <summary>Conductor cluster URL without its /api suffix, shared by the UI and webhooks.</summary>
    public string ServerBaseUrl
    {
        get
        {
            var url = ConductorServerUrl.TrimEnd('/');
            return url.EndsWith("/api", StringComparison.Ordinal) ? url[..^"/api".Length] : url;
        }
    }

    /// <summary>Webhook endpoint on the same Conductor cluster as the API.</summary>
    public string WebhookEndpointUrl => $"{ServerBaseUrl}/webhook/{WebhookId}";

    /// <summary>
    /// Build the SDK connection settings. Unlike the Python SDK, the C# SDK does
    /// not read the CONDUCTOR_* variables itself.
    /// </summary>
    public Configuration CreateConductorConfiguration()
    {
        var configuration = new Configuration { BasePath = ConductorServerUrl };
        if (!string.IsNullOrEmpty(AuthKey) && !string.IsNullOrEmpty(AuthSecret))
        {
            configuration.AuthenticationSettings = new OrkesAuthenticationSettings(AuthKey, AuthSecret);
        }
        return configuration;
    }

    /// <summary>Build settings from the defaults above, applying any env overrides.</summary>
    private static Settings FromEnv()
    {
        // Search upwards from the current folder for the .env at the repository
        // root, without overwriting variables already exported in your shell.
        Env.NoClobber().TraversePath().Load();

        var defaults = new Settings();
        return new Settings
        {
            ConductorServerUrl = Read("CONDUCTOR_SERVER_URL") ?? defaults.ConductorServerUrl,
            AuthKey = Read("CONDUCTOR_AUTH_KEY"),
            AuthSecret = Read("CONDUCTOR_AUTH_SECRET"),
            LlmModel = Read("CONDUCTOR_AGENT_LLM_MODEL") ?? defaults.LlmModel,
            IntegrationName = Read("CONDUCTOR_INTEGRATION_NAME") ?? defaults.IntegrationName,
            WebhookId = Read("WEBHOOK_ID") ?? defaults.WebhookId,
            SourceHeader = Read("WEBHOOK_SOURCE_HEADER") ?? defaults.SourceHeader,
        };
    }

    /// <summary>Return an environment variable, treating an empty value as unset.</summary>
    private static string? Read(string name) =>
        Environment.GetEnvironmentVariable(name) is { Length: > 0 } value ? value : null;
}
