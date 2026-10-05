// The Go version of the webhooks codelab. Run a step from this folder with `go run . <step>`, for
// example `go run . deploy-workflow`.
package main

import (
	"fmt"
	"os"
	"strings"

	"webhookscodelab/utils"
)

// steps lists each codelab step's name and the function that runs it.
var steps = []struct {
	name string
	run  func() error
}{
	{"create-db", utils.CreateSqliteDb},
	{"deploy-workflow", deployWaitForWebhookWorkflow},
	{"serve-agent", serveWebhookAgent},
	{"send-webhook", sendWebhookPayload},
	{"query-db", utils.QuerySqliteDb},
}

func main() {
	if len(os.Args) == 2 {
		for _, step := range steps {
			if step.name == os.Args[1] {
				if err := step.run(); err != nil {
					fmt.Fprintf(os.Stderr, "%s: %v\n", step.name, err)
					os.Exit(1)
				}
				return
			}
		}
	}

	names := make([]string, len(steps))
	for index, step := range steps {
		names[index] = step.name
	}
	fmt.Fprintf(os.Stderr, "Usage: go run . <%s>\n", strings.Join(names, "|"))
	os.Exit(1)
}
