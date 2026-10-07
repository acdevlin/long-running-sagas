// Register and start a durable webhook-driven workflow.
//
// The deploy-workflow step keeps its local workers running until the workflow reaches the
// WAIT_FOR_WEBHOOK task, then exits. Conductor keeps the workflow suspended until the
// send-webhook step sends a callback; the serve-agent step runs the local tools needed after it
// resumes.

package main

import (
	"context"
	"fmt"
	"math"
	"strings"
	"time"

	"github.com/conductor-sdk/conductor-go/sdk/ai"
	"github.com/conductor-sdk/conductor-go/sdk/client"
	"github.com/conductor-sdk/conductor-go/sdk/model"
	"github.com/conductor-sdk/conductor-go/sdk/worker"
	"github.com/conductor-sdk/conductor-go/sdk/workflow"
	"github.com/conductor-sdk/conductor-go/sdk/workflow/executor"
	"webhookscodelab/settings"
	"webhookscodelab/utils"
)

const (
	workflowName    = "wait_for_webhook_demo_" + settings.Language
	workflowVersion = 1
	waitTaskRef     = "wait_for_webhook_ref"

	workflowTimeoutSeconds = 7 * 24 * 60 * 60
	readinessTimeout       = 60 * time.Second
	readinessPollInterval  = time.Second

	// Shown in the workflow's description in the Orkes Conductor UI, and in every
	// email this version sends, so you can tell the language versions apart.
	codelabLanguage = "Go"
)

// taskOutput returns an expression for part of a task's output, for example
// "${wait_for_webhook_ref.output.agent_input}". The SDK's own tasks have an OutputRef method that
// does the same.
func taskOutput(task model.WorkflowTask, path string) string {
	return "${" + task.TaskReferenceName + ".output." + path + "}"
}

// buildWorkflow builds the workflow definition without registering or starting it.
func buildWorkflow() *model.WorkflowDef {
	// The builder needs an executor only to register or start the workflow itself, and this step
	// registers the finished definition instead.
	wf := workflow.NewConductorWorkflow(nil).
		Name(workflowName).
		Version(workflowVersion).
		Description("Durable wait-for-webhook example (registered from "+codelabLanguage+")").
		// Mark the execution TIMED_OUT if it runs longer than workflowTimeoutSeconds,
		// for example because no webhook arrives. ALERT_ONLY would let it keep running.
		TimeoutPolicy(workflow.TimeOutWorkflow, workflowTimeoutSeconds)

	// Builds every send_email task for the fork, so it takes the subject and body too.
	getEmailsTask := workflow.NewSimpleTask("get_user_emails", "get_user_emails_ref").
		Input("user_ids", "${workflow.input.user_ids}").
		Input("subject", "Hello from "+codelabLanguage).
		Input("body", "Sent by the "+codelabLanguage+" version of the webhooks codelab.")

	// The fork adds getEmailsTask before itself and a JOIN after, so add only the fork.
	sendEmailsFork := workflow.NewDynamicForkTask("send_emails_fork", getEmailsTask)

	webhookWait := utils.WaitForWebhookTask(waitTaskRef, map[string]any{
		// Every language version shares one webhook, so only match
		// payloads sent by this language's send-webhook step.
		"$['language']": settings.Language,
		"$['type']":     "customer",
		// Only resume for a webhook about the same users this execution emailed.
		"$['user_ids']": "${workflow.input.user_ids}",
	})

	agentTask := utils.AgentTask(
		"process_webhook_ref",
		utils.WebhookAgentName,
		taskOutput(webhookWait, "agent_input"),
	)

	wf.Add(sendEmailsFork).
		OutputParameters(map[string]any{"agent_response": taskOutput(agentTask, "text")})

	// The SDK's builder has no WAIT_FOR_WEBHOOK or AGENT tasks, and code outside the SDK can't add
	// new kinds of task to it, so add these two to the definition that it builds.
	definition := wf.ToWorkflowDef()
	definition.Tasks = append(definition.Tasks, webhookWait, agentTask)
	// Lists the input that every execution needs. Conductor shows it in the workflow definition
	// but does not require it when a workflow starts.
	definition.InputParameters = []string{"user_ids"}
	return definition
}

// startWorkflow starts one workflow execution and returns its execution ID.
func startWorkflow(workflowExecutor *executor.WorkflowExecutor) (string, error) {
	return workflowExecutor.StartWorkflow(&model.StartWorkflowRequest{
		Name:    workflowName,
		Version: workflowVersion,
		Input:   map[string]any{"user_ids": settings.UserIDs},
	})
}

// waitUntilWebhookReady waits until the execution reaches its WAIT_FOR_WEBHOOK task.
func waitUntilWebhookReady(
	workflowExecutor *executor.WorkflowExecutor, workflowID string,
) (*model.Workflow, error) {
	deadline := time.Now().Add(readinessTimeout)

	for time.Now().Before(deadline) {
		execution, err := workflowExecutor.GetWorkflow(workflowID, true)
		if err != nil {
			return nil, fmt.Errorf("get workflow %s: %w", workflowID, err)
		}

		for _, task := range execution.Tasks {
			if task.ReferenceTaskName == waitTaskRef && task.Status == model.InProgressTask {
				return execution, nil
			}
		}

		switch execution.Status {
		case model.CompletedWorkflow, model.FailedWorkflow, model.TimedOutWorkflow,
			model.TerminatedWorkflow:
			return nil, fmt.Errorf("workflow entered terminal status %s", execution.Status)
		}

		time.Sleep(readinessPollInterval)
	}

	return nil, fmt.Errorf("workflow did not reach %s within %d seconds", waitTaskRef,
		int(readinessTimeout.Seconds()))
}

// emailRow is one completed send_email task's output, checked against the emails table's columns.
type emailRow struct {
	sentTime   int64
	subject    string
	recipients string
}

// getCompletedEmailOutputs returns the checked output of every completed send_email task.
func getCompletedEmailOutputs(execution *model.Workflow) ([]emailRow, error) {
	var emailTasks []model.Task
	for _, task := range execution.GetCompletedTasks() {
		if task.TaskDefName == utils.SendEmailTaskName {
			emailTasks = append(emailTasks, task)
		}
	}
	// No completed send_email task means no email was sent, so fail rather than report success.
	if len(emailTasks) == 0 {
		return nil, fmt.Errorf("no completed %s task outputs were found", utils.SendEmailTaskName)
	}

	// Check every output before inserting any, so a malformed one fails with a message naming its
	// task instead of a database error or a panic.
	rows := make([]emailRow, 0, len(emailTasks))
	for _, task := range emailTasks {
		// JSON numbers arrive as float64, so sent_time must be a whole float64.
		sentTime, sentTimeOK := task.OutputData["sent_time"].(float64)
		subject, subjectOK := task.OutputData["subject"].(string)
		recipients, recipientsOK := task.OutputData["recipients"].(string)
		var invalidFields []string
		if !sentTimeOK || sentTime != math.Trunc(sentTime) {
			invalidFields = append(invalidFields, "sent_time")
		}
		if !subjectOK {
			invalidFields = append(invalidFields, "subject")
		}
		if !recipientsOK {
			invalidFields = append(invalidFields, "recipients")
		}
		if len(invalidFields) > 0 {
			return nil, fmt.Errorf("completed task %s has missing or invalid fields: %s",
				task.ReferenceTaskName, strings.Join(invalidFields, ", "))
		}
		rows = append(rows, emailRow{int64(sentTime), subject, recipients})
	}
	return rows, nil
}

// storeEmailOutputs inserts every email row in one database transaction, and returns the number of
// rows inserted.
func storeEmailOutputs(rows []emailRow) (int, error) {
	db, err := utils.OpenDatabase(true)
	if err != nil {
		return 0, err
	}
	defer db.Close()

	// Use a single DB transaction to avoid partial insert failures. Rollback does nothing once the
	// transaction is committed.
	tx, err := db.Begin()
	if err != nil {
		return 0, err
	}
	defer tx.Rollback()

	for _, row := range rows {
		if _, err := tx.Exec(
			"INSERT INTO emails (sent_time, subject, recipients) VALUES (?, ?, ?)",
			row.sentTime, row.subject, row.recipients,
		); err != nil {
			return 0, err
		}
	}
	if err := tx.Commit(); err != nil {
		return 0, err
	}
	return len(rows), nil
}

// deployWaitForWebhookWorkflow runs the deploy-workflow step.
func deployWaitForWebhookWorkflow() error {
	cfg, err := settings.Load()
	if err != nil {
		return err
	}
	// Build the agent first, so a malformed model setting fails before any worker starts.
	agent, err := utils.NewWebhookAgent(cfg)
	if err != nil {
		return err
	}

	apiClient := client.NewAPIClientFromEnv()
	// Polls for the tasks of every worker in utils.Workers until this step's process exits. Its
	// Shutdown method would stop them sooner, but logs misleading errors as it does.
	taskRunner := worker.NewTaskRunnerWithApiClient(apiClient)
	if err := taskRunner.RegisterWorkers(utils.Workers()...); err != nil {
		return err
	}

	// Register the agent that the workflow's AGENT task runs.
	agentRuntime := ai.NewRuntimeWithClient(apiClient, ai.Config{})
	if _, err := agentRuntime.Deploy(context.Background(), agent); err != nil {
		return err
	}

	workflowExecutor := executor.NewWorkflowExecutor(apiClient)
	// Overwrite any earlier version of the workflow with the same name and version.
	if err := workflowExecutor.RegisterWorkflow(true, buildWorkflow()); err != nil {
		return fmt.Errorf("register workflow %s: %w", workflowName, err)
	}
	fmt.Printf("Registered workflow %s, version %d\n", workflowName, workflowVersion)

	workflowID, err := startWorkflow(workflowExecutor)
	if err != nil {
		return fmt.Errorf("start workflow %s: %w", workflowName, err)
	}
	fmt.Printf("Workflow URL: %s/execution/%s\n", cfg.ServerBaseURL(), workflowID)

	execution, err := waitUntilWebhookReady(workflowExecutor, workflowID)
	if err != nil {
		return err
	}
	rows, err := getCompletedEmailOutputs(execution)
	if err != nil {
		return err
	}
	storedCount, err := storeEmailOutputs(rows)
	if err != nil {
		return fmt.Errorf("store email records in %s: %w", utils.DatabasePath, err)
	}
	fmt.Printf("Stored %d email record(s) in %s\n", storedCount, utils.DatabasePath)
	fmt.Println(waitTaskRef + " is ready")
	fmt.Println("Before sending the webhook, start the agent tool workers with " +
		"`go run . serve-agent`, or restart them if you've changed the code since they started.")
	fmt.Println("Webhook URL: " + cfg.WebhookEndpointURL())
	return nil
}
