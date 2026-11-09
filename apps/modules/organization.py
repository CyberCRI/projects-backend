from django.db.models.manager import BaseManager

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.announcements.models import Announcement
from apps.files.models import AttachmentFile
from apps.modules.base import (
    AbstractModules,
    register_module,
)
from apps.newsfeed.models import Event, Instruction, News
from apps.organizations.models import Organization, ProjectCategory
from apps.projects.models import Project
from services.crisalid.models.researcher import Researcher
from services.crisalid.models.structure import Structure


@register_module(Organization)
class OrganizationModules(AbstractModules):
    instance: Organization
    organization = None

    def categories(self) -> BaseManager[ProjectCategory]:
        return self.instance.project_categories.all()

    def projects(self) -> BaseManager[Project]:
        return self.user.get_project_queryset().filter(
            organizations__in=(self.instance,)
        )

    def groups(self) -> BaseManager[PeopleGroup]:
        return self.user.get_people_group_queryset().filter(
            organizations__in=(self.instance,)
        )

    def announcements(self) -> BaseManager[Announcement]:
        return Announcement.objects.filter(projects__in=self.projects)

    def events(self) -> BaseManager[Event]:
        return Event.objects.filter(organization=self.instance)

    def news(self) -> BaseManager[News]:
        return News.objects.filter(organization=self.instance)

    def instructions(self) -> BaseManager[Instruction]:
        return Instruction.objects.filter(organization=self.instance)

    def structures(self) -> BaseManager[Structure]:
        return Structure.objects.filter(organization=self.instance)

    def users(self) -> BaseManager[ProjectUser]:
        return ProjectUser.objects.filter(groups__organizations__in=(self.instance,))

    def researchers(self) -> BaseManager[Researcher]:
        return Researcher.objects.filter(user__in=self.users)

    def files(self) -> BaseManager[AttachmentFile]:
        return self.instance.attachment_files.all()
