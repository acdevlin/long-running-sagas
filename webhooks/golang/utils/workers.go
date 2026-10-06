// Package utils holds the workers, agent, task helpers and database code that the codelab's steps
// use.
package utils

import (
	"context"
	"fmt"
	"time"

	"github.com/conductor-sdk/conductor-go/sdk/worker"
)

// Workers returns a worker for each task that the workflow runs, for the deploy-workflow step's
// TaskRunner to poll.
func Workers() []worker.Worker {
	return []worker.Worker{
		worker.NewSimpleTypedWorker("get_user_emails", getUserEmails),
		// A batch size above the default of 1 lets this worker send the forked emails in parallel.
		worker.NewSimpleTypedWorker("send_email", sendEmail, worker.WithBatchSize(10)),
	}
}

// getUserEmailsInput is the input of a get_user_emails task. The SDK fills each field from the
// input parameter named in its json tag.
type getUserEmailsInput struct {
	UserIDs []string `json:"user_ids"`
	Subject string   `json:"subject"`
	Body    string   `json:"body"`
}

// getUserEmails returns a send_email task for each user's email address, for the dynamic fork.
func getUserEmails(_ context.Context, in getUserEmailsInput) (map[string]any, error) {
	tasks := []map[string]any{}
	inputs := map[string]any{}
	for index, userID := range in.UserIDs {
		// The index keeps each reference name unique, even when a user ID repeats.
		referenceName := fmt.Sprintf("send_email_%d", index)
		tasks = append(tasks, map[string]any{
			"name":              "send_email",
			"taskReferenceName": referenceName,
			"type":              "SIMPLE",
		})
		inputs[referenceName] = map[string]any{
			"recipients": userID + "@example.com",
			"subject":    in.Subject,
			"body":       in.Body,
		}
	}
	// NewDynamicForkTask reads the forked tasks and their inputs from these two output keys.
	return map[string]any{"forkedTasks": tasks, "forkedTasksInputs": inputs}, nil
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
