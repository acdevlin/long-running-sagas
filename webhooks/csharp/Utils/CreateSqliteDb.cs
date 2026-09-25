using System.Runtime.CompilerServices;
using Microsoft.Data.Sqlite;

namespace WebhooksCodelab.Utils;

/// <summary>Create the local database used from Exercise 1 onward.</summary>
public static class CreateSqliteDb
{
    public static async Task RunAsync()
    {
        // The schema is shared by every language version of this codelab.
        var schema = await File.ReadAllTextAsync(SchemaPath());

        // Implicitly creates a new DB by connecting to it.
        var connectionString = new SqliteConnectionStringBuilder
        {
            DataSource = QuerySqliteDb.DatabasePath,
        }.ToString();
        await using var connection = new SqliteConnection(connectionString);
        await connection.OpenAsync();

        // Create the tables defined in the shared schema.
        await using var command = connection.CreateCommand();
        command.CommandText = schema;
        await command.ExecuteNonQueryAsync();
    }

    // Resolved from this source file's folder, not the build output folder.
    private static string SchemaPath([CallerFilePath] string sourceFile = "") =>
        Path.GetFullPath(Path.Combine(Path.GetDirectoryName(sourceFile)!, "..", "..", "shared", "schema.sql"));
}
