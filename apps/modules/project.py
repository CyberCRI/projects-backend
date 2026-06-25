from django.db.models import (
    Case,
    F,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, JSONObject
from pgvector.django import CosineDistance, VectorField
from services.mistral.models import ProjectEmbedding

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
    instance: OuterRef

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
