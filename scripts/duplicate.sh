#!/bin/bash
# Duplicate an instance's database in another instance
# First parameter in origin environment, second parameter is destination environment

FROM=${1:?"missing arg 1 for origin environment [local/dev/sam/julien/fares/yohann/stag/prod]"}
TO=${2:?"missing arg 2 for destination environment [local/dev/sam/julien/fares/yohann/stag/prod]"}
TO_PGPASSWORD=${TO_PGPASSWORD:?"Specify TO_PGPASSWORD for postgres destination."}

source ./scripts/set_env.sh ${FROM}
TIME=$(date "+%s")
BACKUP_FILE="postgres_${FROM}_${PGDATABASE}_${TIME}"

source ./scripts/backup.sh ${FROM} ${BACKUP_FILE}

echo "If you wish to restore it to another instance, switch your VPN and continue the process."
# Allow user to switch VPN or abort process
while true; do
    read -p "Please switch your VPN and enter Y to continue. Enter N to abort and quit : " answer
    case $answer in
        [Yy]* ) break;;
        [Nn]* ) echo "Restore was aborted."; exit;;
        * ) echo "Please answer Y or N.";;
    esac
done

export PGPASSWORD=${TO_PGPASSWORD}
source ./scripts/restore.sh ${TO} ${BACKUP_FILE}

# Allow user to duplicate file storage or not
while true; do
    read -p "Do you wish to duplicate the file storage as well ? [Y/N] " answer
    case $answer in
        [Yy]* ) break;;
        [Nn]* ) echo "Storage was not duplicated."; exit;;
        * ) echo "Please answer Y or N.";;
    esac
done

source ./scripts/storage.sh ${FROM} ${TO}
