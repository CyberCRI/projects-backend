from django.db.models import Case, Prefetch, Q, QuerySet, Value, When

from apps.accounts.models import PeopleGroup, PeopleGroupLocation, ProjectUser
from apps.commons.models import GroupData
from apps.files.models import PeopleGroupImage
from apps.modules.base import AbstractModules, register_module
from apps.newsfeed.models import Event, EventLocation, NewsLocation
from apps.projects.models import Location, Project
from apps.skills.models import Skill
from services.crisalid.models import Document, DocumentTypeCentralized


@register_module(PeopleGroup)
class PeopleGroupModules(AbstractModules):
    instance: PeopleGroup

    def members(self) -> QuerySet[ProjectUser]:
        def queryset_users(role: GroupData.Role, priority_role_order: int):
            group_data = GroupData.objects.filter(
                role=role, group__people_groups=self.instance
            )

            return ProjectUser.objects.filter(groups__data__in=group_data).annotate(
                role=Value(role), priority_role_order=Value(priority_role_order)
            )

        skills_prefetch = Prefetch(
            "skills", queryset=Skill.objects.select_related("tag")
        )

        # get all members and annote rolepeople_groups
        leaders = queryset_users(GroupData.Role.LEADERS, 1)
        managers = queryset_users(GroupData.Role.MANAGERS, 2)
        members = queryset_users(GroupData.Role.MEMBERS, 3)

        # union all and filter by request.user
        all_members = leaders | managers | members

        return (
            all_members.distinct()
            .filter(pk__in=self.user.get_user_queryset())
            .prefetch_related(skills_prefetch)
            .order_by("priority_role_order")
            .distinct()
        )

    def featured_projects(self) -> QuerySet[Project]:
        group_projects = Project.objects.filter(
            groups__people_groups=self.instance
        ).distinct()

        return (
            self.user.get_project_queryset()
            .filter(
                Q(groups__people_groups=self.instance) | Q(people_groups=self.instance)
            )
            .annotate(
                is_group_project=Case(
                    When(id__in=group_projects, then=True),
                    default=Value(False),
                ),
                is_featured=Case(
                    When(people_groups=self.instance, then=True),
                    default=Value(False),
                ),
            )
            .distinct()
            .order_by("-is_featured", "-is_group_project")
            .prefetch_related("categories")
        )

    def similars(self) -> QuerySet[PeopleGroup]:
        return self.instance.similars().filter(
            pk__in=self.user.get_people_group_queryset()
        )

    def subgroups(self) -> QuerySet[PeopleGroup]:
        return self.instance.children.filter(
            pk__in=self.user.get_people_group_queryset()
        )

    def locations(self) -> QuerySet[Location]:
        qs_project = Location.objects.filter(project__in=self.featured_projects())
        qs_news = NewsLocation.objects.filter(news__in=self.news())
        qs_group = PeopleGroupLocation.objects.filter(people_group__in=self.subgroups())
        qs_location = PeopleGroupLocation.objects.filter(people_group=self.instance)
        qs_event = EventLocation.objects.filter(event__in=self.event())

        return (
            qs_group.union(qs_project)
            .union(qs_news)
            .union(qs_location)
            .union(qs_event)
            .values("lat", "lng", "id", "type", "title", "description")
        )

    def gallery(self):
        return PeopleGroupImage.objects.filter(people_group=self.instance)

    def news(self):
        return self.user.get_news_queryset().filter(people_groups=self.instance)

    def event(self) -> QuerySet[Event]:
        return self.user.get_event_queryset().filter(people_groups=self.instance)

    def _documents(self, documents_type: DocumentTypeCentralized) -> QuerySet[Document]:
        members_qs = self.members()
        return Document.objects.filter(
            document_type__in=documents_type, contributors__user__in=members_qs
        ).distinct()

    def publications(self) -> QuerySet[Document]:
        return self._documents(DocumentTypeCentralized.publications)

    def conferences(self) -> QuerySet[Document]:
        return self._documents(DocumentTypeCentralized.conferences)
