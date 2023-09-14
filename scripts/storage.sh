#!/bin/bash
# Duplicate Azure storage.

FROM=${1:?"missing arg 1 for origin environment [local/dev/rbac/stag/prod]"}
TO=${2:?"missing arg 1 for destination environment [local/dev/rbac/stag/prod]"}
# Generate a token with read and list rights on Azure portal

if [ ${TO} != "local" ]; then
  # Generate a token with all rights on Azure portal
  ORIGIN_TOKEN=${ORIGIN_TOKEN:?"Specify ORIGIN_TOKEN to access existing storage."}
  DESTINATION_TOKEN=${DESTINATION_TOKEN:?"Specify DESTINATION_TOKEN to write in new storage."}

  source ./scripts/set_env.sh ${FROM}
  ORIGIN_ACCOUNT=${AZURE_ACCOUNT_NAME}
  ORIGIN_CONTAINER=${AZURE_CONTAINER}
  ORIGIN="https://${ORIGIN_ACCOUNT}.blob.core.windows.net/${ORIGIN_CONTAINER}?${ORIGIN_TOKEN}"

  source ./scripts/set_env.sh ${TO}
  DESTINATION_ACCOUNT=${AZURE_ACCOUNT_NAME}
  DESTINATION_CONTAINER=${AZURE_CONTAINER}
  DESTINATION="https://${DESTINATION_ACCOUNT}.blob.core.windows.net/${DESTINATION_CONTAINER}?${DESTINATION_TOKEN}"

  echo "Copying ${ORIGIN_ACCOUNT}.blob.core.windows.net/${ORIGIN_CONTAINER} to ${DESTINATION_ACCOUNT}.blob.core.windows.net/${DESTINATION_CONTAINER}"
  azcopy rm "${DESTINATION}" --recursive=true
  azcopy copy "${ORIGIN}" "${DESTINATION}" --recursive
else
  ORIGIN_TOKEN=${ORIGIN_TOKEN:?"Specify ORIGIN_TOKEN to access existing storage."}

  source ./scripts/set_env.sh ${FROM}
  ORIGIN_ACCOUNT=${AZURE_ACCOUNT_NAME}
  ORIGIN_CONTAINER=${AZURE_CONTAINER}
  ORIGIN="https://${ORIGIN_ACCOUNT}.blob.core.windows.net/${ORIGIN_CONTAINER}/*?${ORIGIN_TOKEN}"

  mc alias set myminio http://localhost:9000 minioadmin minioadmin

  echo "Copying ${ORIGIN_ACCOUNT}.blob.core.windows.net/${ORIGIN_CONTAINER}/ to local storage"
  azcopy copy "${ORIGIN}" ~/storage/projects --recursive
  mc mv --recursive ~/storage/projects myminio
fi

echo "File storage copy is over"
