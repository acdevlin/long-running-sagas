# frozen_string_literal: true

# Prints emails stored by the DB for the webhook codelab.

require 'sqlite3'

# Read-only queries of the codelab database, shared by the query-db step and the agent's tools.
module QuerySqliteDb
  DATABASE_PATH = File.join(__dir__, 'webhook_codelab_storage.db')

  # Raised when the create-db step hasn't created the database yet.
  class DatabaseNotFoundError < StandardError; end

  # Open a connection to the codelab database, read-only unless writable is true, yield it, then
  # close it. Opening a missing file would create an empty database, so check the path first and
  # open without creating it.
  def self.open_database(writable: false, &)
    unless File.file?(DATABASE_PATH)
      raise DatabaseNotFoundError, "Database not found at #{DATABASE_PATH}. Run the create-db " \
                                   'step (bundle exec ruby utils/create_sqlite_db.rb) first.'
    end

    # Read-only mode stops the query helpers and agent tools from modifying the database, and
    # neither mode creates the file. Each row is a Hash keyed by column name.
    flags = writable ? SQLite3::Constants::Open::READWRITE : SQLite3::Constants::Open::READONLY
    SQLite3::Database.open(DATABASE_PATH, flags: flags, results_as_hash: true, &)
  end

  # Return stored emails in insertion order, optionally for one recipient.
  def self.fetch_emails(recipient: nil)
    query = +"
      SELECT *
      FROM emails
      "
    parameters = []
    unless recipient.nil?
      query << "WHERE recipients = ?\n"
      parameters << recipient
    end
    query << 'ORDER BY id'

    open_database { |database| database.execute(query, parameters) }
  end

  # Return one email-count row per recipient, ordered by activity.
  def self.fetch_email_activity
    query = "
      SELECT
        recipients AS recipient,
        COUNT(*) AS email_count
      FROM emails
      GROUP BY recipients
      ORDER BY email_count DESC, recipient
      "

    open_database { |database| database.execute(query) }
  end

  # Print email rows in an aligned table with database field headings.
  def self.print_emails(emails)
    field_names = emails.first.keys
    rows = emails.map { |email| field_names.map { |field| email[field].to_s } }
    column_widths = field_names.each_with_index.map do |field, index|
      [field.length, *rows.map { |row| row[index].length }].max
    end

    format_row = lambda do |values|
      values.each_with_index.map { |value, index| value.ljust(column_widths[index]) }.join(' | ')
    end

    puts format_row.call(field_names)
    puts column_widths.map { |width| '-' * width }.join('-+-')
    rows.each { |row| puts format_row.call(row) }
  end

  # Query the codelab database and print readable email records.
  # @return [Integer] the exit status for the query-db step
  def self.main
    begin
      emails = fetch_emails
    rescue DatabaseNotFoundError, SQLite3::Exception => e
      warn "Unable to query stored emails: #{e.message}"
      return 1
    end

    if emails.empty?
      puts "No emails found in #{DATABASE_PATH}"
    else
      print_emails(emails)
    end

    0
  end
end

exit(QuerySqliteDb.main) if $PROGRAM_NAME == __FILE__
