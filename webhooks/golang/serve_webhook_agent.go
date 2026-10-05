// Serve the local database tools used by the post-webhook agent.

package main

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/conductor-sdk/conductor-go/sdk/ai"
	"webhookscodelab/settings"
	"webhookscodelab/utils"
)

// serveWebhookAgent runs the serve-agent step, which deploys the agent and serves its tool workers
// until interrupted.
func serveWebhookAgent() error {
	cfg, err := settings.Load()
	if err != nil {
		return err
	}
	agent, err := utils.NewWebhookAgent(cfg)
	if err != nil {
		return err
	}

	// Cancelled when you press Ctrl+C.
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	fmt.Println("Serving the agent's tool workers. Press Ctrl+C to stop.")
	// Blocks until ctx is cancelled, then stops the workers and returns ctx's error.
	err = ai.NewRuntime(ai.Config{}).Serve(ctx, agent)
	if errors.Is(err, context.Canceled) {
		return nil
	}
	return err
}
