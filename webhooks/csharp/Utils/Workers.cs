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
    // Shared with the deploy step, which finds the completed sends by this name.
    public const string SendEmailTaskName = "send_email";

    // Exercise 2: Change to "get_user_emails" and take a list of user IDs as input.
    /// <summary>Return the email address associated with a user.</summary>
    [WorkerTask(TaskType = "get_user_email")]
    public static string GetUserEmail([InputParam("user_id")] string userId) =>
        $"{userId}@example.com";

    /// <summary>Simulate sending an email.</summary>
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
