import type { WorkflowTask } from "@io-orkes/conductor-javascript";

/**
 * WAIT_FOR_WEBHOOK task, which suspends the workflow until a webhook payload arrives that meets
 * every match rule. Each rule maps a JSONPath into the payload to the value it must have.
 */
export function waitForWebhookTask(
  taskReferenceName: string,
  matches: Record<string, unknown>,
): WorkflowTask {
  // The SDK's own waitForWebhookTask puts the match rules directly in inputParameters, but the
  // server reads them from inputParameters.matches.
  return {
    name: taskReferenceName,
    taskReferenceName,
    type: "WAIT_FOR_WEBHOOK",
    inputParameters: { matches },
  };
}
