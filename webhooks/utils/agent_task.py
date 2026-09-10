"""
Workflow adapter for invoking a deployed Conductor agent. This allows an AGENT task to be
included in a workflow by using the ">>" operator to chain it with non-AGENT tasks.
"""

from conductor.client.http.models import WorkflowTask
from conductor.client.workflow.task.task import TaskInterface
from conductor.client.workflow.task.task_type import TaskType


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
            task_type=TaskType.USER_DEFINED,
            task_name="invoke_agent",
            input_parameters={
                "agentType": "conductor",
                "name": agent_name,
                "prompt": prompt,
                "pollIntervalSeconds": 5,
                "maxDurationSeconds": 300,
            },
        )

    def to_workflow_task(self) -> WorkflowTask:
        # The SDK requires a TaskType enum but does not yet include AGENT.
        # Replace the placeholder only in the definition sent to the server.
        task = super().to_workflow_task()
        task.type = "AGENT"
        return task
