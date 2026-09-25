package io.orkes.codelab.webhooks;

import io.orkes.codelab.webhooks.utils.CreateSqliteDb;
import io.orkes.codelab.webhooks.utils.QuerySqliteDb;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Entry point for every step of the Java webhooks codelab. Run a step from this folder with {@code
 * ./gradlew <step>}, for example {@code ./gradlew deploy-workflow}.
 */
public final class Main {

    /** One codelab step, which returns the exit code for the process. */
    @FunctionalInterface
    private interface Step {
        int run() throws Exception;
    }

    private Main() {}

    public static void main(String[] args) throws Exception {
        Map<String, Step> steps = new LinkedHashMap<>();
        steps.put("create-db", CreateSqliteDb::run);
        steps.put("deploy-workflow", DeployWaitForWebhookWorkflow::run);
        steps.put("serve-agent", ServeWebhookAgent::run);
        steps.put("send-webhook", SendWebhookPayload::run);
        steps.put("query-db", QuerySqliteDb::run);

        Step step = args.length == 1 ? steps.get(args[0]) : null;
        if (step == null) {
            System.err.println("Usage: ./gradlew <" + String.join("|", steps.keySet()) + ">");
            System.exit(1);
        }
        System.exit(step.run());
    }
}
