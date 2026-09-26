import type { WorkflowTask } from "@io-orkes/conductor-javascript";

/**
 * AGENT task that invokes a deployed Conductor agent. The SDK has no builder for this task type,
 * so this creates the task definition that the server expects.
 */
export function agentTask(
  taskReferenceName: string,
  agentName: string,
  prompt: string,
): WorkflowTask {
  return {
    name: "invoke_agent",
    taskReferenceName,
    type: "AGENT",
    inputParameters: {
      // Run the agent deployed to this Conductor cluster under agentName. The
      // default agentType, "a2a", calls an external A2A agent instead.
      agentType: "conductor",
      name: agentName,
      prompt,
      // How often, in seconds, the task checks on the agent, and how long the
      // agent may run before the task fails and Conductor cancels the agent.
      pollIntervalSeconds: 5,
      maxDurationSeconds: 300,
    },
  };
}
