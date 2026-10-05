package utils

import "github.com/conductor-sdk/conductor-go/sdk/model"

// WaitForWebhookTask returns a WAIT_FOR_WEBHOOK task, which suspends the workflow until a webhook
// payload arrives that meets every match rule. Each rule maps a JSONPath into the payload to the
// value it must have. The SDK has no builder for this task type, so this creates the task
// definition that the server expects.
func WaitForWebhookTask(taskReferenceName string, matches map[string]any) model.WorkflowTask {
	return model.WorkflowTask{
		Name:              taskReferenceName,
		TaskReferenceName: taskReferenceName,
		Type_:             "WAIT_FOR_WEBHOOK",
		InputParameters:   map[string]any{"matches": matches},
	}
}
