package io.orkes.codelab.webhooks.utils;

import com.netflix.conductor.sdk.workflow.def.tasks.DynamicForkInput;
import com.netflix.conductor.sdk.workflow.def.tasks.SimpleTask;
import com.netflix.conductor.sdk.workflow.def.tasks.Task;
import com.netflix.conductor.sdk.workflow.task.InputParam;
import com.netflix.conductor.sdk.workflow.task.WorkerTask;

import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Worker tasks used by the webhook workflow. The deploy-workflow step registers an instance of this
 * class, and the SDK then polls for each {@code @WorkerTask} method's tasks and runs them here.
 */
public final class Workers {

    /** Return one send_email task per user's email address, for the workflow's dynamic fork. */
    @WorkerTask("get_user_emails")
    public DynamicForkInput getUserEmails(
            @InputParam("user_ids") List<String> userIds,
            @InputParam("subject") String subject,
            @InputParam("body") String body) {
        List<Task<?>> tasks = new ArrayList<>();
        Map<String, Object> inputs = new LinkedHashMap<>();
        for (int index = 0; index < userIds.size(); index++) {
            // The index keeps each reference name unique, even when a user ID repeats.
            String referenceName = "send_email_" + index;
            tasks.add(new SimpleTask("send_email", referenceName));
            inputs.put(
                    referenceName,
                    Map.of(
                            "recipients", userIds.get(index) + "@example.com",
                            "subject", subject,
                            "body", body));
        }
        return new DynamicForkInput(tasks, inputs);
    }

    // Threads above the default of 1 let this worker send the forked emails in parallel.
    /** Simulate sending an email. */
    @WorkerTask(value = "send_email", threadCount = 10)
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
