#!/bin/bash

# Create a db from an existing one

set -euo pipefail

new_user=$PGUSER
new_password=$PGPASSWORD
new_database=$PGDATABASE

admin_user=$ADMINPGUSER
admin_password=$ADMINPGPASSWORD

origin_database=$ORIGINPGDATABASE

DUMP_FILE="/tmp/$origin_database.dump"

# Create the database with admin creds
echo "Creating database $new_database with user $new_user"
PGPASSWORD="$new_password" PGHOST="$PGHOST" PGUSER="$new_user" createdb "$new_database"

# Dump the origin database into a file
echo "Dumping $origin_database into $DUMP_FILE"
PGPASSWORD="$admin_password" PGHOST="$PGHOST" PGUSER="$admin_user" PGDATABASE="$origin_database" pg_dump -Z0 -Fc -f "$DUMP_FILE"

# Restore the dump into the new database
echo "Restoring $DUMP_FILE into $new_database"
PGPASSWORD="$admin_password" PGHOST="$PGHOST" PGUSER="$admin_user" PGDATABASE="$new_database" pg_restore -d "$new_database" "$DUMP_FILE"

# Grant privileges to the user
echo "Granting privileges to $new_user on $new_database"
PGPASSWORD="$admin_password" PGHOST="$PGHOST" PGUSER="$admin_user" PGDATABASE="$new_database" psql -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $new_user;";
PGPASSWORD="$admin_password" PGHOST="$PGHOST" PGUSER="$admin_user" PGDATABASE="$new_database" psql -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $new_user;";
