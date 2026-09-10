from functools import cached_property

from django.contrib.auth.models import Group
from django.db.models import (
    QuerySet,
)

from apps.accounts.models import (
    AnonymousUser,
    PeopleGroup,
    PrivacySettings,
    ProjectUser,
)
from apps.accounts.utils import get_superadmins_group
from apps.commons.models import GroupData
from apps.files.models import ProjectUserAttachmentFile, ProjectUserAttachmentLink
from apps.modules.base import AbstractModules, organization_related, register_module
from apps.notifications.models import Notification
from apps.organizations.models import CategoryFollow
from apps.projects.models import Project
from apps.skills.models import Mentoring, Skill
from services.crisalid.models import Document, DocumentTypeCentralized, Researcher


@register_module(ProjectUser)
class UserModules(AbstractModules):
    instance: ProjectUser

    @cached_property
    def _privacy_settings(self):
        """generate a privacy informations (only for sklls now) to filter queryset"""

        # return privacy filde from user
        privacy = self.instance.privacy_settings

        # privacy "ORGANIZATION"
        in_organization = self.instance.groups.filter(
            organizations__isnull=False,
            organizations__in=self.user.get_organizations_queryset(),
        ).exists()

        # privacy "hide"
        is_connected = self.user.is_authenticated
        if isinstance(self.user, AnonymousUser):
            is_admin = False
        else:
            is_admin = self.user.groups.contains(get_superadmins_group()) or (
                Group.objects.filter(
                    organizations__isnull=False,
                    organizations__in=self.instance.get_related_organizations(),
                    name__contains="admins",
                    users=self.user,
                ).exists()
            )
        # is same user
        is_same_user = self.user.pk == self.instance.pk

        # return boolean for each privacy field
        return {
            "skills": any(
                (
                    is_same_user,
                    is_connected
                    and is_admin
                    and privacy.skills == PrivacySettings.PrivacyChoices.HIDE,
                    in_organization
                    and privacy.skills == PrivacySettings.PrivacyChoices.ORGANIZATION,
                )
            )
        }

    def skills(self) -> QuerySet[Skill]:
        qs = self.instance.skills.all()
        if self._privacy_settings["skills"]:
            return qs
        return qs.none()

    @organization_related
    def mentor(self) -> QuerySet[Mentoring]:
        return self.instance.mentor_mentorings.all()

    @organization_related
    def mentoree(self) -> QuerySet[Mentoring]:
        return self.instance.mentoree_mentorings.all()

    @organization_related
    def follows_projects(self) -> QuerySet[Project]:
        qs = self.user.get_project_queryset()
        follows_projects = self.instance.follows.all()
        return qs.filter(follows__in=follows_projects)

    def follows_categories(self) -> QuerySet[CategoryFollow]:
        return self.instance.category_follows.all()

    def files(self) -> QuerySet[ProjectUserAttachmentFile]:
        return self.instance.files.all()

    def links(self) -> QuerySet[ProjectUserAttachmentLink]:
        return self.instance.links.all()

    @organization_related
    def groups(self) -> QuerySet[PeopleGroup]:
        return (
            self.user.get_people_group_queryset()
            .filter(groups__users=self.instance, is_root=False)
            .distinct()
        )

    @organization_related
    def projects(self) -> QuerySet[Project]:
        return (
            self.user.get_project_queryset()
            .filter(groups__users=self.instance)
            .distinct()
        )

    @organization_related
    def reviews_projects(self) -> QuerySet[Project]:
        return self.user.get_project_queryset().filter(
            groups__data__role=GroupData.Role.REVIEWERS,
            groups__users=self.instance,
        )

    @organization_related
    def notifications(self) -> QuerySet[Notification]:
        return self.instance.notifications_received.filter(is_viewed=False)

    @cached_property
    def _researcher(self) -> Researcher | None:
        try:
            return self.instance.researcher
        except ProjectUser.researcher.RelatedObjectDoesNotExist:
            return None

    # create dynamicly all research plucations types to modules
    for name, document_types in DocumentTypeCentralized.items():

        def _name(self, document_types=document_types):
            researcher = self._researcher
            if not researcher:
                return Document.objects.none()
            return researcher.documents.filter(document_type__in=document_types)

        _name.__name__ = name
        locals()[name] = _name
