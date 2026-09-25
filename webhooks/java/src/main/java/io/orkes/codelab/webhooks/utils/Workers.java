package io.orkes.codelab.webhooks.utils;

import com.netflix.conductor.sdk.workflow.task.InputParam;
import com.netflix.conductor.sdk.workflow.task.WorkerTask;

import java.time.Instant;
import java.util.Map;

/**
 * Worker tasks used by the webhook workflow. The deploy-workflow step registers an instance of this
 * class, and the SDK then polls for each {@code @WorkerTask} method's tasks and runs them here.
 */
public final class Workers {

    // Exercise 2: Change to "get_user_emails", taking a list of user IDs. Return the fork's
    // send_email tasks as a DynamicForkInput: one SimpleTask per address with a unique reference
    // name (Exercise 3 repeats a user ID), and a map from each name to that task's input.
    /**
     * Return the email address associated with a user. The SDK stores it as the output "result".
     */
    @WorkerTask("get_user_email")
    public String getUserEmail(@InputParam("user_id") String userId) {
        return userId + "@example.com";
    }

    // Exercise 2: Raise threadCount in @WorkerTask, which is 1 by default, so this worker sends the
    // forked emails in parallel.
    /** Simulate sending an email. */
    @WorkerTask("send_email")
    public Map<String, Object> sendEmail(
            @InputParam("recipients") String recipients,
            @InputParam("subject") String subject,
            @InputParam("body") String body) {
        System.out.printf(
                "Sending email%nTo: %s%nSubject: %s%nBody: %s%n", recipients, subject, body);
        return Map.of(
                "sent_time", Instant.now().getEpochSecond(),
                "subject", subject,
                "recipients", recipients);
    }
}
