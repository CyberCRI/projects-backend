import logging
import uuid
from contextlib import suppress

from django.conf import settings
from django.utils import timezone
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken

from apps.commons.mixins import HasPermissionsSetup
from apps.invitations.models import Invitation

from .exceptions import (
    InactiveUserError,
    InvalidInvitationError,
    InvalidTokenError,
)
from .models import InvitationUser, ProjectUser

logger = logging.getLogger(__name__)


class BearerToken(AccessToken):
    token_type = "Bearer"  # nosec

    @classmethod
    def for_user(cls, user: "ProjectUser"):
        """
        Returns an authorization token for the given user that will be provided
        after authenticating the user's credentials.
        """
        user_id = user.keycloak_account.keycloak_id
        if not isinstance(user_id, int):
            user_id = str(user_id)

        token = cls()
        token[api_settings.USER_ID_CLAIM] = user_id

        return token


class AdminAuthentication(OIDCAuthenticationBackend):

    def describe_user_by_claims(self, claims: dict):
        keycloak_id = claims.get(settings.SIMPLE_JWT["USER_ID_CLAIM"])
        return "keycloak_id {}".format(keycloak_id)

    def filter_users_by_claims(self, claims: dict):
        """Return all users matching the specified keycloak_id."""
        keycloak_id = claims.get(settings.SIMPLE_JWT["USER_ID_CLAIM"])
        if not keycloak_id:
            return ProjectUser.objects.none()
        return ProjectUser.objects.filter(keycloak_account__keycloak_id=keycloak_id)

    def verify_claims(self, claims: dict):
        return True

    def create_user(self, claims: dict):
        return ProjectUser.import_from_keycloak(
            claims[settings.SIMPLE_JWT["USER_ID_CLAIM"]]
        )


class ProjectJWTAuthentication(JWTAuthentication):
    """
    custom authentication class for DRF and JWT
    https://github.com/encode/django-rest-framework/blob/master/rest_framework/authentication.py
    """

    def _create_user(self, payload: dict) -> ProjectUser:
        """
        Create user if present in keycloak but not yet in Projects.
        """
        return ProjectUser.import_from_keycloak(
            payload[settings.SIMPLE_JWT["USER_ID_CLAIM"]]
        )

    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        token_type = header.split()[0]
        if token_type.decode("utf-8") == "Invite":
            return self.get_invitation_user(raw_token), raw_token
        validated_token = self.get_validated_token(raw_token)
        user, token = self.get_user(validated_token), validated_token
        ProjectUser.objects.filter(id=user.id).update(
            last_login=timezone.localtime(timezone.now())
        )
        self._reassign_users_groups_permissions(user)
        return user, token

    def _reassign_users_groups_permissions(self, user: "ProjectUser"):
        """Reassign the permissions of the given group to its users."""
        for model in HasPermissionsSetup.__subclasses__():
            instances = model.objects.filter(
                permissions_up_to_date=False, groups__users=user
            )
            if instances.exists():
                for instance in instances:
                    instance.setup_permissions()

    # https://github.com/jazzband/djangorestframework-simplejwt/blob/cd4ea99424ec7256291253a87f3435fec01ecf0e/rest_framework_simplejwt/authentication.py#L109
    # Overriden to use function _create_user
    def get_user(self, validated_token):
        """
        Attempts to find and return a user using the given validated token.
        """
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError as err:
            raise InvalidTokenError from err
        try:
            user = self.user_model.objects.get(**{api_settings.USER_ID_FIELD: user_id})
        except self.user_model.DoesNotExist:
            return self._create_user(validated_token)

        if not user.is_active:
            raise InactiveUserError

        return user

    def get_invitation_user(self, validated_token):
        queryset = Invitation.objects.filter(
            token=uuid.UUID(validated_token.decode("utf-8")),
            expire_at__gt=timezone.localtime(timezone.now()),
        )
        with suppress(Invitation.DoesNotExist):
            return InvitationUser(invitation=queryset.get())
        raise InvalidInvitationError


class KeycloakJWTAuthenticationExtension(OpenApiAuthenticationExtension):
    target_class = JWTAuthentication
    name = "KeycloakJWT"  # name used in the schema

    def get_security_definition(self, auto_schema):
        keycloak_url = settings.KEYCLOAK_SERVER_URL
        if hasattr(settings, "KEYCLOAK_SERVER_PUBLIC_URL"):
            keycloak_url = settings.KEYCLOAK_SERVER_PUBLIC_URL
        return {
            "type": "openIdConnect",
            "name": "Authorization",
            "description": "OIDC access token from Keycloak",
            "openIdConnectUrl": f"{keycloak_url}/realms/{settings.KEYCLOAK_REALM}/.well-known/openid-configuration",
        }
