#!/bin/bash
# Dump database in a pgdump file.

# Set env : choices are local, dev, rbac, stag and prod
set -euo pipefail

FROM=${1:?"missing arg 1 for origin environment [local/dev/rbac/stag/prod]"}
source ./scripts/set_env.sh ${FROM}

TIME=$(date "+%s")
BACKUP_FILE=${2:-"postgres_${FROM}_${PGDATABASE}_${TIME}"}
BACKUP_PATH="dumps/${BACKUP_FILE}.pgdump"

echo "Backing up ${PGDATABASE} to ${BACKUP_FILE}"

pg_dump -Z6 -Fc -f ${BACKUP_PATH} --verbose

echo "Backup completed"
