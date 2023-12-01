import csv
import json
import logging
from datetime import datetime

from django.db.models import Q
from requests import Request

from apps.accounts.models import ProjectUser
from apps.accounts.serializers import UserSerializer
from apps.emailing.utils import send_email_with_attached_file
from projects.celery import app
from services.keycloak.interface import KeycloakService

logger = logging.getLogger(__name__)


@app.task
def batch_create_users(users_data, request_user_pk, update_mode="no_update"):
    """Create users in batch."""
    _batch_create_users(users_data, request_user_pk, update_mode)


def _clean_user_data_from_csv(user_data):
    return {
        key: (
            [x for x in value.split(";") if x]
            if key in ["roles_to_add", "sdgs"]
            else value
        )
        for key, value in user_data.items()
        if value
    }


def _create_user_from_csv_data(request, user_data):
    redirect_organization_code = user_data.pop("redirect_organization_code", "")
    user_data["keycloak_id"] = KeycloakService.create_user(user_data)
    serializer = UserSerializer(
        data=user_data,
        context={"request": request},
    )
    if serializer.is_valid():
        instance = serializer.save()
        KeycloakService.send_email(
            user=instance,
            email_type=KeycloakService.EmailType.ADMIN_CREATED,
            redirect_organization_code=redirect_organization_code,
        )
        return {"email": user_data["email"], "status": "created", "error": ""}
    return {
        "email": user_data["email"],
        "status": "error",
        "error": json.dumps(serializer.errors),
    }


def _get_serializer_update_data(user, user_data, update_mode=""):
    user_data.pop("redirect_organization_code", "")
    if update_mode == "no_update":
        return {"email": user.email}
    if update_mode == "soft":
        user_data = {
            key: value
            for key, value in user_data.items()
            if (
                key in ["roles_to_add", "sdgs"]
                or (value and not getattr(user, key, None))
            )
        }
    elif update_mode == "hard":
        user_data = {key: value for key, value in user_data.items() if value}
    else:
        raise ValueError("Invalid update mode")
    user_data["sdgs"] = list(
        set([int(i) for i in user_data.get("sdgs", []) + user.sdgs])
    )
    user_data["email"] = user.email
    return user_data


def _update_user_from_csv_data(request, user, user_data, update_mode="no_update"):
    user_data = _get_serializer_update_data(user, user_data, update_mode)
    serializer = UserSerializer(
        user,
        data=user_data,
        context={"request": request},
        partial=True,
    )
    if serializer.is_valid():
        instance = serializer.save()
        KeycloakService.update_user(instance)
        return {"email": user_data["email"], "status": "updated", "error": ""}
    return {
        "email": user_data["email"],
        "status": "error",
        "error": json.dumps(serializer.errors),
    }


def _batch_create_users(users_data, request_user_pk, update_mode="no_update"):
    request = Request()
    request.user = ProjectUser.objects.get(pk=request_user_pk)
    email_text = "CSV import results:\n"
    output_file = f"import_users_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}.csv"
    with open(output_file, "w") as output_csv:
        writer = csv.DictWriter(output_csv, fieldnames=["email", "status", "error"])
        writer.writeheader()
        for user_data in users_data:
            try:
                user_data = _clean_user_data_from_csv(user_data)
                user = ProjectUser.objects.filter(
                    Q(external_id=user_data.get("external_id", None))
                    | Q(email=user_data["email"])
                ).distinct()
                if user.exists():
                    results = _update_user_from_csv_data(
                        request, user.get(), user_data, update_mode
                    )
                else:
                    results = _create_user_from_csv_data(request, user_data)

            except Exception as e:  # noqa
                results = {
                    "email": user_data["email"],
                    "status": "error",
                    "error": str(e),
                }
            writer.writerow(results)
            email_text += f"{results['email']};{results['status']};{results['error']}\n"

    with open(output_file, "r") as output_csv:
        send_email_with_attached_file(
            "Projects - CSV import results",
            email_text,
            [request.user.email],
            output_csv,
            "text/csv",
        )
