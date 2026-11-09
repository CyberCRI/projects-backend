from apps.accounts.models import ProjectUser
from apps.announcements.models import Announcement
from apps.modules.base import (
    AbstractModules,
    register_module,
)
from apps.newsfeed.models import Event, Instruction, News
from apps.organizations.models import Organization
from services.crisalid.models.researcher import Researcher
from services.crisalid.models.structure import Structure


@register_module(Organization)
class OrganizationModules(AbstractModules):
    instance: Organization
    organization = None

    def projects(self):
        return self.user.get_project_queryset().filter(
            organizations__in=(self.instance,)
        )

    def groups(self):
        return self.user.get_people_group_queryset().filter(
            organizations__in=(self.instance,)
        )

    def announcements(self):
        return Announcement.objects.filter(projects__in=self.projects)

    def events(self):
        return Event.objects.filter(organization=self.instance)

    def news(self):
        return News.objects.filter(organization=self.instance)

    def instructions(self):
        return Instruction.objects.filter(organization=self.instance)

    def structures(self):
        return Structure.objects.filter(organization=self.instance)

    def users(self):
        return ProjectUser.objects.filter(groups__organizations__in=(self.instance,))

    def researchers(self):
        return Researcher.objects.filter(user__in=self.users)

    def files(self):
        return self.instance.attachment_files.all()
