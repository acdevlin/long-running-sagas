/**
 * Register and start a durable webhook-driven workflow.
 *
 * The program keeps its local workers running until the workflow reaches the WAIT_FOR_WEBHOOK
 * task, then exits. Conductor keeps the workflow suspended until the send-webhook step sends a
 * callback; the serve-agent step runs the local tools needed after it resumes.
 */

import { DatabaseSync } from "node:sqlite";
import { setTimeout as sleep } from "node:timers/promises";
import {
  ConductorWorkflow,
  TaskHandler,
  WorkflowExecutor,
  createConductorClient,
  simpleTask,
  type Workflow,
  type WorkflowTask,
} from "@io-orkes/conductor-javascript";
import { AgentRuntime } from "@io-orkes/conductor-javascript/agents";
import { settings } from "./settings.ts";
import { agentTask } from "./utils/agentTask.ts";
import { DATABASE_PATH } from "./utils/querySqliteDb.ts";
import { waitForWebhookTask } from "./utils/waitForWebhookTask.ts";
import { webhookAgent } from "./utils/webhookAgent.ts";
// Registers the @worker methods in this file, which the TaskHandler in main then runs.
import "./utils/workers.ts";

const WORKFLOW_NAME = `wait_for_webhook_demo_${settings.language}`;
const WORKFLOW_VERSION = 1;
const WAIT_TASK_REF = "wait_for_webhook_ref";

const WORKFLOW_TIMEOUT_SECONDS = 7 * 24 * 60 * 60;
const READINESS_TIMEOUT_MS = 60_000;
const POLL_INTERVAL_MS = 1_000;
const TERMINAL_STATUSES: ReadonlySet<Workflow["status"]> = new Set([
  "COMPLETED",
  "FAILED",
  "TIMED_OUT",
  "TERMINATED",
]);

// Shown in the workflow's description in the Orkes Conductor UI, and in every
// email this version sends, so you can tell the language versions apart.
const CODELAB_LANGUAGE = "TypeScript";

/** Expression for part of a task's output, for example "${get_user_email_ref.output.result}". */
function taskOutput(task: WorkflowTask, jsonPath: string): string {
  return `\${${task.taskReferenceName}.output.${jsonPath}}`;
}

/** Build the workflow definition without registering or starting it. */
function buildWorkflow(workflowExecutor: WorkflowExecutor): ConductorWorkflow {
  const workflow = new ConductorWorkflow(workflowExecutor, WORKFLOW_NAME, WORKFLOW_VERSION)
    .description(`Durable wait-for-webhook example (registered from ${CODELAB_LANGUAGE})`)
    // Mark the execution TIMED_OUT if it runs longer than WORKFLOW_TIMEOUT_SECONDS,
    // for example because no webhook arrives. ALERT_ONLY would let it keep running.
    .timeoutPolicy("TIME_OUT_WF")
    .timeoutSeconds(WORKFLOW_TIMEOUT_SECONDS);

  // Exercise 2: Replace this with one get_user_emails task that resolves every address in
  // workflow.input("user_ids"), so the number of emails is decided at runtime. Pass it the
  // subject and body as well, for the forked send_email tasks.
  const getEmailTask = simpleTask("get_user_email_ref", "get_user_email", {
    user_id: workflow.input("user_id"),
  });

  // Exercise 2: Send the emails with utils/dynamicForkTask.ts (the SDK's dynamicForkTask can't
  // use tasks chosen at runtime), then add joinTask(referenceName, []) straight after it, so it
  // waits for every branch.
  const sendEmailTask = simpleTask("send_email_ref", "send_email", {
    recipients: taskOutput(getEmailTask, "result"),
    subject: `Hello from ${CODELAB_LANGUAGE}`,
    body: `Sent by the ${CODELAB_LANGUAGE} version of the webhooks codelab.`,
  });

  const webhookWait = waitForWebhookTask(WAIT_TASK_REF, {
    // Every language version shares one webhook, so only match
    // payloads sent by this language's send-webhook step.
    "$['language']": settings.language,
    "$['type']": "customer",
    // Exercise 2: Change to 'user_ids'. Be sure the payload sent by
    // sendWebhookPayload.ts matches the key you use here.
    "$['user_id']": workflow.input("user_id"),
  });

  const invokeAgentTask = agentTask(
    "process_webhook_ref",
    webhookAgent.name,
    taskOutput(webhookWait, "agent_input"),
  );

  return workflow
    .add([getEmailTask, sendEmailTask, webhookWait, invokeAgentTask])
    .outputParameter("agent_response", taskOutput(invokeAgentTask, "text"));
}

/** Start one workflow execution and return its execution ID. */
function startWorkflow(workflowExecutor: WorkflowExecutor): Promise<string> {
  return workflowExecutor.startWorkflow({
    name: WORKFLOW_NAME,
    version: WORKFLOW_VERSION,
    input: { user_id: settings.userId },
  });
}

/** Wait until the execution reaches its WAIT_FOR_WEBHOOK task. */
async function waitUntilWebhookReady(
  workflowExecutor: WorkflowExecutor,
  workflowId: string,
): Promise<Workflow> {
  // Unlike Date.now(), performance.now() is unaffected by changes to the system clock.
  const deadline = performance.now() + READINESS_TIMEOUT_MS;

  while (performance.now() < deadline) {
    const execution = await workflowExecutor.getWorkflow(workflowId, true);

    const waitTask = execution.tasks?.find((task) => task.referenceTaskName === WAIT_TASK_REF);
    if (waitTask?.status === "IN_PROGRESS") {
      return execution;
    }

    if (TERMINAL_STATUSES.has(execution.status)) {
      throw new Error(`Workflow entered terminal status ${execution.status}`);
    }

    await sleep(POLL_INTERVAL_MS);
  }

  throw new Error(
    `Workflow did not reach ${WAIT_TASK_REF} within ${READINESS_TIMEOUT_MS / 1000} seconds`,
  );
}

/** Insert all completed email outputs in one database transaction. */
function storeEmailOutputs(execution: Workflow): number {
  const emails = (execution.tasks ?? [])
    .filter((task) => task.taskDefName === "send_email" && task.status === "COMPLETED")
    .map((task) => task.outputData as { sent_time: number; subject: string; recipients: string });

  const database = new DatabaseSync(DATABASE_PATH);
  try {
    const insert = database.prepare(
      "INSERT INTO emails (sent_time, subject, recipients) VALUES (?, ?, ?)",
    );
    // Use a single DB transaction to avoid partial insert failures.
    database.exec("BEGIN");
    try {
      for (const email of emails) {
        insert.run(email.sent_time, email.subject, email.recipients);
      }
      database.exec("COMMIT");
    } catch (error) {
      // SQLite rolls back by itself after some errors, and a second ROLLBACK would hide them.
      if (database.isTransaction) database.exec("ROLLBACK");
      throw error;
    }
  } finally {
    database.close();
  }
  return emails.length;
}

async function main(): Promise<void> {
  const client = await createConductorClient();
  // Polls for the tasks of every registered @worker method until stopped.
  const taskHandler = new TaskHandler({ client });
  await taskHandler.startWorkers();

  try {
    // Register the agent that the workflow's AGENT task runs.
    await new AgentRuntime(client).deploy(webhookAgent);

    const workflowExecutor = new WorkflowExecutor(client);
    // Overwrite any earlier version of the workflow with the same name and version.
    await buildWorkflow(workflowExecutor).register(true);
    console.log(`Registered workflow ${WORKFLOW_NAME}, version ${WORKFLOW_VERSION}`);

    const workflowId = await startWorkflow(workflowExecutor);
    console.log(`Workflow URL: ${settings.serverBaseUrl}/execution/${workflowId}`);

    const execution = await waitUntilWebhookReady(workflowExecutor, workflowId);
    const storedCount = storeEmailOutputs(execution);
    console.log(`Stored ${storedCount} email record(s) in ${DATABASE_PATH}`);
    console.log(`${WAIT_TASK_REF} is ready`);
    console.log(
      "Before sending the webhook, start the agent tool workers with " +
        "`npm run serve-agent`, or restart them if you've changed the code since they started.",
    );
    console.log(`Webhook URL: ${settings.webhookEndpointUrl}`);
  } finally {
    await taskHandler.stopWorkers();
    // The client refreshes its access token in the background, which would keep this process
    // running until it is stopped.
    client.stopBackgroundRefresh();
  }
}

await main();
