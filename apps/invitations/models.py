import uuid
from typing import List

from django.db import models, transaction

from apps.accounts.models import ProjectUser
from apps.accounts.utils import get_default_group
from apps.commons.models import HasOwner
from apps.emailing.utils import render_message, send_email
from apps.organizations.models import Organization
from services.keycloak.interface import KeycloakService

from .exceptions import InvalidEmailTypeError


class Invitation(models.Model, HasOwner):
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE
    )
    people_group = models.ForeignKey(
        "accounts.PeopleGroup", on_delete=models.CASCADE, null=True
    )
    token = models.UUIDField(default=uuid.uuid4)
    description = models.CharField(max_length=255, blank=True)
    owner = models.ForeignKey(
        "accounts.ProjectUser", on_delete=models.CASCADE, related_name="invitations"
    )
    expire_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is the owner of the object."""
        return self.owner == user

    def get_owner(self):
        """Get the owner of the object."""
        return self.owner


class AccessRequest(models.Model):
    """
    A request to access an organization.
    It can be created by an existing user or by a new user.
    """

    class Status(models.TextChoices):
        PENDING = "pending"
        ACCEPTED = "accepted"
        DECLINED = "declined"

    class EmailType(models.TextChoices):
        REQUEST_CREATED = "request_created"
        REQUEST_ACCEPTED = "request_accepted"
        REQUEST_DECLINED = "request_declined"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="access_requests",
    )
    user = models.ForeignKey(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        related_name="access_requests",
        null=True,
    )
    email = models.CharField(max_length=255, blank=True)
    given_name = models.CharField(max_length=255, blank=True)
    family_name = models.CharField(max_length=255, blank=True)
    job = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.given_name} {self.family_name} ({self.email})"

    @property
    def contact_email(self):
        if self.user:
            if hasattr(self.user, "keycloak_account"):
                return self.user.keycloak_account.email
            return self.user.email
        return self.email

    @property
    def contact_language(self):
        if self.user:
            return self.user.language
        return self.organization.language

    @property
    def template_user(self):
        if self.user:
            return self.user
        return {
            "given_name": self.given_name,
            "family_name": self.family_name,
            "email": self.email,
            "job": self.job,
        }

    def send_email(self, email_type: str, emails: List[str] = None):
        if email_type not in self.EmailType.values:
            raise InvalidEmailTypeError(email_type=email_type)
        subject, _ = render_message(
            f"{email_type}/object",
            self.contact_language,
            organization=self.organization,
            user=self.template_user,
            request_id=self.id,
        )
        text, html = render_message(
            f"{email_type}/mail",
            self.contact_language,
            organization=self.organization,
            user=self.template_user,
            request_id=self.id,
            message=self.message,
        )

        if emails is None:
            emails = [self.contact_email]
        send_email(subject, text, emails, html_content=html)

    @transaction.atomic
    def accept(self):
        self.user.groups.add(self.organization.get_users())
        self.status = AccessRequest.Status.ACCEPTED
        self.save()
        self.send_email(AccessRequest.EmailType.REQUEST_ACCEPTED)

    def accept_and_create(self):
        with transaction.atomic():
            self.user = ProjectUser.objects.create(
                email=self.email,
                given_name=self.given_name,
                family_name=self.family_name,
                job=self.job,
                language=self.organization.language,
            )
            self.user.groups.add(
                self.organization.get_users(),
                get_default_group(),
            )
            keycloak_account = KeycloakService.create_user(self.user)
            self.status = AccessRequest.Status.ACCEPTED
            self.save()
        KeycloakService.send_email(
            keycloak_account=keycloak_account,
            email_type=KeycloakService.EmailType.ADMIN_CREATED,
            redirect_organization_code=self.organization.code,
        )

    @transaction.atomic
    def decline(self):
        self.status = AccessRequest.Status.DECLINED
        self.save()
        self.send_email(AccessRequest.EmailType.REQUEST_DECLINED)

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return [self.organization]

    class Meta:
        permissions = (("manage_accessrequest", "Can manage access requests"),)
