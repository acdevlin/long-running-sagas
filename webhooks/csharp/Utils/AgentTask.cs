namespace WebhooksCodelab.Utils;

/// <summary>
/// Workflow adapter for invoking a deployed Conductor agent with the server's
/// native AGENT task, so it can be added to a workflow alongside other tasks.
/// </summary>
public class AgentTask : Conductor.Definition.TaskType.Task
{
    // conductor-csharp 3.0.0 has no AGENT member in WorkflowTaskTypeEnum, and the
    // base class only accepts enum members, so SIMPLE is a placeholder that the
    // constructor replaces with the AGENT type the server expects.
    public AgentTask(string taskReferenceName, string agentName, string prompt)
        : base(taskReferenceName, WorkflowTaskTypeEnum.SIMPLE)
    {
        Name = "invoke_agent";
        WorkflowTaskType = null;
        Type = "AGENT";
        InputParameters = new Dictionary<string, object>
        {
            // Run the agent deployed to this Conductor cluster under agentName. The
            // default agentType, "a2a", calls an external A2A agent instead.
            ["agentType"] = "conductor",
            ["name"] = agentName,
            ["prompt"] = prompt,
            // How often, in seconds, the task checks on the agent, and how long the
            // agent may run before the task fails and Conductor cancels the agent.
            ["pollIntervalSeconds"] = 5,
            ["maxDurationSeconds"] = 300,
        };
    }
}
