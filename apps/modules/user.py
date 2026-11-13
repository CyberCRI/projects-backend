from django.db.models import (
    QuerySet,
)

from apps.accounts.models import (
    PeopleGroup,
    ProjectUser,
)
from apps.commons.models import GroupData
from apps.files.models import ProjectUserAttachmentFile, ProjectUserAttachmentLink
from apps.modules.base import (
    AbstractModules,
    ignore_method,
    organization_related,
    register_module,
)
from apps.notifications.models import Notification
from apps.organizations.models import CategoryFollow
from apps.projects.models import Project
from apps.skills.models import Mentoring, Skill


@register_module(ProjectUser)
class UserModules(AbstractModules):
    instance: ProjectUser

    def skills(self) -> QuerySet[Skill]:
        return self.user.get_skills_queryset().filter(pk__in=self.instance.skills.all())

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

    @organization_related
    def follows_categories(self) -> QuerySet[CategoryFollow]:
        return self.instance.category_follows.all()

    def files(self) -> QuerySet[ProjectUserAttachmentFile]:
        return self.instance.files.all()

    def links(self) -> QuerySet[ProjectUserAttachmentLink]:
        return self.instance.links.all()

    @organization_related
    def groups(self) -> QuerySet[PeopleGroup]:
        return self.user.get_people_group_queryset().filter(
            groups__users=self.instance, is_root=False
        )

    @organization_related
    def projects(self) -> QuerySet[Project]:
        return self.user.get_project_queryset().filter(groups__users=self.instance)

    @organization_related
    def reviews_projects(self) -> QuerySet[Project]:
        return self.user.get_project_queryset().filter(
            groups__data__role=GroupData.Role.REVIEWERS,
            groups__users=self.instance,
        )

    @organization_related
    @ignore_method
    def all_notifications(self) -> QuerySet[Notification]:
        return self.instance.notifications_received.all()

    def notifications(self) -> QuerySet[Notification]:
        return self.all_notifications().filter(is_viewed=False)
