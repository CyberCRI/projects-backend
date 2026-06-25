from django.db.models import (
    Case,
    CharField,
    IntegerField,
    OuterRef,
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
    LinkedProject,
    Location,
    Project,
    ProjectMessage,
)
from services.mistral.models import ProjectEmbedding


@register_module(Project)
class ProjectModules(AbstractModules):
    instance: OuterRef

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

    def linked_projects(self) -> QuerySet[LinkedProject]:
        return LinkedProject.objects.filter(target=self.instance).filter(
            project__in=self.user.get_project_queryset()
        )

    def similars(self) -> QuerySet[Project]:
        base_qs = self.outer_ref(ProjectEmbedding.objects.all())

        qs_similar = base_qs.vector_search(self.instance, 0.15)

        project_qs = self.outer_ref(self.user.get_project_queryset())

        return project_qs.filter(embedding__in=qs_similar)

    def locations(self) -> QuerySet[Location]:
        return Location.objects.filter(project=self.instance)

    def comments(self) -> QuerySet[Comment]:
        return Comment.objects.filter(project=self.instance)

    def goals(self) -> QuerySet[Goal]:
        return Goal.objects.filter(project=self.instance)

    def blogs(self) -> QuerySet[BlogEntry]:
        return BlogEntry.objects.filter(project=self.instance)

    def files(self) -> QuerySet[AttachmentFile]:
        return AttachmentFile.objects.filter(project=self.instance)

    def links(self) -> QuerySet[AttachmentLink]:
        return AttachmentLink.objects.filter(project=self.instance)

    def announcements(self) -> QuerySet[Announcement]:
        return Announcement.objects.filter(project=self.instance)

    def reviews(self) -> QuerySet[Review]:
        return Review.objects.filter(project=self.instance)

    def messages(self) -> QuerySet[ProjectMessage]:
        return ProjectMessage.objects.filter(project=self.instance)
