#!/bin/bash

# Drop a database for the current backend, with checks

set -euo pipefail

hostname=$POSTGRES_HOST

new_user=$POSTGRES_USER
new_password=$POSTGRES_PASSWORD
current_database=$POSTGRES_DB

origin_database=$ORIGIN_POSTGRES_DB

dry_run="${DRY_RUN-}"
force_disconnect="${FORCE_DISCONNECT-}"

# Check that the instance is not the main one
if [ "${INSTANCE}" == "main" ]; then
  echo "Cannot drop the main database"
  exit 1
fi

if [ "${current_database}" == "${origin_database}" ]; then
  echo "Cannot drop the origin database"
  exit 1
fi

# Check that the environment is not production
if [ "${ENVIRONMENT}" == "production" ]; then
  echo "Cannot drop a database in production"
  exit 1
fi

# Drop the database
if [ "${dry_run}" == "true" ]; then
  echo "Would drop database ${current_database} (dry run)"
  exit 0
else
  if [ "${force_disconnect}" == "true" ]; then
  admin_user=$ADMIN_POSTGRES_USER
  admin_password=$ADMIN_POSTGRES_PASSWORD
PGPASSWORD="$admin_password" PGHOST="$hostname" PGUSER="$admin_user" PGDATABASE=postgres psql <<EOF
  select pg_terminate_backend(pid)
    from pg_stat_activity
    where
      datname = '$current_database'
    ;
EOF
  fi

  echo "Dropping database ${current_database}"
  PGPASSWORD="$new_password" PGHOST="$hostname" PGUSER="$new_user" dropdb --if-exists "${current_database}"
fi