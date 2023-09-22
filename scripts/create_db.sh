#!/bin/bash

# Create a db from an existing one

set -euo pipefail

# Check that the instance is not the main one
if [ "${INSTANCE}" == "main" ]; then
  echo "Cannot create the main database"
  exit 1
fi

if [ "${POSTGRES_DATABASE}" == "${ORIGIN_POSTGRES_DATABASE}" ]; then
  echo "Cannot create the origin database"
  exit 1
fi

# Check that the environment is not production
if [ "${ENVIRONMENT}" == "production" ]; then
  echo "Cannot create a database in production"
  exit 1
fi

hostname=$POSTGRES_HOST

new_user=$POSTGRES_USER
new_password=$POSTGRES_PASSWORD
new_database=$POSTGRES_DATABASE

admin_user=$ADMIN_POSTGRES_USER
admin_password=$ADMIN_POSTGRES_PASSWORD

origin_database=$ORIGIN_POSTGRES_DATABASE

dump_file="/tmp/$origin_database.dump"

# Create the database with admin creds
echo "Creating database $new_database with user $new_user"
PGPASSWORD="$new_password" PGHOST="$hostname" PGUSER="$new_user" createdb "$new_database"

# Dump the origin database into a file
echo "Dumping $origin_database into $dump_file"
PGPASSWORD="$admin_password" PGHOST="$hostname" PGUSER="$admin_user" PGDATABASE="$origin_database" pg_dump -Z0 -Fc -f "$dump_file"

# Restore the dump into the new database
echo "Restoring $dump_file into $new_database"
PGPASSWORD="$admin_password" PGHOST="$hostname" PGUSER="$admin_user" PGDATABASE="$new_database" pg_restore -d "$new_database" "$dump_file"

# Grant privileges to the user
echo "Granting privileges to $new_user on $new_database"
PGPASSWORD="$admin_password" PGHOST="$hostname" PGUSER="$admin_user" PGDATABASE="$new_database" psql -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $new_user;";
PGPASSWORD="$admin_password" PGHOST="$hostname" PGUSER="$admin_user" PGDATABASE="$new_database" psql -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $new_user;";
