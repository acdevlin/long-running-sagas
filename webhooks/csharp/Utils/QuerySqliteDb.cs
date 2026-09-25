using System.Runtime.CompilerServices;
using Microsoft.Data.Sqlite;

namespace WebhooksCodelab.Utils;

/// <summary>Prints emails stored by the DB for the webhook codelab.</summary>
public static class QuerySqliteDb
{
    /// <summary>The local database file, created by the create-db step.</summary>
    public static string DatabasePath { get; } = LocateDatabase();

    // Exercise 3: Use the recipient argument in get_recipient_email_history to
    // retrieve only the selected recipient's records.
    /// <summary>Return stored emails in insertion order, optionally for one recipient.</summary>
    public static async Task<List<Dictionary<string, object?>>> FetchEmailsAsync(string? recipient = null)
    {
        await using var connection = await OpenReadOnlyDatabaseAsync();
        await using var command = connection.CreateCommand();

        command.CommandText = """
            SELECT *
            FROM emails
            """;
        if (recipient is not null)
        {
            command.CommandText += "\nWHERE recipients = $recipient";
            command.Parameters.AddWithValue("$recipient", recipient);
        }
        command.CommandText += "\nORDER BY id";

        return await ReadRowsAsync(command);
    }

    // Exercise 3: Use these rows in summarize_email_activity to total the emails and return
    // each recipient's activity. Each row's email_count is a long.
    /// <summary>Return one email-count row per recipient, ordered by activity.</summary>
    public static async Task<List<Dictionary<string, object?>>> FetchEmailActivityAsync()
    {
        await using var connection = await OpenReadOnlyDatabaseAsync();
        await using var command = connection.CreateCommand();

        command.CommandText = """
            SELECT
                recipients AS recipient,
                COUNT(*) AS email_count
            FROM emails
            GROUP BY recipients
            ORDER BY email_count DESC, recipient
            """;

        return await ReadRowsAsync(command);
    }

    /// <summary>Print email rows in an aligned table with database field headings.</summary>
    public static void PrintEmails(List<Dictionary<string, object?>> emails)
    {
        var fieldNames = emails[0].Keys.ToArray();
        var rows = emails
            .Select(email => fieldNames.Select(field => email[field]?.ToString() ?? "").ToArray())
            .ToList();
        var columnWidths = fieldNames
            .Select((field, index) => Math.Max(field.Length, rows.Max(row => row[index].Length)))
            .ToArray();

        string FormatRow(string[] values) =>
            string.Join(" | ", values.Select((value, index) => value.PadRight(columnWidths[index])));

        Console.WriteLine(FormatRow(fieldNames));
        Console.WriteLine(string.Join("-+-", columnWidths.Select(width => new string('-', width))));
        foreach (var row in rows)
        {
            Console.WriteLine(FormatRow(row));
        }
    }

    /// <summary>Query the codelab database and print readable email records.</summary>
    public static async Task RunAsync()
    {
        List<Dictionary<string, object?>> emails;
        try
        {
            emails = await FetchEmailsAsync();
        }
        catch (Exception error) when (error is FileNotFoundException or SqliteException)
        {
            Console.Error.WriteLine($"Unable to query stored emails: {error.Message}");
            Environment.ExitCode = 1;
            return;
        }

        if (emails.Count == 0)
        {
            Console.WriteLine($"No emails found in {DatabasePath}");
        }
        else
        {
            PrintEmails(emails);
        }
    }

    /// <summary>
    /// Helper function that opens a read-only connection to the codelab database.
    ///
    /// Checking the path first gives a clear error when the database has not
    /// been created yet, instead of a generic SQLite "unable to open" error.
    /// </summary>
    private static async Task<SqliteConnection> OpenReadOnlyDatabaseAsync()
    {
        if (!File.Exists(DatabasePath))
        {
            throw new FileNotFoundException(
                $"Database not found at {DatabasePath}. Run the create-db step first.");
        }

        // Read-only mode prevents this query helper and the agent tools that use
        // it from modifying the codelab database.
        var connectionString = new SqliteConnectionStringBuilder
        {
            DataSource = DatabasePath,
            Mode = SqliteOpenMode.ReadOnly,
            // A pooled connection keeps its file open, so a long-running serve-agent step
            // would keep reading a database file even after it was deleted and re-created.
            Pooling = false,
        }.ToString();
        var connection = new SqliteConnection(connectionString);
        await connection.OpenAsync();
        return connection;
    }

    /// <summary>Read every result row as a dictionary keyed by column name.</summary>
    private static async Task<List<Dictionary<string, object?>>> ReadRowsAsync(SqliteCommand command)
    {
        await using var reader = await command.ExecuteReaderAsync();

        var rows = new List<Dictionary<string, object?>>();
        while (await reader.ReadAsync())
        {
            var row = new Dictionary<string, object?>();
            for (var index = 0; index < reader.FieldCount; index++)
            {
                row[reader.GetName(index)] = reader.IsDBNull(index) ? null : reader.GetValue(index);
            }
            rows.Add(row);
        }
        return rows;
    }

    // Resolved from this source file's folder, as the Python version does, rather
    // than the build output folder, so every step uses the same database file.
    private static string LocateDatabase([CallerFilePath] string sourceFile = "") =>
        Path.Combine(Path.GetDirectoryName(sourceFile)!, "webhook_codelab_storage.db");
}
