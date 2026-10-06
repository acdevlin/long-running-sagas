//! Helper for the workflow's `AGENT` task.

use serde_json::{Value, json};

/// Return an `AGENT` task, as JSON, that invokes a deployed Conductor agent. The SDK's
/// `WorkflowTask` has no `AGENT` type, so this creates the task definition that the server expects.
pub fn agent_task(task_reference_name: &str, agent_name: &str, prompt: &str) -> Value {
    json!({
        "name": "invoke_agent",
        "taskReferenceName": task_reference_name,
        "type": "AGENT",
        "inputParameters": {
            // Run the agent deployed to this Conductor cluster under agent_name. The
            // default agentType, "a2a", calls an external A2A agent instead.
            "agentType": "conductor",
            "name": agent_name,
            "prompt": prompt,
            // How often, in seconds, the task checks on the agent, and how long the
            // agent may run before the task fails and Conductor cancels the agent.
            "pollIntervalSeconds": 5,
            "maxDurationSeconds": 300,
        },
    })
}
