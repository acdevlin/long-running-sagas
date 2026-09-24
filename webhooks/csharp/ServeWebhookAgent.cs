using Conductor.AI;
using WebhooksCodelab.Utils;

namespace WebhooksCodelab;

/// <summary>Serve the local database tools used by the post-webhook agent.</summary>
public static class ServeWebhookAgent
{
    /// <summary>Deploy the agent and serve its tool workers until interrupted.</summary>
    public static async Task RunAsync()
    {
        using var cancellation = new CancellationTokenSource();
        Console.CancelKeyPress += (_, eventArgs) =>
        {
            // Let ServeAsync stop its workers cleanly instead of killing the process.
            eventArgs.Cancel = true;
            cancellation.Cancel();
        };

        await using var runtime = new AgentRuntime(Settings.Current.CreateConductorConfiguration());
        Console.WriteLine("Serving the agent's tool workers. Press Ctrl+C to stop.");
        await runtime.ServeAsync(WebhookAgent.Agent, cancellation.Token);
    }
}
