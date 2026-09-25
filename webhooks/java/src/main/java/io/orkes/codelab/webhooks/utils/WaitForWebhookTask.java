package io.orkes.codelab.webhooks.utils;

import com.netflix.conductor.common.metadata.tasks.TaskType;
import com.netflix.conductor.common.metadata.workflow.WorkflowTask;
import com.netflix.conductor.sdk.workflow.def.tasks.Task;

import java.util.Map;

/**
 * WAIT_FOR_WEBHOOK task, which suspends the workflow until a webhook payload arrives that meets
 * every match rule. Each rule maps a JSONPath into the payload to the value it must have.
 */
public final class WaitForWebhookTask extends Task<WaitForWebhookTask> {

    public WaitForWebhookTask(String taskReferenceName, Map<String, Object> matches) {
        // The SDK's TaskType enum has no WAIT_FOR_WEBHOOK member, so SIMPLE is a placeholder
        // that updateWorkflowTask replaces with the type the server expects.
        super(taskReferenceName, TaskType.SIMPLE);
        input("matches", matches);
    }

    @Override
    protected void updateWorkflowTask(WorkflowTask workflowTask) {
        workflowTask.setType("WAIT_FOR_WEBHOOK");
    }
}
