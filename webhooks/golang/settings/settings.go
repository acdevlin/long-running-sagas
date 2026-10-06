// Package settings holds the settings for the Go version of the webhooks codelab.
//
// Account-specific values are read from environment variables so that every language version of
// this codelab shares one configuration. Copy .env.example at the repository root to .env and
// fill it in; Load reads it. Variables already exported in your shell take precedence over the
// ones in .env, for example:
//
//	export CONDUCTOR_AGENT_LLM_MODEL=anthropic/claude-sonnet-4-6
//	export CONDUCTOR_INTEGRATION_NAME=my_anthropic_integration
package settings

import (
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/joho/godotenv"
)

// Language identifies this language version in its workflow and agent names and in the webhook
// payload, so every language version can share one webhook.
const Language = "golang"

// The workflow sends an email to each user ID in this list.
// Exercise 3: Repeat one user ID so the agent has a clear most-active
// recipient to identify from the stored email activity.
var UserIDs = []string{"alex", "user_1", "user_2", "user_555"}

// Settings holds the account-specific values, read from the shell or .env.
type Settings struct {
	// ConductorServerURL is set by CONDUCTOR_SERVER_URL; the webhook URL is derived from it.
	ConductorServerURL string
	// LLMModel is set by CONDUCTOR_AGENT_LLM_MODEL, in 'provider/model' format.
	LLMModel string
	// IntegrationName is set by CONDUCTOR_INTEGRATION_NAME.
	IntegrationName string
	// WebhookID is set by WEBHOOK_ID.
	WebhookID string
	// SourceHeader is set by WEBHOOK_SOURCE_HEADER.
	SourceHeader string
}

// Load adds the values in .env at the repository root to the environment, then reads the
// settings. Call it before creating any Conductor client, so the SDK also picks up
// CONDUCTOR_SERVER_URL, CONDUCTOR_AUTH_KEY and CONDUCTOR_AUTH_SECRET from .env.
func Load() (Settings, error) {
	envPath := filepath.Join(repositoryRoot(), ".env")
	// godotenv.Load skips any variable that is already set in the shell.
	if err := godotenv.Load(envPath); err != nil && !errors.Is(err, fs.ErrNotExist) {
		return Settings{}, fmt.Errorf("load %s: %w", envPath, err)
	}

	return Settings{
		ConductorServerURL: read("CONDUCTOR_SERVER_URL", "https://developer.orkescloud.com/api"),
		LLMModel:           read("CONDUCTOR_AGENT_LLM_MODEL", "openai/gpt-5-nano"),
		IntegrationName:    read("CONDUCTOR_INTEGRATION_NAME", "your_integration_name_here"),
		WebhookID:          read("WEBHOOK_ID", "your_webhook_id_here"),
		SourceHeader:       read("WEBHOOK_SOURCE_HEADER", "your_source_header_here"),
	}, nil
}

// ServerBaseURL returns the Conductor cluster URL without its /api suffix, which the UI and
// webhooks share.
func (s Settings) ServerBaseURL() string {
	return strings.TrimSuffix(strings.TrimRight(s.ConductorServerURL, "/"), "/api")
}

// WebhookEndpointURL returns the webhook endpoint on the same Conductor cluster as the API.
func (s Settings) WebhookEndpointURL() string {
	return s.ServerBaseURL() + "/webhook/" + s.WebhookID
}

// read returns a variable from the shell or .env, treating an empty value as unset.
func read(name, defaultValue string) string {
	if value := strings.TrimSpace(os.Getenv(name)); value != "" {
		return value
	}
	return defaultValue
}

// repositoryRoot returns the folder three levels above this file. go run compiles each step with
// the full path of every source file, so this works from any folder.
func repositoryRoot() string {
	_, thisFile, _, _ := runtime.Caller(0)
	return filepath.Join(filepath.Dir(thisFile), "..", "..", "..")
}
