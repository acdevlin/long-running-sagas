//! Helper for the `DYNAMIC_FORK` task that Exercise 2 adds.

use std::collections::HashMap;

use conductor::models::{TaskType, WorkflowTask};

// The input parameters that hold the forked task definitions and their inputs.
const TASKS_PARAM: &str = "dynamicTasks";
const TASKS_INPUTS_PARAM: &str = "dynamicTasksInputs";

/// Return a `DYNAMIC_FORK` task, which runs one branch per task definition it receives at runtime.
/// The SDK has no builder for this task type. Add `WorkflowTask::join(reference_name, vec![])`
/// straight after it, so the workflow waits for every branch to finish.
///
/// `tasks` is an expression for the list of task definitions to fork, each with a `name`, a
/// unique `taskReferenceName` and a `type` (`SIMPLE` for a worker task). `tasks_inputs` is an
/// expression for an object that maps each forked task's `taskReferenceName` to that task's input.
///
/// ```ignore
/// let fork = dynamic_fork_task(
///     "send_emails_fork",
///     "${get_user_emails_ref.output.dynamicTasks}",
///     "${get_user_emails_ref.output.dynamicTasksInputs}",
/// );
/// ```
pub fn dynamic_fork_task(
    task_reference_name: &str,
    tasks: &str,
    tasks_inputs: &str,
) -> WorkflowTask {
    WorkflowTask {
        name: task_reference_name.to_owned(),
        task_reference_name: task_reference_name.to_owned(),
        task_type: TaskType::ForkJoinDynamic,
        input_parameters: HashMap::from([
            (TASKS_PARAM.to_owned(), tasks.into()),
            (TASKS_INPUTS_PARAM.to_owned(), tasks_inputs.into()),
        ]),
        dynamic_fork_tasks_param: Some(TASKS_PARAM.to_owned()),
        dynamic_fork_tasks_input_param_name: Some(TASKS_INPUTS_PARAM.to_owned()),
        ..WorkflowTask::default()
    }
}
