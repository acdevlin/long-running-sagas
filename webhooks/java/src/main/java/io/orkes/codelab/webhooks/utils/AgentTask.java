package io.orkes.codelab.webhooks.utils;

import com.netflix.conductor.common.metadata.tasks.TaskType;
import com.netflix.conductor.common.metadata.workflow.WorkflowTask;
import com.netflix.conductor.sdk.workflow.def.tasks.Task;

/**
 * Workflow adapter for invoking a deployed Conductor agent with the server's native AGENT task, so
 * it can be added to a workflow alongside other tasks.
 */
public final class AgentTask extends Task<AgentTask> {

    public AgentTask(String taskReferenceName, String agentName, String prompt) {
        // The SDK's TaskType enum has no AGENT member, so SIMPLE is a placeholder that
        // updateWorkflowTask replaces with the type the server expects.
        super(taskReferenceName, TaskType.SIMPLE);
        name("invoke_agent");
        // Run the agent deployed to this Conductor cluster under agentName. The
        // default agentType, "a2a", calls an external A2A agent instead.
        input("agentType", "conductor");
        input("name", agentName);
        input("prompt", prompt);
        // How often, in seconds, the task checks on the agent, and how long the
        // agent may run before the task fails and Conductor cancels the agent.
        input("pollIntervalSeconds", 5);
        input("maxDurationSeconds", 300);
    }

    @Override
    protected void updateWorkflowTask(WorkflowTask workflowTask) {
        workflowTask.setType("AGENT");
    }
}
