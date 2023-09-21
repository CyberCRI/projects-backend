#!/bin/bash

# Drop a database for the current backend, with checks

set -euo pipefail

# Check that the instance is not the main one
if [ "${INSTANCE}" == "main" ]; then
  echo "Cannot drop the main database"
  exit 1
fi

# Check that the environment is not production
if [ "${ENVIRONMENT}" == "production" ]; then
  echo "Cannot drop a database in production"
  exit 1
fi

# Drop the database
echo "Dropping database ${PGDATABASE}"

if [ "${DRY_RUN}" == "true" ]; then
  echo "Would drop database ${PGDATABASE} (dry run)"
else
  dropdb --if-exists "${PGDATABASE}"
fi
