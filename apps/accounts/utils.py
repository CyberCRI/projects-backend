from base64 import b64decode
from typing import Any, Dict, List, Optional, Tuple, Union

import jwt
from cryptography.hazmat.primitives import serialization
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from guardian.shortcuts import assign_perm, get_group_perms
from rest_framework import exceptions
from rest_framework.request import Request

from apps.commons.db.abc import PermissionsSetupModel


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
        raise exceptions.AuthenticationFailed("access_token expired")
    except IndexError:
        raise exceptions.AuthenticationFailed("Token prefix missing")


def get_default_group_permissions():
    return Permission.objects.filter(
        codename__in=["add_project", "add_follow", "add_comment"]
    )


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
    permission: Union[Permission, str], instance: Optional[PermissionsSetupModel] = None
) -> str:
    if instance:
        content_type = ContentType.objects.get_for_model(instance)
        return f"{content_type.app_label}.{permission}.{instance.pk}"
    return f"{permission.content_type.app_label}.{permission.codename}"


def get_instance_from_group(group: Group) -> Optional[PermissionsSetupModel]:
    if group.projects.exists() and group.people_groups.exists():
        return group.projects.get()
    if group.projects.exists():
        return group.projects.get()
    if group.organizations.exists():
        return group.organizations.get()
    if group.people_groups.exists():
        return group.people_groups.get()
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
) -> Tuple[Optional[str], Optional[PermissionsSetupModel]]:
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
