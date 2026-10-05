// Create the local database used from Exercise 1 onward.

package utils

import (
	"database/sql"
	"os"
	"path/filepath"
)

// schemaPath is the schema that every language version of this codelab shares.
var schemaPath = filepath.Join(sourceDir(), "..", "..", "shared", "schema.sql")

// CreateSqliteDb runs the create-db step, which creates the tables in the shared schema.
func CreateSqliteDb() error {
	schema, err := os.ReadFile(schemaPath)
	if err != nil {
		return err
	}

	// Implicitly creates a new DB by opening it.
	db, err := sql.Open("sqlite", DatabasePath)
	if err != nil {
		return err
	}
	defer db.Close()

	// Create the tables defined in the shared schema. Exec runs every statement in it.
	_, err = db.Exec(string(schema))
	return err
}
