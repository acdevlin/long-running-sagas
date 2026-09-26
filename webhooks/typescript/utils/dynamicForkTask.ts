import type { WorkflowTask } from "@io-orkes/conductor-javascript";

// The input parameters that hold the forked task definitions and their inputs.
const TASKS_PARAM = "dynamicTasks";
const TASKS_INPUTS_PARAM = "dynamicTasksInputs";

/**
 * DYNAMIC_FORK task that runs one branch per task definition it receives at runtime. Use it in
 * place of the SDK's dynamicForkTask, which only accepts a list of tasks that is fixed when the
 * workflow is built, and add the SDK's joinTask straight after it so the workflow waits for every
 * branch to finish.
 *
 * @example
 * // taskOutput is defined in deployWaitForWebhookWorkflow.ts.
 * const fork = dynamicForkTask(
 *   "send_emails_fork",
 *   taskOutput(getEmailsTask, "dynamicTasks"),
 *   taskOutput(getEmailsTask, "dynamicTasksInputs"),
 * );
 * workflow.add([getEmailsTask, fork, joinTask("send_emails_join", []), ...]);
 *
 * @param taskReferenceName Reference name of the fork task.
 * @param tasks Expression for the list of task definitions to fork, each with a `name`, a unique
 *   `taskReferenceName` and a `type` (`SIMPLE` for a worker task).
 * @param tasksInputs Expression for an object that maps each forked task's `taskReferenceName`
 *   to that task's input.
 */
export function dynamicForkTask(
  taskReferenceName: string,
  tasks: string,
  tasksInputs: string,
): WorkflowTask {
  return {
    name: taskReferenceName,
    taskReferenceName,
    type: "FORK_JOIN_DYNAMIC",
    inputParameters: {
      [TASKS_PARAM]: tasks,
      [TASKS_INPUTS_PARAM]: tasksInputs,
    },
    dynamicForkTasksParam: TASKS_PARAM,
    dynamicForkTasksInputParamName: TASKS_INPUTS_PARAM,
  };
}
