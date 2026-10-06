// Send a webhook payload to the specified Orkes webhook endpoint.

package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"webhookscodelab/settings"
)

// sendWebhookPayload runs the send-webhook step.
func sendWebhookPayload() error {
	cfg, err := settings.Load()
	if err != nil {
		return err
	}

	payload := map[string]any{
		// The same list as the workflow's input, which the WAIT_FOR_WEBHOOK task matches on.
		"user_ids": settings.UserIDs,
		"type":     "customer",
		// The WAIT_FOR_WEBHOOK task passes this to the AGENT task as its prompt.
		"agent_input": "Create an email activity digest. First summarize all stored email " +
			"activity. If there is no stored activity, return a concise no-activity digest. " +
			"Otherwise, inspect the history of the recipient with the greatest number of " +
			"emails before returning your final analysis.",
		// Every language version shares one webhook; this key selects this
		// language's workflow (see the matches in the deploy-workflow step).
		"language": settings.Language,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	request, err := http.NewRequest(http.MethodPost, cfg.WebhookEndpointURL(), bytes.NewReader(body))
	if err != nil {
		return err
	}
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Accept", "application/json")
	request.Header.Set("source", cfg.SourceHeader)

	httpClient := &http.Client{Timeout: 30 * time.Second}
	response, err := httpClient.Do(request)
	if err != nil {
		return err
	}
	defer response.Body.Close()

	responseBody, err := io.ReadAll(response.Body)
	if err != nil {
		return err
	}
	fmt.Printf("Status: %d\n", response.StatusCode)
	fmt.Printf("Response: %s\n", responseBody)

	// Return an error for HTTP error responses (for example, 4xx and 5xx).
	if response.StatusCode >= 400 {
		return fmt.Errorf("webhook request failed with status %d", response.StatusCode)
	}

	fmt.Println("Webhook was accepted by Orkes Conductor.")
	return nil
}
