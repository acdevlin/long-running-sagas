package io.orkes.codelab.webhooks.utils;

import org.sqlite.SQLiteConfig;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import java.util.stream.IntStream;
import java.util.stream.Stream;

/** Prints emails stored by the DB for the webhook codelab. */
public final class QuerySqliteDb {

    /** The local database file, created by the create-db step in this project's folder. */
    public static final Path DATABASE_PATH = Path.of("webhook_codelab_storage.db").toAbsolutePath();

    private QuerySqliteDb() {}

    /** Return every stored email in insertion order. */
    public static List<Map<String, Object>> fetchEmails() throws IOException, SQLException {
        return fetchEmails(null);
    }

    /**
     * Return stored emails in insertion order, for one recipient unless {@code recipient} is null.
     */
    public static List<Map<String, Object>> fetchEmails(String recipient)
            throws IOException, SQLException {
        String query =
                """
                SELECT *
                FROM emails
                """
                        + (recipient != null ? "WHERE recipients = ?\n" : "")
                        + "ORDER BY id";

        try (Connection connection = openReadOnlyDatabase();
                var statement = connection.prepareStatement(query)) {
            if (recipient != null) {
                statement.setString(1, recipient);
            }
            try (ResultSet resultSet = statement.executeQuery()) {
                return readRows(resultSet);
            }
        }
    }

    /** Return one email-count row per recipient, ordered by activity. */
    public static List<Map<String, Object>> fetchEmailActivity() throws IOException, SQLException {
        String query =
                """
                SELECT
                    recipients AS recipient,
                    COUNT(*) AS email_count
                FROM emails
                GROUP BY recipients
                ORDER BY email_count DESC, recipient
                """;

        try (Connection connection = openReadOnlyDatabase();
                var statement = connection.prepareStatement(query);
                ResultSet resultSet = statement.executeQuery()) {
            return readRows(resultSet);
        }
    }

    /** Print email rows in an aligned table with database field headings. */
    public static void printEmails(List<Map<String, Object>> emails) {
        List<String> fieldNames = List.copyOf(emails.getFirst().keySet());
        List<List<String>> rows =
                emails.stream()
                        .map(
                                email ->
                                        fieldNames.stream()
                                                .map(field -> String.valueOf(email.get(field)))
                                                .toList())
                        .toList();
        // Each column is as wide as its longest value, counting the heading as a value.
        int[] columnWidths =
                IntStream.range(0, fieldNames.size())
                        .map(
                                index ->
                                        Stream.concat(Stream.of(fieldNames), rows.stream())
                                                .mapToInt(row -> row.get(index).length())
                                                .max()
                                                .orElseThrow())
                        .toArray();

        System.out.println(formatRow(fieldNames, columnWidths));
        System.out.println(
                Arrays.stream(columnWidths)
                        .mapToObj("-"::repeat)
                        .collect(Collectors.joining("-+-")));
        rows.forEach(row -> System.out.println(formatRow(row, columnWidths)));
    }

    /** Query the codelab database and print readable email records. */
    public static int run() {
        List<Map<String, Object>> emails;
        try {
            emails = fetchEmails();
        } catch (IOException | SQLException error) {
            System.err.println("Unable to query stored emails: " + error.getMessage());
            return 1;
        }

        if (emails.isEmpty()) {
            System.out.println("No emails found in " + DATABASE_PATH);
        } else {
            printEmails(emails);
        }
        return 0;
    }

    /**
     * Open a read-only connection to the codelab database. Checking the path first gives a clear
     * error when the database has not been created yet.
     */
    private static Connection openReadOnlyDatabase() throws IOException, SQLException {
        if (!Files.isRegularFile(DATABASE_PATH)) {
            throw new FileNotFoundException(
                    "Database not found at " + DATABASE_PATH + ". Run the create-db step first.");
        }

        // Read-only mode prevents this query helper and the agent tools that use it from
        // modifying the codelab database.
        SQLiteConfig config = new SQLiteConfig();
        config.setReadOnly(true);
        return DriverManager.getConnection("jdbc:sqlite:" + DATABASE_PATH, config.toProperties());
    }

    /** Read every result row as a map keyed by column name, in column order. */
    private static List<Map<String, Object>> readRows(ResultSet resultSet) throws SQLException {
        // Plain loops read the ResultSet: it has no stream API, and its getters throw the checked
        // SQLException, which a stream's lambdas cannot throw.
        var metadata = resultSet.getMetaData();
        int columnCount = metadata.getColumnCount();
        List<Map<String, Object>> rows = new ArrayList<>();
        while (resultSet.next()) {
            Map<String, Object> row = new LinkedHashMap<>();
            for (int column = 1; column <= columnCount; column++) {
                row.put(metadata.getColumnLabel(column), resultSet.getObject(column));
            }
            rows.add(row);
        }
        return rows;
    }

    /** Join one row's values with column separators, padding each value to its column's width. */
    private static String formatRow(List<String> values, int[] columnWidths) {
        return IntStream.range(0, values.size())
                .mapToObj(
                        index -> String.format("%-" + columnWidths[index] + "s", values.get(index)))
                .collect(Collectors.joining(" | "));
    }
}
