from django.db.models import (
    Case,
    CharField,
    IntegerField,
    QuerySet,
    Value,
    When,
)

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
        return (
            self.user.get_user_queryset()
            .filter(
                groups__data__role__in=(
                    GroupData.Role.OWNERS,
                    GroupData.Role.MEMBERS,
                    GroupData.Role.REVIEWERS,
                ),
                groups__projects=self.instance,
            )
            .annotate(
                role=Case(
                    When(
                        groups__data__role=GroupData.Role.OWNERS,
                        then=Value(GroupData.Role.OWNERS.value),
                    ),
                    When(
                        groups__data__role=GroupData.Role.MEMBERS,
                        then=Value(GroupData.Role.MEMBERS.value),
                    ),
                    When(
                        groups__data__role=GroupData.Role.REVIEWERS,
                        then=Value(GroupData.Role.REVIEWERS.value),
                    ),
                    output_field=CharField(),
                ),
                priority_role_order=Case(
                    When(groups__data__role=GroupData.Role.OWNERS, then=Value(1)),
                    When(groups__data__role=GroupData.Role.MEMBERS, then=Value(2)),
                    When(groups__data__role=GroupData.Role.REVIEWERS, then=Value(3)),
                    output_field=IntegerField(),
                ),
            )
            .order_by("priority_role_order")
            .distinct()
        )

    def groups(self) -> QuerySet[PeopleGroup]:
        return (
            self.user.get_people_group_queryset()
            .filter(
                groups__data__role__in=(
                    GroupData.Role.OWNER_GROUPS,
                    GroupData.Role.MEMBER_GROUPS,
                    GroupData.Role.REVIEWER_GROUPS,
                ),
                groups__projects=self.instance,
            )
            .annotate(
                role=Case(
                    When(
                        groups__data__role=GroupData.Role.OWNER_GROUPS,
                        then=Value(GroupData.Role.OWNER_GROUPS.value),
                    ),
                    When(
                        groups__data__role=GroupData.Role.MEMBER_GROUPS,
                        then=Value(GroupData.Role.MEMBER_GROUPS.value),
                    ),
                    When(
                        groups__data__role=GroupData.Role.REVIEWER_GROUPS,
                        then=Value(GroupData.Role.REVIEWER_GROUPS.value),
                    ),
                    output_field=CharField(),
                ),
                priority_role_order=Case(
                    When(groups__data__role=GroupData.Role.OWNER_GROUPS, then=Value(1)),
                    When(
                        groups__data__role=GroupData.Role.MEMBER_GROUPS, then=Value(2)
                    ),
                    When(
                        groups__data__role=GroupData.Role.REVIEWER_GROUPS,
                        then=Value(3),
                    ),
                    output_field=IntegerField(),
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
