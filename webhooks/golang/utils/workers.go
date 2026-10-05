// Package utils holds the workers, agent, task helpers and database code that the codelab's steps
// use.
package utils

import (
	"context"
	"fmt"

	"github.com/conductor-sdk/conductor-go/sdk/worker"
)

// Workers returns a worker for each task that the workflow runs, for the deploy-workflow step's
// TaskRunner to poll.
func Workers() []worker.Worker {
	return []worker.Worker{
		// Exercise 2: Register getUserEmails for "get_user_emails" instead.
		worker.NewSimpleTypedWorker("get_user_email", getUserEmail),
		// Exercise 2: Pass worker.WithBatchSize, which is 1 by default, so this worker sends the
		// forked emails in parallel.
		worker.NewSimpleTypedWorker("send_email", sendEmail),
	}
}

// getUserEmailInput is the input of a get_user_email task. The SDK fills each field from the
// input parameter named in its json tag.
type getUserEmailInput struct {
	UserID string `json:"user_id"`
}

// Exercise 2: Change to getUserEmails, taking a list of user IDs. Return the fork's send_email
// tasks under "forkedTasks", each of type "SIMPLE" with a unique taskReferenceName (Exercise 3
// repeats a user ID), and under "forkedTasksInputs" a map from each name to that task's input.

// getUserEmail returns the email address associated with a user, as the task output "result".
func getUserEmail(_ context.Context, in getUserEmailInput) (map[string]any, error) {
	return map[string]any{"result": in.UserID + "@example.com"}, nil
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
	// Exercise 1: Return this email's fields for the emails table, with sent_time as a Unix
	// timestamp in seconds.
	return nil, nil
}
