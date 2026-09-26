/**
 * Worker tasks used by the webhook workflow. Importing this file registers each @worker method
 * with the SDK, and the deploy-workflow step's TaskHandler then polls for their tasks.
 */

import { worker, type Task, type TaskResult } from "@io-orkes/conductor-javascript";

/** What a worker returns: the task's status and, optionally, its output. */
type WorkerResult = Omit<TaskResult, "taskId" | "workflowInstanceId">;

// The SDK calls each @worker method without creating a Workers instance, so the methods are
// static and cannot use `this`.
export class Workers {
  // Exercise 2: Change to "get_user_emails", taking a list of user_ids. Return the fork's
  // send_email tasks, each of type "SIMPLE" with a unique taskReferenceName (Exercise 3 repeats a
  // user_id), and an object mapping each one to that task's input (see utils/dynamicForkTask.ts).
  /** Return the email address associated with a user, as the task output "result". */
  @worker({ taskDefName: "get_user_email" })
  static async getUserEmail(task: Task): Promise<WorkerResult> {
    const { user_id: userId } = task.inputData as { user_id: string };
    return { status: "COMPLETED", outputData: { result: `${userId}@example.com` } };
  }

  // Exercise 2: Set concurrency in @worker, which is 1 by default, so this worker sends the forked
  // emails in parallel.
  /** Simulate sending an email. */
  @worker({ taskDefName: "send_email" })
  static async sendEmail(task: Task): Promise<WorkerResult> {
    const { recipients, subject, body } = task.inputData as {
      recipients: string;
      subject: string;
      body: string;
    };
    console.log(`Sending email\nTo: ${recipients}\nSubject: ${subject}\nBody: ${body}`);
    // Exercise 1: Return this email's fields for the emails table as outputData, with sent_time
    // as a Unix timestamp in seconds.
    return { status: "COMPLETED" };
  }
}
