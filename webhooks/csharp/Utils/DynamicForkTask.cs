namespace WebhooksCodelab.Utils;

/// <summary>
/// DYNAMIC_FORK task that runs one branch per task definition it receives at
/// runtime. Use it in place of the SDK's <c>DynamicFork</c>, and add a
/// <c>JoinTask</c> immediately after it in the workflow so the workflow waits
/// for every branch to finish.
/// </summary>
/// <example>
/// <code>
/// var fork = new DynamicForkTask(
///     "send_emails_fork",
///     getEmailsTask.Output("dynamicTasks"),
///     getEmailsTask.Output("dynamicTasksInputs"));
/// workflow.WithTask(getEmailsTask, fork, new JoinTask("send_emails_join"), ...);
/// </code>
/// </example>
public class DynamicForkTask : Conductor.Definition.TaskType.Task
{
    // The input parameters that hold the forked task definitions and their inputs.
    private const string TasksParam = "dynamicTasks";
    private const string TasksInputsParam = "dynamicTasksInputs";

    /// <param name="taskReferenceName">Reference name of the fork task.</param>
    /// <param name="tasks">
    /// Expression for the list of task definitions to fork, each with a
    /// <c>name</c>, a unique <c>taskReferenceName</c> and a <c>type</c>
    /// (<c>SIMPLE</c> for a worker task).
    /// </param>
    /// <param name="tasksInputs">
    /// Expression for a map from each forked task's <c>taskReferenceName</c> to
    /// that task's input.
    /// </param>
    public DynamicForkTask(string taskReferenceName, string tasks, string tasksInputs)
        : base(taskReferenceName, WorkflowTaskTypeEnum.FORKJOINDYNAMIC)
    {
        // conductor-csharp 3.0.0's DynamicFork only sets these two fields when
        // it is converted by a code path that ConductorWorkflow.WithTask never
        // calls, so the server would not know where to find the forked tasks.
        DynamicForkTasksParam = TasksParam;
        DynamicForkTasksInputParamName = TasksInputsParam;
        InputParameters[TasksParam] = tasks;
        InputParameters[TasksInputsParam] = tasksInputs;
    }
}
