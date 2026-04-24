from django.db.models import Case, Prefetch, Q, QuerySet, Value, When

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.announcements.models import Announcement
from apps.feedbacks.models import Comment, Review
from apps.files.models import AttachmentFile, AttachmentLink
from apps.modules.base import AbstractModules, register_module
from apps.projects.models import BlogEntry, Goal, Location, Project


@register_module(Project)
class ProjectModules(AbstractModules):
    instance: Project

    def members(self) -> QuerySet[ProjectUser]:

        owners = self.instance.get_owners().users.all().annotate(role=Value("owners"))
        reviewers = (
            self.instance.get_reviewers().users.all().annotate(role=Value("reviewers"))
        )
        members = (
            self.instance.get_members().users.all().annotate(role=Value("members"))
        )

        all_members = owners | reviewers | members
        return all_members.filter(pk__in=self.user.get_user_queryset())

    def groups(self) -> QuerySet[PeopleGroup]:
        return self.instance.get_all_groups().filter(
            pk__in=self.user.get_people_group_queryset()
        )

    def linked_projects(self) -> QuerySet[Project]:
        return self.instance.linked_projects.filter(
            project__in=self.user.get_project_queryset()
        )

    # def similars(self) -> QuerySet[Project]:
    #     return self.instance.similars().filter(pk__in=self.user.get_project_queryset())

    def locations(self) -> QuerySet[Location]:
        return self.instance.locations.all()

    def comments(self) -> QuerySet[Comment]:
        return self.instance.comments.all()

    def goals(self) -> QuerySet[Goal]:
        return self.instance.goals.all()

    def blogs(self) -> QuerySet[BlogEntry]:
        return self.instance.blog_entries.all()

    def files(self) -> QuerySet[AttachmentFile]:
        return self.instance.files.all()

    def links(self) -> QuerySet[AttachmentLink]:
        return self.instance.links.all()

    def announcements(self) -> QuerySet[Announcement]:
        return self.instance.announcements.all()

    def reviews(self) -> QuerySet[Review]:
        return self.instance.reviews.all()
