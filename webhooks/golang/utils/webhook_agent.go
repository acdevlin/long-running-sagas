// Agent definition that is used in the wait-for-webhook example workflow. The agent is configured
// to use the LLM model and integration from the settings package, and summarizes stored email
// activity with its tools.

package utils

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"github.com/conductor-sdk/conductor-go/sdk/ai"
	"github.com/conductor-sdk/conductor-go/sdk/ai/tool"
	"webhookscodelab/settings"
)

// Read-only database tools for the agent. The serve-agent step runs each tool as a Conductor
// worker task, and the agent receives the tool's result as JSON.
var (
	summarizeEmailActivityTool = tool.Func(
		"summarize_email_activity", summarizeEmailActivity,
		"Return the total number of stored emails and the number sent to each recipient. "+
			"Call this first.")
	getRecipientEmailHistoryTool = tool.Func(
		"get_recipient_email_history", getRecipientEmailHistory,
		"Return every stored email for one recipient. Pass the exact recipient email address "+
			"from summarize_email_activity.")
)

// summarizeEmailActivity runs the summarize_email_activity tool, which takes no arguments.
func summarizeEmailActivity(_ context.Context, _ struct{}) (map[string]any, error) {
	recipientActivity, err := FetchEmailActivity()
	if err != nil {
		return nil, err
	}
	var totalEmails int64
	for _, recipient := range recipientActivity {
		totalEmails += recipient.EmailCount
	}
	// has_activity tells the agent whether there is any recipient history to look up.
	return map[string]any{
		"total_emails":       totalEmails,
		"has_activity":       len(recipientActivity) > 0,
		"recipient_activity": recipientActivity,
	}, nil
}

// recipientInput holds the get_recipient_email_history tool's argument.
type recipientInput struct {
	Recipient string `json:"recipient"`
}

// getRecipientEmailHistory runs the get_recipient_email_history tool.
func getRecipientEmailHistory(_ context.Context, in recipientInput) (map[string]any, error) {
	// FetchEmails returns every email for an empty recipient, so require one.
	if in.Recipient == "" {
		return nil, errors.New("a recipient email address is required")
	}
	emails, err := FetchEmails(in.Recipient)
	if err != nil {
		return nil, err
	}
	return map[string]any{
		"recipient":   in.Recipient,
		"email_count": len(emails),
		"emails":      emails,
	}, nil
}

// WebhookAgentName is the name the agent is deployed under, which the workflow's AGENT task
// refers to.
const WebhookAgentName = "webhook_customer_service_" + settings.Language

// NewWebhookAgent builds the agent definition, checking that the LLM model setting is well formed.
func NewWebhookAgent(cfg settings.Settings) (*ai.Agent, error) {
	_, model, found := strings.Cut(cfg.LLMModel, "/")
	if !found {
		return nil, fmt.Errorf("CONDUCTOR_AGENT_LLM_MODEL must use the 'provider/model' format, "+
			"for example 'openai/gpt-5-nano'; got %q", cfg.LLMModel)
	}

	return &ai.Agent{
		Name:  WebhookAgentName,
		Model: cfg.IntegrationName + "/" + model,
		Instructions: "You are an email activity analyst. First call summarize_email_activity. " +
			"If has_activity is false, do not call get_recipient_email_history; return a " +
			"concise digest stating that there is no stored email activity. Otherwise, " +
			"identify the recipient with the greatest email_count, breaking ties by choosing " +
			"the alphabetically first recipient. Then call get_recipient_email_history with " +
			"that exact recipient. Base every factual claim on the tool results and return a " +
			"concise, multi-line activity digest.",
		Tools: ai.Tools(summarizeEmailActivityTool, getRecipientEmailHistoryTool),
		// Enough turns for both tool calls and the final digest, with two to spare.
		MaxTurns:    5,
		Temperature: ai.Ptr(0.2),
	}, nil
}
