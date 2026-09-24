using System.Net.Http.Json;

namespace WebhooksCodelab;

/// <summary>Send a webhook payload to the specified Orkes webhook endpoint.</summary>
public static class SendWebhookPayload
{
    public static async Task RunAsync()
    {
        var payload = new Dictionary<string, object>
        {
            ["user_id"] = Settings.Current.UserId,
            ["type"] = "customer",
            // Exercise 3: Replace this prompt with a request to summarize stored email
            // activity, inspect the busiest recipient's history, and return a digest.
            ["agent_input"] = "Introduce yourself, then inform the user that their email has been sent.",
            // Every language version shares one webhook; this key selects this
            // language's workflow (see the matches in the deploy step).
            ["language"] = Settings.Current.Language,
        };

        using var request = new HttpRequestMessage(HttpMethod.Post, Settings.Current.WebhookEndpointUrl)
        {
            Content = JsonContent.Create(payload),
        };
        request.Headers.Add("Accept", "application/json");
        request.Headers.Add("source", Settings.Current.SourceHeader);

        using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(30) };
        using var response = await client.SendAsync(request);

        Console.WriteLine($"Status: {(int)response.StatusCode}");
        Console.WriteLine($"Response: {await response.Content.ReadAsStringAsync()}");

        // Throw an exception for HTTP error responses (e.g.: 4xx and 5xx).
        response.EnsureSuccessStatusCode();

        Console.WriteLine("Webhook was accepted by Orkes Conductor.");
    }
}
