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
    // Exercise 2: Change to "get_user_emails", taking a list of user IDs. Return the fork's
    // send_email tasks, each of type "SIMPLE" with a unique taskReferenceName (Exercise 3 repeats
    // a user ID), and a map from each one to that task's input (see Utils/DynamicForkTask.cs).
    /// <summary>Return the email address associated with a user.</summary>
    [WorkerTask(TaskType = "get_user_email")]
    public static string GetUserEmail([InputParam("user_id")] string userId) =>
        $"{userId}@example.com";

    /// <summary>Simulate sending an email.</summary>
    [WorkerTask(TaskType = "send_email")]
    public static void SendEmail(string recipients, string subject, string body)
    {
        Console.WriteLine($"Sending email\nTo: {recipients}\nSubject: {subject}\nBody: {body}");
        // Exercise 1: Return the emails table's fields for this email (change the return type to
        // match), with sent_time as a Unix timestamp in seconds.
    }
}
