#!/bin/bash

case ${1} in
  local )
    export PGHOST=localhost;
    export PGPORT=5432;
    export PGDATABASE=postgres;
    export PGUSER=postgres;
    export PGPASSWORD=password;;
  sam )
    export PGHOST=dev-lab-projects-backend.postgres.database.azure.com;
    export PGPORT=5432;
    export PGDATABASE=dev_sam;
    export PGUSER=dev_tech;
    export PGPASSWORD=${PGPASSWORD:?"Specify PGPASSWORD to connect to db."};
    export AZURE_ACCOUNT_NAME=criparisdevlabprojects;
    export AZURE_CONTAINER="projects-sam";;
  julien )
    export PGHOST=dev-lab-projects-backend.postgres.database.azure.com;
    export PGPORT=5432;
    export PGDATABASE=julien;
    export PGUSER=dev_tech;
    export PGPASSWORD=${PGPASSWORD:?"Specify PGPASSWORD to connect to db."};
    export AZURE_ACCOUNT_NAME=criparisdevlabprojects;
    export AZURE_CONTAINER="projects-julien";;
  alice )
    export PGHOST=dev-lab-projects-backend.postgres.database.azure.com;
    export PGPORT=5432;
    export PGDATABASE=alice;
    export PGUSER=dev_tech;
    export PGPASSWORD=${PGPASSWORD:?"Specify PGPASSWORD to connect to db."};
    export AZURE_ACCOUNT_NAME=criparisdevlabprojects;
    export AZURE_CONTAINER="projects-alice";;
  dev )
    export PGHOST=dev-lab-projects-backend.postgres.database.azure.com;
    export PGPORT=5432;
    export PGDATABASE=dev_projects;
    export PGUSER=dev_tech;
    export PGPASSWORD=${PGPASSWORD:?"Specify PGPASSWORD to connect to db."};
    export AZURE_ACCOUNT_NAME=criparisdevlabprojects;
    export AZURE_CONTAINER="projects";;
  stag )
    export PGHOST=dev-lab-projects-backend.postgres.database.azure.com;
    export PGPORT=5432;
    export PGDATABASE=staging_projects;
    export PGUSER=staging;
    export PGPASSWORD=${PGPASSWORD:?"Specify PGPASSWORD to connect to db."};
    export AZURE_ACCOUNT_NAME=criparisstagtestprojects;
    export AZURE_CONTAINER="projects";;
  prod )
    export PGHOST=prod-prod-projects-backend.postgres.database.azure.com;
    export PGPORT=5432;
    export PGDATABASE=projects;
    export PGUSER=psqladmin;
    export PGPASSWORD=${PGPASSWORD:?"Specify PGPASSWORD to connect to db."};
    export AZURE_ACCOUNT_NAME=criparisprodprodprojects;
    export AZURE_CONTAINER="projects";;
esac