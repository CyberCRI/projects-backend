from django.db.models import Case, Prefetch, Q, QuerySet, Value, When

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.modules.base import AbstractModules, register_module
from apps.projects.models import Location, Project
from apps.skills.models import Skill
from services.crisalid.models import Document, DocumentTypeCentralized


@register_module(PeopleGroup)
class PeopleGroupModules(AbstractModules):
    instance: PeopleGroup

    def members(self) -> QuerySet[ProjectUser]:
        managers_ids = self.instance.managers.all().values_list("id", flat=True)
        leaders_ids = self.instance.leaders.all().values_list("id", flat=True)
        skills_prefetch = Prefetch(
            "skills", queryset=Skill.objects.select_related("tag")
        )
        return (
            self.instance.get_all_members()
            .distinct()
            .annotate(
                is_leader=Case(
                    When(id__in=leaders_ids, then=True), default=Value(False)
                )
            )
            .annotate(
                is_manager=Case(
                    When(id__in=managers_ids, then=True), default=Value(False)
                )
            )
            .order_by("-is_leader", "-is_manager")
            .prefetch_related(skills_prefetch, "groups")
        )

    def featured_projects(self) -> QuerySet[Project]:
        group_projects_ids = (
            Project.objects.filter(groups__people_groups=self.instance)
            .distinct()
            .values_list("id", flat=True)
        )

        return (
            self.user.get_project_queryset()
            .filter(
                Q(groups__people_groups=self.instance) | Q(people_groups=self.instance)
            )
            .annotate(
                is_group_project=Case(
                    When(id__in=group_projects_ids, then=True), default=Value(False)
                ),
                is_featured=Case(
                    When(people_groups=self.instance, then=True), default=Value(False)
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

    def projects_locations(self) -> QuerySet[Location]:
        return Location.objects.filter(project__in=self.featured_projects())

    def _documents(self, documents_type: DocumentTypeCentralized) -> QuerySet[Document]:
        members_qs = self.members()
        return Document.objects.filter(
            document_type__in=documents_type,
            contributors__user__in=members_qs,
        ).distinct()

    def publications(self) -> QuerySet[Document]:
        return self._documents(DocumentTypeCentralized.publications)

    def conferences(self) -> QuerySet[Document]:
        return self._documents(DocumentTypeCentralized.conferences)
