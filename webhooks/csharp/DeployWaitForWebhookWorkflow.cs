using System.Diagnostics;
using Conductor.AI;
using Conductor.Api;
using Conductor.Client.Extensions;
using Conductor.Client.Models;
using Conductor.Definition;
using Conductor.Definition.TaskType;
using Conductor.Executor;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using WebhooksCodelab.Utils;
using Task = System.Threading.Tasks.Task;

namespace WebhooksCodelab;

/// <summary>
/// Register and start a durable webhook-driven workflow.
///
/// The step keeps its local workers running until the workflow reaches the
/// WAIT_FOR_WEBHOOK task, then exits. Conductor keeps the workflow suspended
/// until the send-webhook step sends a callback; the serve-agent step runs the
/// local tools needed after it resumes.
/// </summary>
public static class DeployWaitForWebhookWorkflow
{
    private static readonly string WorkflowName = $"wait_for_webhook_demo_{Settings.Current.Language}";
    private const int WorkflowVersion = 1;
    private const string WaitTaskRef = "wait_for_webhook_ref";

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
            // Mark the execution TIMED_OUT if it runs longer than WorkflowTimeoutSeconds,
            // for example because no webhook arrives. ALERT_ONLY would let it keep running.
            .WithTimeoutPolicy(WorkflowDef.TimeoutPolicyEnum.TIMEOUTWF, WorkflowTimeoutSeconds);

        // Exercise 2: Replace this with one get_user_emails task that resolves every address in
        // workflow.Input("user_ids"), so the number of emails is decided at runtime. Pass it the
        // subject and body as well, for the forked send_email tasks.
        var getEmailTask = new SimpleTask("get_user_email", "get_user_email_ref")
            .WithInput("user_id", workflow.Input("user_id"));

        // Exercise 2: Send the emails with Utils/DynamicForkTask (the SDK's DynamicFork is broken),
        // then add a JoinTask with no branches straight after it, so it waits for every branch.
        var sendEmailTask = new SimpleTask("send_email", "send_email_ref")
            .WithInput("recipients", getEmailTask.Output("result"))
            .WithInput("subject", $"Hello from {CodelabLanguage}")
            .WithInput("body", $"Sent by the {CodelabLanguage} version of the webhooks codelab.");

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

    /// <summary>Wait until the execution reaches its WAIT_FOR_WEBHOOK task.</summary>
    private static async Task WaitUntilWebhookReadyAsync(WorkflowResourceApi workflowClient, string workflowId)
    {
        var elapsed = Stopwatch.StartNew();

        while (elapsed.Elapsed < ReadinessTimeout)
        {
            var execution = await workflowClient.GetExecutionStatusAsync(workflowId, includeTasks: true);

            var waitTask = execution.Tasks?.FirstOrDefault(task => task.ReferenceTaskName == WaitTaskRef);
            if (waitTask?.Status == Conductor.Client.Models.Task.StatusEnum.INPROGRESS)
            {
                // Exercise 1: Return this execution, with its tasks, so the caller can read every
                // send_email output (change this method to return Task<Workflow>).
                return;
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

    public static async Task RunAsync()
    {
        var configuration = Settings.Current.CreateConductorConfiguration();

        // Starts polling for every [WorkerTask] in this project.
        using var workerHost = WorkflowTaskHost.CreateWorkerHost(configuration, LogLevel.Warning);
        await workerHost.StartAsync();

        try
        {
            // Register the agent that the workflow's AGENT task runs.
            await using (var runtime = new AgentRuntime(configuration))
            {
                await runtime.DeployAsync(WebhookAgent.Agent);
            }

            var workflowExecutor = new WorkflowExecutor(configuration);
            workflowExecutor.RegisterWorkflow(BuildWorkflow(), overwrite: true);
            Console.WriteLine($"Registered workflow {WorkflowName}, version {WorkflowVersion}");

            var workflowId = StartWorkflow(workflowExecutor);
            Console.WriteLine($"Workflow URL: {Settings.Current.ServerBaseUrl}/execution/{workflowId}");

            await WaitUntilWebhookReadyAsync(configuration.GetClient<WorkflowResourceApi>(), workflowId);
            // Exercise 1: Store a row in QuerySqliteDb.DatabasePath for each completed send_email
            // task. Match on TaskDefName, as ReferenceTaskName differs per email from Exercise 2 on.
            // Each task's result is in its OutputData, where whole numbers arrive as long.
            Console.WriteLine($"{WaitTaskRef} is ready");
            Console.WriteLine(
                "Before sending the webhook, start the agent tool workers with " +
                "`dotnet run -- serve-agent`, or restart them if you've changed " +
                "the code since they started.");
            Console.WriteLine($"Webhook URL: {Settings.Current.WebhookEndpointUrl}");
        }
        finally
        {
            await workerHost.StopAsync();
        }
    }
}
