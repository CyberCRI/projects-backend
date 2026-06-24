from django.db.models import QuerySet, Value

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.announcements.models import Announcement
from apps.commons.models import GroupData
from apps.feedbacks.models import Comment, Review
from apps.files.models import AttachmentFile, AttachmentLink
from apps.modules.base import AbstractModules, register_module
from apps.projects.models import (
    BlogEntry,
    Goal,
    LinkedProject,
    Location,
    Project,
    ProjectMessage,
)


@register_module(Project)
class ProjectModules(AbstractModules):
    instance: Project

    def members(self) -> QuerySet[ProjectUser]:

        def queryset_users(role: GroupData.Role, priority_role_order: int):
            group_data = GroupData.objects.filter(
                role=role, group__projects=self.instance
            )
            return ProjectUser.objects.filter(groups__data__in=group_data).annotate(
                role=Value(role), priority_role_order=Value(priority_role_order)
            )

        # get all members and annote role
        owners = queryset_users(GroupData.Role.OWNERS, 1)
        members = queryset_users(GroupData.Role.MEMBERS, 2)
        reviewers = queryset_users(GroupData.Role.REVIEWERS, 3)

        # union all and filter by request.user
        all_members = owners | members | reviewers
        return (
            all_members.distinct()
            .filter(pk__in=self.user.get_user_queryset())
            .order_by("priority_role_order")
            .distinct()
        )

    def groups(self) -> QuerySet[PeopleGroup]:
        def queryset_groups(role: GroupData.Role, priority_role_order: int):
            group_data = GroupData.objects.filter(
                role=role, group__projects=self.instance
            )
            return PeopleGroup.objects.filter(groups__data__in=group_data).annotate(
                role=Value(role), priority_role_order=Value(priority_role_order)
            )

        # get all members and annote role
        owner_groups = queryset_groups(GroupData.Role.OWNER_GROUPS, 1)
        member_groups = queryset_groups(GroupData.Role.MEMBER_GROUPS, 2)
        reviewer_groups = queryset_groups(GroupData.Role.REVIEWER_GROUPS, 3)

        # union all and filter by request.user
        all_groups = owner_groups | member_groups | reviewer_groups
        return (
            all_groups.distinct()
            .filter(pk__in=self.user.get_people_group_queryset())
            .order_by("priority_role_order")
            .distinct()
        )

    def linked_projects(self) -> QuerySet[Project]:
        return self.instance.linked_projects.filter(
            project__in=self.user.get_project_queryset()
        )

    def similars(self) -> QuerySet[Project]:
        return self.instance.similars().filter(pk__in=self.user.get_project_queryset())

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

    def messages(self) -> QuerySet[ProjectMessage]:
        return self.instance.messages.all()
