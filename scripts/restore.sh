#!/bin/bash
# Restore pgdump to a database

# Set env : choices are local, dev, rbac, stag and prod
set -euo pipefail

TO=${1:?"missing arg 1 for destination environment [local/dev/rbac/stag/prod]"}
BACKUP_FILE=${2:?"missing arg 2 for backup file name"}
BACKUP_PATH="dumps/${BACKUP_FILE}.pgdump"
source ./scripts/set_env.sh ${TO}

echo "Restoring ${BACKUP_FILE} to ${PGDATABASE}"

dropdb --if-exists --force ${PGDATABASE}
createdb -T template0 ${PGDATABASE}
pg_restore --no-owner --no-acl -d ${PGDATABASE} ${BACKUP_PATH} --verbose

echo "${PGDATABASE} database restored"
