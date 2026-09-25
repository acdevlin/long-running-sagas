using Conductor.Client.Worker;

namespace WebhooksCodelab.Utils;

/// <summary>
/// Worker tasks used by the webhook workflow. The SDK finds every
/// <c>[WorkerTask]</c> method on a class that also has the attribute.
/// </summary>
/// <remarks>
/// Set <c>TaskType</c> by name rather than passing constructor arguments: the
/// constructor resets the batch size and poll interval to 0, and a worker with a
/// batch size of 0 never polls for tasks.
///
/// A worker must return a string, a number, a <c>List&lt;object&gt;</c> or a
/// <c>Dictionary&lt;string, object&gt;</c>. The SDK fails the task for any other
/// type, such as a record or an anonymous object.
/// </remarks>
[WorkerTask]
public static class Workers
{
    // Task names shared with the deploy step. It schedules get_user_emails by
    // name, and finds the completed sends by the send_email name.
    public const string GetUserEmailsTaskName = "get_user_emails";
    public const string SendEmailTaskName = "send_email";

    // The keys of get_user_emails's output that the deploy step passes to its
    // DYNAMIC_FORK task: the tasks to fork, and the input for each of them.
    public const string DynamicTasksKey = "dynamicTasks";
    public const string DynamicTaskInputsKey = "dynamicTasksInputs";

    /// <summary>
    /// Resolve each user's email address and describe one send_email task per
    /// address, for the workflow's DYNAMIC_FORK task to run in parallel.
    /// </summary>
    /// <remarks>
    /// A DYNAMIC_FORK task only decides which branches to run when the workflow
    /// reaches it, using two inputs: a list of task definitions, and a map from
    /// each definition's reference name to that task's input. Returning both from
    /// this worker means the workflow sends as many emails as there are user IDs.
    /// </remarks>
    [WorkerTask(TaskType = GetUserEmailsTaskName)]
    public static Dictionary<string, object> GetUserEmails(
        [InputParam("user_ids")] List<string>? userIds, string subject, string body)
    {
        // The SDK passes null when the workflow does not supply user_ids.
        // Throwing an exception fails this task. Conductor then retries it as its
        // task definition allows, and fails the workflow if every attempt fails.
        if (userIds is not { Count: > 0 })
        {
            throw new ArgumentException("At least one user ID is required", nameof(userIds));
        }

        // The SDK sends these nested collections to Conductor as JSON arrays and
        // objects. Each task definition mixes strings with a nested dictionary,
        // so their values are typed as object.
        var dynamicTasks = new List<object>();
        var dynamicTaskInputs = new Dictionary<string, object>();

        for (var index = 0; index < userIds.Count; index++)
        {
            var userId = userIds[index];
            if (string.IsNullOrWhiteSpace(userId))
            {
                throw new ArgumentException($"Invalid user ID at index {index}", nameof(userIds));
            }

            // Every task in a workflow execution needs a unique reference name.
            // The same user ID can appear more than once, so use its position.
            var taskReferenceName = $"send_email_{index}";
            dynamicTasks.Add(new Dictionary<string, object>
            {
                ["name"] = SendEmailTaskName,
                ["taskReferenceName"] = taskReferenceName,
                ["type"] = "SIMPLE",
                // Empty because the fork supplies each task's input from the
                // dynamic task inputs below.
                ["inputParameters"] = new Dictionary<string, object>(),
            });
            dynamicTaskInputs[taskReferenceName] = new Dictionary<string, object>
            {
                ["recipients"] = $"{userId}@example.com",
                ["subject"] = subject,
                ["body"] = body,
            };
        }

        return new Dictionary<string, object>
        {
            [DynamicTasksKey] = dynamicTasks,
            [DynamicTaskInputsKey] = dynamicTaskInputs,
        };
    }

    /// <summary>Simulate sending an email.</summary>
    /// <remarks>
    /// Conductor schedules every forked send_email task at once. The SDK polls
    /// for up to a batch of tasks at a time (twice the processor count, and at
    /// least 2) and runs a batch in parallel, so this worker needs no extra
    /// settings to send the emails in parallel.
    /// </remarks>
    [WorkerTask(TaskType = SendEmailTaskName)]
    public static Dictionary<string, object> SendEmail(string recipients, string subject, string body)
    {
        Console.WriteLine($"Sending email\nTo: {recipients}\nSubject: {subject}\nBody: {body}");
        return new Dictionary<string, object>
        {
            ["sent_time"] = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
            ["subject"] = subject,
            ["recipients"] = recipients,
        };
    }
}
