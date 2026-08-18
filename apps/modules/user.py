from functools import cached_property

from django.db.models import (
    QuerySet,
)

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.files.models import ProjectUserAttachmentFile, ProjectUserAttachmentLink
from apps.modules.base import AbstractModules, register_module
from apps.notifications.models import Notification
from apps.organizations.models import CategoryFollow
from apps.projects.models import Project
from apps.skills.models import Mentoring, Skill
from services.crisalid.models import Document, DocumentTypeCentralized, Researcher


@register_module(ProjectUser)
class UserModules(AbstractModules):
    instance: ProjectUser

    def skills(self) -> QuerySet[Skill]:
        return self.instance.skills.all()

    def mentor(self) -> QuerySet[Mentoring]:
        return self.instance.mentor_mentorings.all()

    def mentoree(self) -> QuerySet[Mentoring]:
        return self.instance.mentoree_mentorings.all()

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

    def groups(self) -> QuerySet[PeopleGroup]:
        return (
            self.user.get_people_group_queryset()
            .filter(groups__users=self.instance, is_root=False)
            .distinct()
        )

    def projects(self) -> QuerySet[Project]:
        return (
            self.user.get_project_queryset()
            .filter(groups__users=self.instance)
            .distinct()
        )

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
