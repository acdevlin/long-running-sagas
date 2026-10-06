/**
 * Worker tasks used by the webhook workflow. Importing this file registers each @worker method
 * with the SDK, and the deploy-workflow step's TaskHandler then polls for their tasks.
 */

import {
  worker,
  type Task,
  type TaskResult,
  type WorkflowTask,
} from "@io-orkes/conductor-javascript";

/** What a worker returns: the task's status and, optionally, its output. */
type WorkerResult = Omit<TaskResult, "taskId" | "workflowInstanceId">;

// These shared names keep the worker's output synchronized with the workflow definition that
// reads it in the deploy-workflow step.
export const DYNAMIC_TASKS_PARAM = "dynamicTasks";
export const DYNAMIC_TASKS_INPUTS_PARAM = "dynamicTasksInputs";
export const SEND_EMAIL_TASK_NAME = "send_email";

// The SDK calls each @worker method without creating a Workers instance, so the methods are
// static and cannot use `this`.
export class Workers {
  /** Return one send_email task per user's email address, for the workflow's dynamic fork. */
  @worker({ taskDefName: "get_user_emails" })
  static async getUserEmails(task: Task): Promise<WorkerResult> {
    const {
      user_ids: userIds,
      subject,
      body,
    } = task.inputData as { user_ids: string[]; subject: string; body: string };
    if (!Array.isArray(userIds) || userIds.length === 0) {
      throw new Error("At least one user ID is required");
    }

    const dynamicTasks: WorkflowTask[] = [];
    const dynamicTasksInputs: Record<string, unknown> = {};
    for (const [index, userId] of userIds.entries()) {
      if (typeof userId !== "string" || userId.trim() === "") {
        throw new Error(`Invalid user ID at index ${index}`);
      }

      // The index keeps each reference name unique, even when a user ID repeats.
      const taskReferenceName = `send_email_${index}`;
      dynamicTasks.push({ name: SEND_EMAIL_TASK_NAME, taskReferenceName, type: "SIMPLE" });
      dynamicTasksInputs[taskReferenceName] = {
        recipients: `${userId}@example.com`,
        subject,
        body,
      };
    }
    return {
      status: "COMPLETED",
      outputData: {
        [DYNAMIC_TASKS_PARAM]: dynamicTasks,
        [DYNAMIC_TASKS_INPUTS_PARAM]: dynamicTasksInputs,
      },
    };
  }

  // Concurrency above the default of 1 lets this worker send the forked emails in parallel.
  /** Simulate sending an email. */
  @worker({ taskDefName: SEND_EMAIL_TASK_NAME, concurrency: 10 })
  static async sendEmail(task: Task): Promise<WorkerResult> {
    const { recipients, subject, body } = task.inputData as {
      recipients: string;
      subject: string;
      body: string;
    };
    console.log(`Sending email\nTo: ${recipients}\nSubject: ${subject}\nBody: ${body}`);
    return {
      status: "COMPLETED",
      outputData: { sent_time: Math.floor(Date.now() / 1000), subject, recipients },
    };
  }
}
