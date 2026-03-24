from django.db.models import Case, Prefetch, Q, QuerySet, Value, When

from apps.accounts.models import PeopleGroup, PeopleGroupLocation, ProjectUser
from apps.files.models import PeopleGroupImage
from apps.modules.base import AbstractModules, register_module
from apps.newsfeed.models import Event, EventLocation, News, NewsLocation
from apps.projects.models import Location, Project
from apps.skills.models import Skill
from services.crisalid.models import Document, DocumentTypeCentralized


@register_module(PeopleGroup)
class PeopleGroupModules(AbstractModules):
    instance: PeopleGroup

    def members(self) -> QuerySet[ProjectUser]:
        skills_prefetch = Prefetch(
            "skills", queryset=Skill.objects.select_related("tag")
        )

        return (
            self.instance.get_all_members()
            .distinct()
            .annotate(
                is_leader=Case(
                    When(id__in=self.instance.leaders.all(), then=True),
                    default=Value(False),
                )
            )
            .annotate(
                is_manager=Case(
                    When(id__in=self.instance.managers.all(), then=True),
                    default=Value(False),
                )
            )
            .order_by("-is_leader", "-is_manager")
            .prefetch_related(skills_prefetch, "groups")
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
        return self.user.get_news_related_queryset(
            News.objects.filter(people_groups=self.instance), news_related_name="pk"
        )

    def event(self) -> QuerySet[Event]:
        return self.user.get_event_related_queryset(
            Event.objects.filter(people_groups=self.instance), event_related_name="pk"
        )

    def _documents(self, documents_type: DocumentTypeCentralized) -> QuerySet[Document]:
        members_qs = self.members()
        return Document.objects.filter(
            document_type__in=documents_type, contributors__user__in=members_qs
        ).distinct()

    def publications(self) -> QuerySet[Document]:
        return self._documents(DocumentTypeCentralized.publications)

    def conferences(self) -> QuerySet[Document]:
        return self._documents(DocumentTypeCentralized.conferences)
