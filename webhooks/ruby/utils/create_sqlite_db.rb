# frozen_string_literal: true

# Create the local database used from Exercise 1 onward.

require 'sqlite3'
require_relative 'query_sqlite_db'

# Creates the codelab database from the shared schema.
module CreateSqliteDb
  # The schema is shared by every language version of this codelab
  SCHEMA_PATH = File.expand_path('../../shared/schema.sql', __dir__)

  def self.main
    schema = File.read(SCHEMA_PATH, encoding: 'utf-8')

    # Implicitly creates a new DB by opening it, and closes it at the end of the block
    SQLite3::Database.open(QuerySqliteDb::DATABASE_PATH) do |database|
      # Create the tables defined in the shared schema; execute_batch runs every statement in it
      database.execute_batch(schema)
    end
  end
end

CreateSqliteDb.main if $PROGRAM_NAME == __FILE__
