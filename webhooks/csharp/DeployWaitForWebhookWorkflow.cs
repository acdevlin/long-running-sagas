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

    // Shown in the workflow's description in the Orkes Conductor UI, and in every
    // email this version sends, so you can tell the language versions apart.
    private const string CodelabLanguage = "C#";

    /// <summary>Build the workflow definition without registering or starting it.</summary>
    public static ConductorWorkflow BuildWorkflow()
    {
        var workflow = new ConductorWorkflow()
            .WithName(WorkflowName)
            .WithVersion(WorkflowVersion)
            .WithDescription($"Durable wait-for-webhook example (registered from {CodelabLanguage})")
            .WithTimeoutPolicy(WorkflowDef.TimeoutPolicyEnum.TIMEOUTWF, WorkflowTimeoutSeconds)
            // Lists the input that StartWorkflow supplies. Conductor shows it in the
            // workflow definition but does not require it when a workflow starts.
            .WithInputParameter("user_ids");

        // Resolve every recipient's address in a single worker task, which also
        // prepares one send_email task per address for the fork below.
        var getEmailsTask = new SimpleTask(Workers.GetUserEmailsTaskName, "get_user_emails_ref")
            .WithInput("user_ids", workflow.Input("user_ids"))
            .WithInput("subject", $"Hello from {CodelabLanguage}")
            .WithInput("body", $"Sent by the {CodelabLanguage} version of the webhooks codelab.");

        // A DYNAMIC_FORK task starts one parallel branch for each task that
        // get_user_emails returned, so the number of emails is decided at runtime
        // rather than in this definition. Utils/DynamicForkTask.cs replaces the
        // SDK's DynamicFork class, which does not work in conductor-csharp 3.0.0.
        var sendEmailsFork = new DynamicForkTask(
            "send_emails_fork",
            getEmailsTask.Output(Workers.DynamicTasksKey),
            getEmailsTask.Output(Workers.DynamicTaskInputsKey));

        // A JOIN task holds the workflow until the fork's branches finish, so every
        // email is sent before the workflow waits for the webhook. JoinOn normally
        // lists the branches to wait for, but a dynamic fork's branches are only
        // known at runtime, so it is left empty and the server waits for all of them.
        var sendEmailsJoin = new JoinTask("send_emails_join");

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
                // Only resume for a webhook about the recipients this execution
                // emailed. The send-webhook step sends the same user_ids list.
                ["$['user_ids']"] = workflow.Input("user_ids"),
            },
        });
        webhookWait.WorkflowTaskType = null;
        webhookWait.Type = "WAIT_FOR_WEBHOOK";

        var agentTask = new AgentTask(
            "process_webhook_ref",
            WebhookAgent.Agent.Name,
            webhookWait.Output("agent_input"));

        // The JOIN must come straight after its DYNAMIC_FORK.
        workflow.WithTask(getEmailsTask, sendEmailsFork, sendEmailsJoin, webhookWait, agentTask);
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
            input: new Dictionary<string, object> { ["user_ids"] = Settings.Current.UserIds }));

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
        // Match on the task name, because each forked send_email task has its own
        // reference name (send_email_0, send_email_1 and so on).
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
