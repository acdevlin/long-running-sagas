using System.Diagnostics;
using Conductor.AI;
using Conductor.Api;
using Conductor.Client.Extensions;
using Conductor.Client.Models;
using Conductor.Definition;
using Conductor.Definition.TaskType;
using Conductor.Executor;
using Microsoft.Data.Sqlite;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using WebhooksCodelab.Utils;
using Task = System.Threading.Tasks.Task;

namespace WebhooksCodelab;

/// <summary>
/// Register and start a durable webhook-driven workflow.
///
/// The step keeps its local workers running until the workflow reaches the
/// WAIT_FOR_WEBHOOK task, stores the completed email results, then exits.
/// Conductor keeps the workflow suspended until the send-webhook step sends a
/// callback; the serve-agent step runs the local tools needed after it resumes.
/// </summary>
public static class DeployWaitForWebhookWorkflow
{
    private static readonly string WorkflowName = $"wait_for_webhook_demo_{Settings.Current.Language}";
    private const int WorkflowVersion = 1;
    private const string WaitTaskRef = "wait_for_webhook_ref";

    // The type each send_email output field must have to fit the emails table,
    // once the SDK has read it from JSON (which gives whole numbers as long).
    private static readonly (string Name, Type Type)[] EmailOutputFields =
    [
        ("sent_time", typeof(long)),
        ("subject", typeof(string)),
        ("recipients", typeof(string)),
    ];

    private const int WorkflowTimeoutSeconds = 7 * 24 * 60 * 60;
    private static readonly TimeSpan ReadinessTimeout = TimeSpan.FromSeconds(60);
    private static readonly TimeSpan PollInterval = TimeSpan.FromSeconds(1);

    // Shown in the workflow's description in the Orkes Conductor UI.
    private const string CodelabLanguage = "C#";

    /// <summary>Build the workflow definition without registering or starting it.</summary>
    public static ConductorWorkflow BuildWorkflow()
    {
        var workflow = new ConductorWorkflow()
            .WithName(WorkflowName)
            .WithVersion(WorkflowVersion)
            .WithDescription($"Durable wait-for-webhook example (registered from {CodelabLanguage})")
            .WithTimeoutPolicy(WorkflowDef.TimeoutPolicyEnum.TIMEOUTWF, WorkflowTimeoutSeconds);

        // Exercise 2: Iterate over all user IDs in Settings.Current.UserIds and get their email addresses.
        var getEmailTask = new SimpleTask("get_user_email", "get_user_email_ref")
            .WithInput("user_id", workflow.Input("user_id"));

        // Exercise 2: Use a DYNAMIC_FORK to send an email to each recipient.
        // The SDK's DynamicFork is broken, so use Utils/DynamicForkTask instead, and
        // add a JoinTask right after it in WithTask to consolidate the results.
        // Also ensure that each sent email's task reference name is unique, for
        // example by appending the user ID's position in the list, since Exercise 3
        // repeats a user ID.
        var sendEmailTask = new SimpleTask(Workers.SendEmailTaskName, "send_email_ref")
            .WithInput("recipients", getEmailTask.Output("result"))
            .WithInput("subject", "Hello from Orkes")
            .WithInput("body", "Test Email");

        // conductor-csharp 3.0.0 serializes WaitForWebHookTask in a way the server
        // rejects, so two fields are corrected here. The server reads the match
        // rules from inputParameters.matches, not from inputParameters itself, and
        // it only accepts WAIT_FOR_WEBHOOK as a plain type string, not as a
        // workflowTaskType enum value.
        var webhookWait = new WaitForWebHookTask(WaitTaskRef, new Dictionary<string, object>
        {
            ["matches"] = new Dictionary<string, object>
            {
                // Every language version shares one webhook, so only match
                // payloads sent by this language's send-webhook step.
                ["$['language']"] = Settings.Current.Language,
                ["$['type']"] = "customer",
                // Exercise 2: Change to 'user_ids'.
                // Be sure the payload sent by SendWebhookPayload.cs matches the key you use here.
                ["$['user_id']"] = workflow.Input("user_id"),
            },
        });
        webhookWait.WorkflowTaskType = null;
        webhookWait.Type = "WAIT_FOR_WEBHOOK";

        var agentTask = new AgentTask(
            "process_webhook_ref",
            WebhookAgent.Agent.Name,
            webhookWait.Output("agent_input"));

        workflow.WithTask(getEmailTask, sendEmailTask, webhookWait, agentTask);
        // Set directly because WithOutputParameter throws while OutputParameters
        // is still null, which it is for every new ConductorWorkflow.
        workflow.OutputParameters = new Dictionary<string, object>
        {
            ["agent_response"] = agentTask.Output("text"),
        };

        return workflow;
    }

    /// <summary>Start one workflow execution and return its execution ID.</summary>
    private static string StartWorkflow(WorkflowExecutor workflowExecutor) =>
        workflowExecutor.StartWorkflow(new StartWorkflowRequest(
            name: WorkflowName,
            version: WorkflowVersion,
            input: new Dictionary<string, object> { ["user_id"] = Settings.Current.UserId }));

    /// <summary>Return the execution after it reaches its WAIT_FOR_WEBHOOK task.</summary>
    private static async Task<Workflow> WaitUntilWebhookReadyAsync(WorkflowResourceApi workflowClient, string workflowId)
    {
        var elapsed = Stopwatch.StartNew();

        while (elapsed.Elapsed < ReadinessTimeout)
        {
            var execution = workflowClient.GetExecutionStatus(workflowId, includeTasks: true);

            var waitTask = execution.Tasks?.FirstOrDefault(task => task.ReferenceTaskName == WaitTaskRef);
            if (waitTask?.Status == Conductor.Client.Models.Task.StatusEnum.INPROGRESS)
            {
                return execution;
            }

            if (execution.Status is Workflow.StatusEnum.FAILED
                or Workflow.StatusEnum.TIMEDOUT
                or Workflow.StatusEnum.TERMINATED)
            {
                throw new InvalidOperationException($"Workflow entered terminal status {execution.Status}");
            }

            await Task.Delay(PollInterval);
        }

        throw new TimeoutException(
            $"Workflow did not reach {WaitTaskRef} within {ReadinessTimeout.TotalSeconds} seconds");
    }

    /// <summary>Return valid outputs from every completed send-email task.</summary>
    private static List<Dictionary<string, object>> GetCompletedEmailOutputs(Workflow execution)
    {
        // Task-definition names remain stable while task references may not.
        var emailTasks = (execution.Tasks ?? [])
            .Where(task => task.TaskDefName == Workers.SendEmailTaskName
                && task.Status == Conductor.Client.Models.Task.StatusEnum.COMPLETED)
            .ToList();
        if (emailTasks.Count == 0)
        {
            throw new InvalidOperationException(
                $"No completed {Workers.SendEmailTaskName} task outputs were found");
        }

        var emailOutputs = new List<Dictionary<string, object>>();
        foreach (var task in emailTasks)
        {
            var output = task.OutputData
                ?? throw new InvalidOperationException(
                    $"Completed task {task.ReferenceTaskName} has invalid output");

            // A null value has no type, so this also rejects missing (null) values.
            var invalidFields = EmailOutputFields
                .Where(field => output.GetValueOrDefault(field.Name)?.GetType() != field.Type)
                .Select(field => field.Name)
                .ToList();
            if (invalidFields.Count > 0)
            {
                throw new InvalidOperationException(
                    $"Completed task {task.ReferenceTaskName} has missing or invalid fields: " +
                    string.Join(", ", invalidFields));
            }

            emailOutputs.Add(output);
        }

        return emailOutputs;
    }

    /// <summary>Insert all completed email outputs in one database transaction.</summary>
    private static async Task<int> StoreEmailOutputsAsync(List<Dictionary<string, object>> emailOutputs)
    {
        await using var connection = await QuerySqliteDb.OpenDatabaseAsync(writable: true);

        // Use a single DB transaction to avoid partial insert failures.
        await using var transaction = connection.BeginTransaction();
        await using var command = connection.CreateCommand();
        command.CommandText = """
            INSERT INTO emails (
                sent_time,
                subject,
                recipients
            )
            VALUES ($sent_time, $subject, $recipients)
            """;

        // Reuse one command for every row, changing only the parameter values.
        var sentTime = command.Parameters.Add("$sent_time", SqliteType.Integer);
        var subject = command.Parameters.Add("$subject", SqliteType.Text);
        var recipients = command.Parameters.Add("$recipients", SqliteType.Text);
        foreach (var emailOutput in emailOutputs)
        {
            sentTime.Value = emailOutput["sent_time"];
            subject.Value = emailOutput["subject"];
            recipients.Value = emailOutput["recipients"];
            await command.ExecuteNonQueryAsync();
        }

        await transaction.CommitAsync();
        return emailOutputs.Count;
    }

    public static async Task RunAsync()
    {
        var configuration = Settings.Current.CreateConductorConfiguration();

        // Starts polling for every [WorkerTask] in this project.
        using var workerHost = WorkflowTaskHost.CreateWorkerHost(configuration, LogLevel.Warning);
        await workerHost.StartAsync();

        try
        {
            // Deploy agent definition
            await using (var runtime = new AgentRuntime(configuration))
            {
                await runtime.DeployAsync(WebhookAgent.Agent);
            }

            var workflowExecutor = new WorkflowExecutor(configuration);
            workflowExecutor.RegisterWorkflow(BuildWorkflow(), overwrite: true);
            Console.WriteLine($"Registered workflow {WorkflowName}, version {WorkflowVersion}");

            var workflowId = StartWorkflow(workflowExecutor);
            Console.WriteLine($"Workflow URL: {Settings.Current.ServerBaseUrl}/execution/{workflowId}");

            var execution = await WaitUntilWebhookReadyAsync(
                configuration.GetClient<WorkflowResourceApi>(), workflowId);
            var emailOutputs = GetCompletedEmailOutputs(execution);
            var storedCount = await StoreEmailOutputsAsync(emailOutputs);
            Console.WriteLine($"Stored {storedCount} email record(s) in {QuerySqliteDb.DatabasePath}");
            Console.WriteLine($"{WaitTaskRef} is ready");
            Console.WriteLine(
                "Before sending the webhook, start the agent tool workers with " +
                "`dotnet run -- serve-agent`.");
            Console.WriteLine($"Webhook URL: {Settings.Current.WebhookEndpointUrl}");
        }
        catch (Exception error) when (error is FileNotFoundException or InvalidOperationException
            or TimeoutException or SqliteException)
        {
            // Report expected failures in one line, as the query-db step does.
            Console.Error.WriteLine($"Deploy step failed: {error.Message}");
            Environment.ExitCode = 1;
        }
        finally
        {
            await workerHost.StopAsync();
        }
    }
}
