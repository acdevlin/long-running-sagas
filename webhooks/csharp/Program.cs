// Entry point for every step of the C# webhooks codelab. Run a step from this
// folder with `dotnet run -- <step>`, for example `dotnet run -- deploy-workflow`.
using WebhooksCodelab;
using WebhooksCodelab.Utils;

var steps = new Dictionary<string, Func<Task>>
{
    ["create-db"] = CreateSqliteDb.RunAsync,
    ["deploy-workflow"] = DeployWaitForWebhookWorkflow.RunAsync,
    ["serve-agent"] = ServeWebhookAgent.RunAsync,
    ["send-webhook"] = SendWebhookPayload.RunAsync,
    ["query-db"] = QuerySqliteDb.RunAsync,
};

if (args.Length != 1 || !steps.TryGetValue(args[0], out var step))
{
    Console.Error.WriteLine($"Usage: dotnet run -- <{string.Join("|", steps.Keys)}>");
    Environment.ExitCode = 1;
    return;
}

// A step that handles its own failure reports it through Environment.ExitCode.
await step();
