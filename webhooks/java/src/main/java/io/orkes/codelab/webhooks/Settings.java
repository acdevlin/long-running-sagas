package io.orkes.codelab.webhooks;

import io.github.cdimascio.dotenv.Dotenv;
import io.orkes.conductor.client.ApiClient;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Objects;
import java.util.stream.Stream;

/**
 * Settings for the Java version of the webhooks codelab, read from the {@code .env} file at the
 * repository root that every language version shares. Shell variables take precedence over it.
 */
public record Settings(
        String conductorServerUrl,
        String authKey,
        String authSecret,
        String llmModel,
        String integrationName,
        String webhookId,
        String sourceHeader) {

    // Identifies this language version in its workflow and agent names and in the webhook
    // payload, so every language version can share one webhook.
    public static final String LANGUAGE = "java";

    // The workflow sends an email to each user ID in this list. Repeating "alex" gives the
    // agent a clear most-active recipient to identify from the stored email activity.
    public static final List<String> USER_IDS =
            List.of("alex", "alex", "alex", "user_1", "user_2", "user_555");

    private static final Settings CURRENT = fromEnv();

    /** The settings for this run, read once from the environment and {@code .env}. */
    public static Settings current() {
        return CURRENT;
    }

    /** Conductor cluster URL without its /api suffix, shared by the UI and webhooks. */
    public String serverBaseUrl() {
        String url = conductorServerUrl.replaceAll("/+$", "");
        return url.endsWith("/api") ? url.substring(0, url.length() - "/api".length()) : url;
    }

    /** Webhook endpoint on the same Conductor cluster as the API. */
    public String webhookEndpointUrl() {
        return serverBaseUrl() + "/webhook/" + webhookId;
    }

    /**
     * Build a new client for the Conductor API. The SDK reads the CONDUCTOR_* variables only from
     * the process environment, so the values from {@code .env} are passed to it here.
     */
    public ApiClient createApiClient() {
        var builder = ApiClient.builder().basePath(conductorServerUrl);
        if (authKey != null && authSecret != null) {
            builder.credentials(authKey, authSecret);
        }
        return builder.build();
    }

    // A record's generated toString() lists every component, so leave the secret out of it.
    @Override
    public String toString() {
        return "Settings[conductorServerUrl="
                + conductorServerUrl
                + ", llmModel="
                + llmModel
                + ", integrationName="
                + integrationName
                + ", webhookId="
                + webhookId
                + "]";
    }

    /** Build settings from the defaults below, applying any environment overrides. */
    private static Settings fromEnv() {
        Dotenv dotenv =
                Dotenv.configure()
                        .directory(findEnvDirectory().toString())
                        .ignoreIfMissing()
                        .load();
        return new Settings(
                read(dotenv, "CONDUCTOR_SERVER_URL", "https://developer.orkescloud.com/api"),
                read(dotenv, "CONDUCTOR_AUTH_KEY", null),
                read(dotenv, "CONDUCTOR_AUTH_SECRET", null),
                read(dotenv, "CONDUCTOR_AGENT_LLM_MODEL", "openai/gpt-5-nano"),
                read(dotenv, "CONDUCTOR_INTEGRATION_NAME", "your_integration_name_here"),
                read(dotenv, "WEBHOOK_ID", "your_webhook_id_here"),
                read(dotenv, "WEBHOOK_SOURCE_HEADER", "your_source_header_here"));
    }

    // Search upwards from the current folder, which is webhooks/java for every Gradle step, for
    // the .env file at the repository root.
    private static Path findEnvDirectory() {
        Path start = Path.of("").toAbsolutePath();
        return Stream.iterate(start, Objects::nonNull, directory -> directory.getParent())
                .filter(directory -> Files.isRegularFile(directory.resolve(".env")))
                .findFirst()
                .orElse(start);
    }

    /** Return a variable from the shell or {@code .env}, treating an empty value as unset. */
    private static String read(Dotenv dotenv, String name, String defaultValue) {
        String value = dotenv.get(name);
        return value == null || value.isBlank() ? defaultValue : value.trim();
    }
}
