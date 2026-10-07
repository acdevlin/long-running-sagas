// Package utils holds the workers, agent, task helpers and database code that the codelab's steps
// use.
package utils

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/conductor-sdk/conductor-go/sdk/worker"
)

// SendEmailTaskName is shared by the worker, the forked tasks and the deploy-workflow step's
// storing filter, which must all agree.
const SendEmailTaskName = "send_email"

// The output keys that workflow.NewDynamicForkTask reads the forked tasks and their inputs from.
const (
	forkedTasksKey       = "forkedTasks"
	forkedTasksInputsKey = "forkedTasksInputs"
)

// Workers returns a worker for each task that the workflow runs, for the deploy-workflow step's
// TaskRunner to poll.
func Workers() []worker.Worker {
	return []worker.Worker{
		worker.NewSimpleTypedWorker("get_user_emails", getUserEmails),
		// A batch size above the default of 1 lets this worker send the forked emails in parallel.
		worker.NewSimpleTypedWorker(SendEmailTaskName, sendEmail, worker.WithBatchSize(10)),
	}
}

// getUserEmailsInput is the input of a get_user_emails task. The SDK fills each field from the
// input parameter named in its json tag.
type getUserEmailsInput struct {
	UserIDs []string `json:"user_ids"`
	Subject string   `json:"subject"`
	Body    string   `json:"body"`
}

// getUserEmails returns a send_email task for each user's email address, for the dynamic fork. It
// returns any, not a map: the SDK reports a nil map returned with an error as a COMPLETED task.
func getUserEmails(_ context.Context, in getUserEmailsInput) (any, error) {
	// With no user IDs the fork would send no emails, but the workflow would still wait for its
	// webhook, so fail instead. The SDK leaves UserIDs empty if user_ids is missing.
	if len(in.UserIDs) == 0 {
		return nil, errors.New("at least one user ID is required")
	}

	tasks := []map[string]any{}
	inputs := map[string]any{}
	for index, userID := range in.UserIDs {
		// A blank ID would produce an invalid address such as "@example.com".
		if strings.TrimSpace(userID) == "" {
			return nil, fmt.Errorf("invalid user ID at index %d", index)
		}

		// The index keeps each reference name unique, even when a user ID repeats.
		referenceName := fmt.Sprintf("send_email_%d", index)
		tasks = append(tasks, map[string]any{
			"name":              SendEmailTaskName,
			"taskReferenceName": referenceName,
			"type":              "SIMPLE",
		})
		inputs[referenceName] = map[string]any{
			"recipients": userID + "@example.com",
			"subject":    in.Subject,
			"body":       in.Body,
		}
	}
	return map[string]any{forkedTasksKey: tasks, forkedTasksInputsKey: inputs}, nil
}

// sendEmailInput is the input of a send_email task.
type sendEmailInput struct {
	Recipients string `json:"recipients"`
	Subject    string `json:"subject"`
	Body       string `json:"body"`
}

// sendEmail simulates sending an email.
func sendEmail(_ context.Context, in sendEmailInput) (map[string]any, error) {
	fmt.Printf("Sending email\nTo: %s\nSubject: %s\nBody: %s\n", in.Recipients, in.Subject, in.Body)
	return map[string]any{
		"sent_time":  time.Now().Unix(),
		"subject":    in.Subject,
		"recipients": in.Recipients,
	}, nil
}
