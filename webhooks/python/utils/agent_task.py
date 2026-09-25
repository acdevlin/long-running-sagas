"""
Workflow adapter for invoking a deployed Conductor agent. This allows an AGENT task to be
included in a workflow by using the ">>" operator to chain it with non-AGENT tasks.
"""

from conductor.client.http.models import WorkflowTask
from conductor.client.workflow.task.task import TaskInterface
from conductor.client.workflow.task.task_type import TaskType

# Lets AgentTask pass the real enum member when available and fall back otherwise.
# None until the SDK adds TaskType.AGENT (absent in conductor-python 2.0.0).
_AGENT_TASK_TYPE: TaskType | None = getattr(TaskType, "AGENT", None)


class AgentTask(TaskInterface):
    """Invoke a deployed agent using the server's native AGENT task."""

    def __init__(
        self,
        task_ref_name: str,
        agent_name: str,
        prompt: str,
    ) -> None:
        super().__init__(
            task_reference_name=task_ref_name,
            task_type=_AGENT_TASK_TYPE or TaskType.USER_DEFINED,
            task_name="invoke_agent",
            input_parameters={
                # Run the agent deployed to this Conductor cluster under agent_name.
                # The default agentType, "a2a", calls an external A2A agent instead.
                "agentType": "conductor",
                "name": agent_name,
                "prompt": prompt,
                # How often, in seconds, the task checks on the agent, and how long the
                # agent may run before the task fails and Conductor cancels the agent.
                "pollIntervalSeconds": 5,
                "maxDurationSeconds": 300,
            },
        )

    def to_workflow_task(self) -> WorkflowTask:
        """Serialize the task with the AGENT type the server expects."""
        task = super().to_workflow_task()
        if _AGENT_TASK_TYPE is None:
            # The base class only accepts TaskType members, so __init__ used a
            # placeholder. Correct the type in the definition sent to the server.
            task.type = "AGENT"
        return task
