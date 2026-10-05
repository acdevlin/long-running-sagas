package utils

import "github.com/conductor-sdk/conductor-go/sdk/model"

// AgentTask returns an AGENT task that invokes a deployed Conductor agent. The SDK has no builder
// for this task type, so this creates the task definition that the server expects.
func AgentTask(taskReferenceName, agentName, prompt string) model.WorkflowTask {
	return model.WorkflowTask{
		Name:              "invoke_agent",
		TaskReferenceName: taskReferenceName,
		Type_:             "AGENT",
		InputParameters: map[string]any{
			// Run the agent deployed to this Conductor cluster under agentName. The
			// default agentType, "a2a", calls an external A2A agent instead.
			"agentType": "conductor",
			"name":      agentName,
			"prompt":    prompt,
			// How often, in seconds, the task checks on the agent, and how long the
			// agent may run before the task fails and Conductor cancels the agent.
			"pollIntervalSeconds": 5,
			"maxDurationSeconds":  300,
		},
	}
}
