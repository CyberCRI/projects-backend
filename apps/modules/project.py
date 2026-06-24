from django.db.models import Case, QuerySet, Value, When

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.announcements.models import Announcement
from apps.commons.models import GroupData
from apps.feedbacks.models import Comment, Review
from apps.files.models import AttachmentFile, AttachmentLink
from apps.modules.base import AbstractModules, register_module
from apps.projects.models import (
    BlogEntry,
    Goal,
    Location,
    Project,
    ProjectMessage,
)


@register_module(Project)
class ProjectModules(AbstractModules):
    instance: Project

    def members(self) -> QuerySet[ProjectUser]:

        def queryset_users(role: GroupData.Role):
            group_data = GroupData.objects.filter(
                role=role, group__projects=self.instance
            )
            return ProjectUser.objects.filter(groups__data__in=group_data)

        # get all members and annote role
        owners = queryset_users(GroupData.Role.OWNERS)
        members = queryset_users(GroupData.Role.MEMBERS)
        reviewers = queryset_users(GroupData.Role.REVIEWERS)

        # union all and filter by request.user
        all_members = owners | members | reviewers
        return (
            all_members.distinct()
            .filter(pk__in=self.user.get_user_queryset())
            .annotate(
                role=Case(
                    When(pk__in=owners, then=Value(GroupData.Role.OWNERS)),
                    When(pk__in=members, then=Value(GroupData.Role.MEMBERS)),
                    When(pk__in=reviewers, then=Value(GroupData.Role.REVIEWERS)),
                ),
                # add sort order priority (first leader, manager and members)
                priority_role_order=Case(
                    When(pk__in=owners, then=1),
                    When(pk__in=members, then=2),
                    When(pk__in=reviewers, then=3),
                ),
            )
            .order_by("priority_role_order")
            .distinct()
        )

    def groups(self) -> QuerySet[PeopleGroup]:
        def queryset_groups(role: GroupData.Role):
            group_data = GroupData.objects.filter(
                role=role, group__projects=self.instance
            )
            return PeopleGroup.objects.filter(groups__data__in=group_data)

        # get all members and annote role
        owner_groups = queryset_groups(GroupData.Role.OWNER_GROUPS)
        member_groups = queryset_groups(GroupData.Role.MEMBER_GROUPS)
        reviewer_groups = queryset_groups(GroupData.Role.REVIEWER_GROUPS)

        # union all and filter by request.user
        all_groups = owner_groups | member_groups | reviewer_groups
        return (
            all_groups.distinct()
            .filter(pk__in=self.user.get_people_group_queryset())
            .annotate(
                role=Case(
                    When(pk__in=owner_groups, then=Value(GroupData.Role.OWNER_GROUPS)),
                    When(
                        pk__in=member_groups, then=Value(GroupData.Role.MEMBER_GROUPS)
                    ),
                    When(
                        pk__in=reviewer_groups,
                        then=Value(GroupData.Role.REVIEWER_GROUPS),
                    ),
                ),
                # add sort order priority (first leader, manager and members)
                priority_role_order=Case(
                    When(pk__in=owner_groups, then=1),
                    When(pk__in=member_groups, then=2),
                    When(pk__in=reviewer_groups, then=3),
                ),
            )
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
