#!/usr/bin/env bash

t="test_accept_access_requests_2_superadmin"
# test_accept_access_requests_2_superadmin
# test_accept_access_requests_3_organization_admin
# test_accept_access_requests_with_other_requests
# test_accept_access_request_keycloak_email_error
docker exec projects-backend python manage.py test --no-input  --settings=projects.settings.test -k "$t"
# docker exec projects-backend cat apps/files/tasks.py
# docker exec -it projects-backend python manage.py shell_plus
