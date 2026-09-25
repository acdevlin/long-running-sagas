package io.orkes.codelab.webhooks.utils;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.DriverManager;
import java.sql.SQLException;

/** Create the local database used from Exercise 1 onward. */
public final class CreateSqliteDb {

    // Resolved from this project's folder, the working directory of every Gradle step.
    private static final Path SCHEMA_PATH =
            Path.of("..", "shared", "schema.sql").toAbsolutePath().normalize();

    private CreateSqliteDb() {}

    public static int run() throws IOException, SQLException {
        // The schema is shared by every language version of this codelab.
        String schema = Files.readString(SCHEMA_PATH);

        // Implicitly creates a new DB by connecting to it.
        try (var connection =
                        DriverManager.getConnection("jdbc:sqlite:" + QuerySqliteDb.DATABASE_PATH);
                var statement = connection.createStatement()) {
            // Create the tables defined in the shared schema. The SQLite driver's executeUpdate
            // runs every statement in it, whereas execute would run only the first.
            statement.executeUpdate(schema);
        }
        return 0;
    }
}
