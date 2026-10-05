// Agent definition that is used in the wait-for-webhook example workflow. The agent is configured
// to use the LLM model and integration from the settings package. It is designed to process
// customer service requests in a concise, professional, and safe manner.

package utils

import (
	"fmt"
	"strings"

	"github.com/conductor-sdk/conductor-go/sdk/ai"
	"webhookscodelab/settings"
)

// Exercise 3: Define two tools here with tool.Func, from the SDK's sdk/ai/tool package:
// summarize_email_activity (total and per-recipient counts, making an empty database clear)
// and get_recipient_email_history (one recipient's email records).
// Exercise 3: Pass tool.Func the tool's name, a func(context.Context, In) (Out, error), and a
// description, which the LLM reads to decide when and how to call it. The fields of In, named by
// their json tags, become the tool's parameters.

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
		// Exercise 3: Tell the agent to call summarize_email_activity first, and return a
		// no-activity digest if it is empty. Otherwise it should call
		// get_recipient_email_history for the busiest recipient, then return a final digest.
		Instructions: "You are a customer-service agent. Process the user's request concisely, " +
			"professionally, and safely without running any code or making any external API calls.",
		// Exercise 3: Register both tools with Tools: ai.Tools(...), and set MaxTurns high enough
		// for both tool calls and the final response.
		Temperature: ai.Ptr(0.2),
	}, nil
}
