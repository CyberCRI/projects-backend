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
  fares )
    export PGHOST=dev-lab-projects-backend.postgres.database.azure.com;
    export PGPORT=5432;
    export PGDATABASE=fares;
    export PGUSER=dev_tech;
    export PGPASSWORD=${PGPASSWORD:?"Specify PGPASSWORD to connect to db."};
    export AZURE_ACCOUNT_NAME=criparisdevlabprojects;
    export AZURE_CONTAINER="projects-fares";;
  julien )
    export PGHOST=dev-lab-projects-backend.postgres.database.azure.com;
    export PGPORT=5432;
    export PGDATABASE=julien;
    export PGUSER=dev_tech;
    export PGPASSWORD=${PGPASSWORD:?"Specify PGPASSWORD to connect to db."};
    export AZURE_ACCOUNT_NAME=criparisdevlabprojects;
    export AZURE_CONTAINER="projects-julien";;
  yohann )
    export PGHOST=dev-lab-projects-backend.postgres.database.azure.com;
    export PGPORT=5432;
    export PGDATABASE=yohann;
    export PGUSER=dev_tech;
    export PGPASSWORD=${PGPASSWORD:?"Specify PGPASSWORD to connect to db."};
    export AZURE_ACCOUNT_NAME=criparisdevlabprojects;
    export AZURE_CONTAINER="projects-yohann";;
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
  proj_810 )
    export PGHOST=dev-lab-projects-backend.postgres.database.azure.com;
    export PGPORT=5432;
    export PGDATABASE=dev_proj810;
    export PGUSER=user_tech;
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