// Prints emails stored by the DB for the webhook codelab.

package utils

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"unicode/utf8"

	// Registers the SQLite driver with database/sql under the name "sqlite".
	_ "modernc.org/sqlite"
)

// DatabasePath is the local database file, which the create-db step creates next to this file.
var DatabasePath = filepath.Join(sourceDir(), "webhook_codelab_storage.db")

// Email is one row of the emails table.
type Email struct {
	ID         int64  `json:"id"`
	SentTime   int64  `json:"sent_time"`
	Subject    string `json:"subject"`
	Recipients string `json:"recipients"`
}

// EmailActivity is the number of stored emails sent to one recipient.
type EmailActivity struct {
	Recipient  string `json:"recipient"`
	EmailCount int64  `json:"email_count"`
}

// OpenDatabase opens the codelab database, read-only unless writable is true. Opening a missing
// file would create an empty database, so check the path first and open without creating it.
func OpenDatabase(writable bool) (*sql.DB, error) {
	if info, err := os.Stat(DatabasePath); err != nil || !info.Mode().IsRegular() {
		return nil, fmt.Errorf("database not found at %s; run the create-db step "+
			"(go run . create-db) first", DatabasePath)
	}

	// Read-only mode prevents this query helper and the agent tools that use it from modifying the
	// codelab database. Neither mode creates the file.
	mode := "ro"
	if writable {
		mode = "rw"
	}
	return sql.Open("sqlite", "file:"+filepath.ToSlash(DatabasePath)+"?mode="+mode)
}

// FetchEmails returns the stored emails in insertion order. Unless recipient is empty, it returns
// only the emails sent to that recipient.
func FetchEmails(recipient string) ([]Email, error) {
	query := `
		SELECT id, sent_time, subject, recipients
		FROM emails
		`
	var args []any
	if recipient != "" {
		query += "WHERE recipients = ?\n"
		args = append(args, recipient)
	}
	query += "ORDER BY id"

	db, err := OpenDatabase(false)
	if err != nil {
		return nil, err
	}
	defer db.Close()

	rows, err := db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	// Not nil, so that an empty result becomes [] in JSON rather than null.
	emails := []Email{}
	for rows.Next() {
		var email Email
		if err := rows.Scan(&email.ID, &email.SentTime, &email.Subject, &email.Recipients); err != nil {
			return nil, err
		}
		emails = append(emails, email)
	}
	return emails, rows.Err()
}

// FetchEmailActivity returns the number of emails sent to each recipient, ordered by activity.
func FetchEmailActivity() ([]EmailActivity, error) {
	query := `
		SELECT
			recipients AS recipient,
			COUNT(*) AS email_count
		FROM emails
		GROUP BY recipients
		ORDER BY email_count DESC, recipient
		`

	db, err := OpenDatabase(false)
	if err != nil {
		return nil, err
	}
	defer db.Close()

	rows, err := db.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	// Not nil, so that an empty result becomes [] in JSON rather than null.
	activity := []EmailActivity{}
	for rows.Next() {
		var recipient EmailActivity
		if err := rows.Scan(&recipient.Recipient, &recipient.EmailCount); err != nil {
			return nil, err
		}
		activity = append(activity, recipient)
	}
	return activity, rows.Err()
}

// PrintEmails prints email rows in an aligned table with database field headings.
func PrintEmails(emails []Email) {
	table := [][]string{{"id", "sent_time", "subject", "recipients"}}
	for _, email := range emails {
		table = append(table, []string{
			strconv.FormatInt(email.ID, 10),
			strconv.FormatInt(email.SentTime, 10),
			email.Subject,
			email.Recipients,
		})
	}

	// Each column is as wide as its longest value, counting the heading as a value.
	columnWidths := make([]int, len(table[0]))
	for _, row := range table {
		for index, value := range row {
			columnWidths[index] = max(columnWidths[index], utf8.RuneCountInString(value))
		}
	}

	formatRow := func(values []string) string {
		padded := make([]string, len(values))
		for index, value := range values {
			padded[index] = fmt.Sprintf("%-*s", columnWidths[index], value)
		}
		return strings.Join(padded, " | ")
	}

	dashes := make([]string, len(columnWidths))
	for index, width := range columnWidths {
		dashes[index] = strings.Repeat("-", width)
	}

	fmt.Println(formatRow(table[0]))
	fmt.Println(strings.Join(dashes, "-+-"))
	for _, row := range table[1:] {
		fmt.Println(formatRow(row))
	}
}

// QuerySqliteDb runs the query-db step, which prints the stored emails as a table.
func QuerySqliteDb() error {
	emails, err := FetchEmails("")
	if err != nil {
		return fmt.Errorf("unable to query stored emails: %w", err)
	}

	if len(emails) == 0 {
		fmt.Printf("No emails found in %s\n", DatabasePath)
	} else {
		PrintEmails(emails)
	}
	return nil
}

// sourceDir returns the folder that holds this file. go run compiles each step with the full path
// of every source file, so this works from any folder.
func sourceDir() string {
	_, thisFile, _, _ := runtime.Caller(0)
	return filepath.Dir(thisFile)
}
