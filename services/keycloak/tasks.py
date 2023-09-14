from apps.accounts.models import ProjectUser
from projects.celery import app
from services.keycloak.interface import KeycloakService


@app.task(name="services.keycloak.tasks.delete_keycloak_account")
def delete_keycloak_account(user_id: int, service=KeycloakService):
    _delete_keycloak_account(user_id, service)


def _delete_keycloak_account(user_id: int, service):
    user = ProjectUser.objects.get(id=user_id)
    service.delete_user(user)


@app.task(name="services.keycloak.tasks.update_keycloak_account")
def update_keycloak_account(user_id: int, payload, service=KeycloakService):
    _update_keycloak_account(user_id, payload, service)


def _update_keycloak_account(user_id: int, payload, service):
    user = ProjectUser.objects.get(id=user_id)
    service.update_user(user, payload)
