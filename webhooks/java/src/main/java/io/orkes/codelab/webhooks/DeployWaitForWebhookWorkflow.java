package io.orkes.codelab.webhooks;

import com.netflix.conductor.client.http.WorkflowClient;
import com.netflix.conductor.common.metadata.tasks.Task;
import com.netflix.conductor.common.metadata.workflow.WorkflowDef;
import com.netflix.conductor.common.run.Workflow;
import com.netflix.conductor.sdk.workflow.def.ConductorWorkflow;
import com.netflix.conductor.sdk.workflow.def.tasks.DynamicFork;
import com.netflix.conductor.sdk.workflow.def.tasks.SimpleTask;
import com.netflix.conductor.sdk.workflow.executor.WorkflowExecutor;

import io.orkes.codelab.webhooks.utils.AgentTask;
import io.orkes.codelab.webhooks.utils.QuerySqliteDb;
import io.orkes.codelab.webhooks.utils.WaitForWebhookTask;
import io.orkes.codelab.webhooks.utils.WebhookAgent;
import io.orkes.codelab.webhooks.utils.Workers;

import org.conductoross.conductor.ai.AgentRuntime;

import java.sql.DriverManager;
import java.sql.SQLException;
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

        // Builds every send_email task for the fork, so it takes the subject and body too.
        var getEmailsTask =
                new SimpleTask("get_user_emails", "get_user_emails_ref")
                        .input("user_ids", ConductorWorkflow.input.get("user_ids"))
                        .input("subject", subject)
                        .input("body", body);

        // The fork adds getEmailsTask before itself and a join after, so add only the fork.
        var sendEmailsFork = new DynamicFork("send_emails_fork", getEmailsTask);

        Map<String, Object> matches = new LinkedHashMap<>();
        // Every language version shares one webhook, so only match
        // payloads sent by this language's send-webhook step.
        matches.put("$['language']", Settings.LANGUAGE);
        matches.put("$['type']", "customer");
        // Only resume for a webhook about the same users this execution emailed.
        matches.put("$['user_ids']", ConductorWorkflow.input.get("user_ids"));
        var webhookWait = new WaitForWebhookTask(WAIT_TASK_REF, matches);

        var agentTask =
                new AgentTask(
                        "process_webhook_ref",
                        WebhookAgent.NAME,
                        webhookWait.taskOutput.get("agent_input"));

        workflow.add(sendEmailsFork);
        workflow.add(webhookWait);
        workflow.add(agentTask);
        workflow.setWorkflowOutput(Map.of("agent_response", agentTask.taskOutput.get("text")));

        return workflow;
    }

    /** Start one workflow execution and return its execution ID. */
    private static String startWorkflow(WorkflowExecutor workflowExecutor) {
        return workflowExecutor.startWorkflow(
                WORKFLOW_NAME, WORKFLOW_VERSION, Map.of("user_ids", Settings.USER_IDS));
    }

    /** Wait until the execution reaches its WAIT_FOR_WEBHOOK task. */
    private static Workflow waitUntilWebhookReady(WorkflowClient workflowClient, String workflowId)
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
                return execution;
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

    /** Insert all completed email outputs in one database transaction. */
    private static int storeEmailOutputs(Workflow execution) throws SQLException {
        List<Map<String, Object>> emails =
                execution.getTasks().stream()
                        .filter(task -> "send_email".equals(task.getTaskDefName()))
                        .filter(task -> task.getStatus() == Task.Status.COMPLETED)
                        .map(task -> task.getOutputData())
                        .toList();
        String insertSql =
                """
                INSERT INTO emails (sent_time, subject, recipients)
                VALUES (?, ?, ?)
                """;

        try (var connection =
                        DriverManager.getConnection("jdbc:sqlite:" + QuerySqliteDb.DATABASE_PATH);
                var insert = connection.prepareStatement(insertSql)) {
            // Use a single DB transaction to avoid partial insert failures.
            connection.setAutoCommit(false);
            for (Map<String, Object> email : emails) {
                // The server returns whole numbers as Integer or Long, depending on their size.
                insert.setLong(1, ((Number) email.get("sent_time")).longValue());
                insert.setString(2, (String) email.get("subject"));
                insert.setString(3, (String) email.get("recipients"));
                insert.executeUpdate();
            }
            connection.commit();
        }
        return emails.size();
    }

    public static int run() throws InterruptedException, TimeoutException, SQLException {
        Settings settings = Settings.current();
        // Build the agent first, so a malformed model setting fails before any worker starts.
        var agent = WebhookAgent.create();
        var apiClient = settings.createApiClient();
        var workflowExecutor = new WorkflowExecutor(apiClient, WORKER_POLL_INTERVAL_MILLIS);

        try {
            // Starts polling for the tasks of every @WorkerTask method in Workers.
            workflowExecutor.initWorkersFromInstances(List.<Object>of(new Workers()));

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

            Workflow execution = waitUntilWebhookReady(new WorkflowClient(apiClient), workflowId);
            int storedCount = storeEmailOutputs(execution);
            System.out.println(
                    "Stored " + storedCount + " email record(s) in " + QuerySqliteDb.DATABASE_PATH);
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
