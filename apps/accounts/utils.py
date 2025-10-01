import json
from base64 import b64decode
from typing import Any, Dict, List, Optional, Tuple, Union

import jwt
from cryptography.hazmat.primitives import serialization
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from googleapiclient.errors import HttpError
from guardian.shortcuts import assign_perm, get_group_perms
from keycloak import KeycloakError
from rest_framework.request import Request

from apps.commons.mixins import HasPermissionsSetup

from .exceptions import (
    ExpiredTokenError,
    GoogleSyncError,
    KeycloakSyncError,
    TokenPrefixMissingError,
)


def decode_token(request: Request) -> Optional[Dict[str, Any]]:
    """Decode the request's JWT token."""
    authorization_header = request.headers.get("Authorization")
    if not authorization_header:
        return None
    try:
        access_token = authorization_header.split(" ")[1]
        base64_public_key = settings.AUTH_CONFIG["PUBLIC_KEY"]
        public_key = b64decode(base64_public_key)
        if settings.AUTH_CONFIG["VERIFY_SIGNATURE"]:
            public_key = serialization.load_der_public_key(public_key)
        return jwt.decode(
            access_token,
            public_key,
            algorithms=["RS256"],
            options={"verify_signature": settings.AUTH_CONFIG["VERIFY_SIGNATURE"]},
        )
    except jwt.ExpiredSignatureError:
        raise ExpiredTokenError
    except IndexError:
        raise TokenPrefixMissingError


def get_default_group_permissions():
    return Permission.objects.filter(codename__in=["add_follow", "add_comment"])


def get_superadmins_group_permissions():
    return Permission.objects.all()


def get_default_group():
    group, created = Group.objects.get_or_create(name="default")
    if created:
        for permission in get_default_group_permissions():
            assign_perm(permission, group)
    return group


def get_superadmins_group():
    group, created = Group.objects.get_or_create(name="superadmins")
    if created:
        for permission in get_superadmins_group_permissions():
            assign_perm(permission, group)
    return group


def get_permission_representation(
    permission: Union[Permission, str], instance: Optional[HasPermissionsSetup] = None
) -> str:
    if instance:
        content_type = ContentType.objects.get_for_model(instance)
        return f"{content_type.app_label}.{permission}.{instance.pk}"
    return f"{permission.content_type.app_label}.{permission.codename}"


def get_instance_from_group(group: Group) -> Optional[HasPermissionsSetup]:
    """
    Get the related instance from a django.contrib.auth.models.Group instance.
    The instance can be an Organization, a Project or a PeopleGroup.

    The projects check must absolutely come before the people_groups check, because
    a project can have a people_group as a member. The concerned group is related to
    both the project and the people_group, but the project is the one that should be
    returned.
    """
    if group.data.exists():
        return group.data.get().instance
    return None


def get_group_permissions(group: Group) -> List[str]:
    instance = get_instance_from_group(group)
    if instance:
        return list(
            set(
                [
                    get_permission_representation(permission, instance)
                    for permission in get_group_perms(group, instance)
                ]
            )
        )
    return list(
        set(
            [
                get_permission_representation(permission)
                for permission in group.permissions.all()
            ]
        )
    )


def get_permission_from_representation(
    representation: str,
) -> Tuple[Optional[str], Optional[HasPermissionsSetup]]:
    split_representation = representation.split(".")
    if len(split_representation) == 2:
        return representation, None
    if len(split_representation) == 3:
        app_label = split_representation[0]
        codename = split_representation[1]
        object_pk = split_representation[2]
        permission = Permission.objects.filter(
            content_type__app_label=app_label, codename=codename
        )
        if permission.exists() and permission.count() == 1:
            permission = permission.get()
            model = apps.get_model(app_label, permission.content_type.model)
            instance = model.objects.get(pk=object_pk)
            return f"{app_label}.{codename}", instance
    return None, None


def default_onboarding_status():
    return {"show_welcome": True}


def account_sync_errors_handler(
    keycloak_error: Union[KeycloakError, Tuple[KeycloakError]] = KeycloakError,
    google_error: HttpError = HttpError,
):
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            try:
                return func(request, *args, **kwargs)
            except keycloak_error as e:
                message = json.loads(e.response_body.decode()).get("errorMessage")
                raise KeycloakSyncError(message=message, code=e.response_code)
            except google_error as e:
                raise GoogleSyncError(message=e.reason, code=e.status_code)

        return wrapper

    return decorator
