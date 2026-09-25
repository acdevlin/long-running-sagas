package io.orkes.codelab.webhooks;

import com.netflix.conductor.client.http.WorkflowClient;
import com.netflix.conductor.common.metadata.tasks.Task;
import com.netflix.conductor.common.metadata.workflow.WorkflowDef;
import com.netflix.conductor.common.run.Workflow;
import com.netflix.conductor.sdk.workflow.def.ConductorWorkflow;
import com.netflix.conductor.sdk.workflow.def.tasks.SimpleTask;
import com.netflix.conductor.sdk.workflow.executor.WorkflowExecutor;

import io.orkes.codelab.webhooks.utils.AgentTask;
import io.orkes.codelab.webhooks.utils.WaitForWebhookTask;
import io.orkes.codelab.webhooks.utils.WebhookAgent;
import io.orkes.codelab.webhooks.utils.Workers;

import org.conductoross.conductor.ai.AgentRuntime;

import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeoutException;

/**
 * Register and start a durable webhook-driven workflow, running its workers until it reaches the
 * WAIT_FOR_WEBHOOK task. Conductor then keeps it suspended until the send-webhook step resumes it.
 */
public final class DeployWaitForWebhookWorkflow {

    private static final String WORKFLOW_NAME = "wait_for_webhook_demo_" + Settings.LANGUAGE;
    private static final int WORKFLOW_VERSION = 1;
    private static final String WAIT_TASK_REF = "wait_for_webhook_ref";

    private static final long WORKFLOW_TIMEOUT_SECONDS = Duration.ofDays(7).toSeconds();
    private static final Duration READINESS_TIMEOUT = Duration.ofSeconds(60);
    private static final Duration READINESS_POLL_INTERVAL = Duration.ofSeconds(1);
    private static final int WORKER_POLL_INTERVAL_MILLIS = 100;

    // Shown in the workflow's description in the Orkes Conductor UI, and in every
    // email this version sends, so you can tell the language versions apart.
    private static final String CODELAB_LANGUAGE = "Java";

    private DeployWaitForWebhookWorkflow() {}

    /** Build the workflow definition without registering or starting it. */
    private static ConductorWorkflow<Map<String, Object>> buildWorkflow(
            WorkflowExecutor workflowExecutor) {
        var workflow = new ConductorWorkflow<Map<String, Object>>(workflowExecutor);
        workflow.setName(WORKFLOW_NAME);
        workflow.setVersion(WORKFLOW_VERSION);
        workflow.setDescription(
                "Durable wait-for-webhook example (registered from " + CODELAB_LANGUAGE + ")");
        // Mark the execution TIMED_OUT if it runs longer than WORKFLOW_TIMEOUT_SECONDS,
        // for example because no webhook arrives. ALERT_ONLY would let it keep running.
        workflow.setTimeoutPolicy(WorkflowDef.TimeoutPolicy.TIME_OUT_WF);
        workflow.setTimeoutSeconds(WORKFLOW_TIMEOUT_SECONDS);

        String subject = "Hello from " + CODELAB_LANGUAGE;
        String body = "Sent by the " + CODELAB_LANGUAGE + " version of the webhooks codelab.";

        // Exercise 2: Replace this with one get_user_emails task that resolves every address in
        // ConductorWorkflow.input.get("user_ids"), so the number of emails is decided at runtime.
        // Pass it the subject and body as well, for the forked send_email tasks.
        var getEmailTask =
                new SimpleTask("get_user_email", "get_user_email_ref")
                        .input("user_id", ConductorWorkflow.input.get("user_id"));

        // Exercise 2: Send the emails with new DynamicFork(referenceName, getEmailsTask). It adds
        // get_user_emails before itself and a join after, so add only the fork to the workflow.
        var sendEmailTask =
                new SimpleTask("send_email", "send_email_ref")
                        .input("recipients", getEmailTask.taskOutput.get("result"))
                        .input("subject", subject)
                        .input("body", body);

        Map<String, Object> matches = new LinkedHashMap<>();
        // Every language version shares one webhook, so only match
        // payloads sent by this language's send-webhook step.
        matches.put("$['language']", Settings.LANGUAGE);
        matches.put("$['type']", "customer");
        // Exercise 2: Change to 'user_ids'. Be sure the payload sent by
        // SendWebhookPayload.java matches the key you use here.
        matches.put("$['user_id']", ConductorWorkflow.input.get("user_id"));
        var webhookWait = new WaitForWebhookTask(WAIT_TASK_REF, matches);

        var agentTask =
                new AgentTask(
                        "process_webhook_ref",
                        WebhookAgent.NAME,
                        webhookWait.taskOutput.get("agent_input"));

        workflow.add(getEmailTask);
        workflow.add(sendEmailTask);
        workflow.add(webhookWait);
        workflow.add(agentTask);
        workflow.setWorkflowOutput(Map.of("agent_response", agentTask.taskOutput.get("text")));

        return workflow;
    }

    /** Start one workflow execution and return its execution ID. */
    private static String startWorkflow(WorkflowExecutor workflowExecutor) {
        return workflowExecutor.startWorkflow(
                WORKFLOW_NAME, WORKFLOW_VERSION, Map.of("user_id", Settings.USER_ID));
    }

    /** Wait until the execution reaches its WAIT_FOR_WEBHOOK task. */
    private static void waitUntilWebhookReady(WorkflowClient workflowClient, String workflowId)
            throws InterruptedException, TimeoutException {
        // Unlike Instant.now(), System.nanoTime() is unaffected by changes to the system clock.
        long deadline = System.nanoTime() + READINESS_TIMEOUT.toNanos();

        while (System.nanoTime() - deadline < 0) {
            Workflow execution = workflowClient.getWorkflow(workflowId, true);

            boolean waiting =
                    execution.getTasks().stream()
                            .anyMatch(
                                    task ->
                                            WAIT_TASK_REF.equals(task.getReferenceTaskName())
                                                    && task.getStatus() == Task.Status.IN_PROGRESS);
            if (waiting) {
                // Exercise 1: Return this execution, with its tasks, so the caller can read every
                // send_email output (change this method to return Workflow).
                return;
            }

            if (execution.getStatus().isTerminal()) {
                throw new IllegalStateException(
                        "Workflow entered terminal status " + execution.getStatus());
            }

            Thread.sleep(READINESS_POLL_INTERVAL);
        }

        throw new TimeoutException(
                "Workflow did not reach %s within %d seconds"
                        .formatted(WAIT_TASK_REF, READINESS_TIMEOUT.toSeconds()));
    }

    public static int run() throws InterruptedException, TimeoutException {
        Settings settings = Settings.current();
        // Build the agent first, so a malformed model setting fails before any worker starts.
        var agent = WebhookAgent.create();
        var apiClient = settings.createApiClient();
        var workflowExecutor = new WorkflowExecutor(apiClient, WORKER_POLL_INTERVAL_MILLIS);

        try {
            // Starts polling for the tasks of every @WorkerTask method in Workers.
            workflowExecutor.initWorkersFromInstances(List.of(new Workers()));

            // Register the agent that the workflow's AGENT task runs. The runtime gets a client
            // of its own, because closing the runtime also shuts down the client it was given.
            try (var runtime = new AgentRuntime(settings.createApiClient())) {
                runtime.deploy(agent);
            }

            // Overwrite any earlier version, and register a task definition for each SIMPLE task
            // that the server does not know yet.
            buildWorkflow(workflowExecutor).registerWorkflow(true, true);
            System.out.println(
                    "Registered workflow " + WORKFLOW_NAME + ", version " + WORKFLOW_VERSION);

            String workflowId = startWorkflow(workflowExecutor);
            System.out.println(
                    "Workflow URL: " + settings.serverBaseUrl() + "/execution/" + workflowId);

            waitUntilWebhookReady(new WorkflowClient(apiClient), workflowId);
            // Exercise 1: Store a row in QuerySqliteDb.DATABASE_PATH for each completed send_email
            // task, matching on getTaskDefName(): each task's getReferenceTaskName() is unique from
            // Exercise 2 on. Read each result from getOutputData(); numbers are Integer or Long.
            System.out.println(WAIT_TASK_REF + " is ready");
            System.out.println(
                    "Before sending the webhook, start the agent tool workers with "
                            + "`./gradlew serve-agent`.");
            System.out.println("Webhook URL: " + settings.webhookEndpointUrl());
            return 0;
        } finally {
            workflowExecutor.shutdown();
            apiClient.shutdown();
        }
    }
}
