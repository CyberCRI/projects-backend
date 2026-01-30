from contextlib import suppress
from typing import Any

from django.contrib import admin, messages
from django.db.models import Count
from django.db.models.query import QuerySet
from django.http.request import HttpRequest

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.commons.admin import TranslateObjectAdminMixin
from services.crisalid.manager import CrisalidQuerySet
from services.crisalid.tasks import vectorize_documents

from .models import (
    CrisalidConfig,
    Document,
    DocumentContributor,
    Identifier,
    Researcher,
    Structure,
)


class IdentifierAminMixin:
    @admin.display(description="identifiers count", ordering="identifiers_count")
    def get_identifiers(self, instance):
        # list all harvester name from this profile
        result = [o.harvester for o in instance.identifiers.all()]
        if not result:
            return None

        return f"{', '.join(result)} ({len(result)})"


@admin.register(Identifier)
class IdentifierAdmin(admin.ModelAdmin):
    list_display = ("harvester", "value", "get_researcher", "get_documents")
    search_fields = ("harvester", "value")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("researchers", "documents")
            .annotate(documents_count=Count("documents__id", distinct=True))
            .annotate(researchers_count=Count("researchers__id", distinct=True))
        )

    @admin.display(description="researchers assosiate", ordering="researchers_count")
    def get_researcher(self, instance):
        return instance.researchers_count

    @admin.display(description="documents assosiate", ordering="documents_count")
    def get_documents(self, instance):
        return instance.documents_count


class DocumentContributorAdminInline(admin.StackedInline):
    model = DocumentContributor
    extra = 0


@admin.register(Document)
class DocumentAdmin(TranslateObjectAdminMixin, IdentifierAminMixin, admin.ModelAdmin):
    list_display = (
        "title",
        "publication_date",
        "document_type",
        "get_contributors",
        "get_identifiers",
    )
    search_fields = (
        "title",
        "publication_date",
        "document_type",
        "contributors__given_name",
        "contributors__family_name",
        "identifiers__value",
        "identifiers__harvester",
    )
    inlines = (DocumentContributorAdminInline,)

    actions = ("vectorize",)

    def vectorize(self, request, queryset):
        # run vecotrize async in celery
        documents_pks = list(queryset.values_list("pk", flat=True))
        vectorize_documents.apply_async((documents_pks,))
        messages.add_message(
            request,
            messages.INFO,
            f"Vecotrize Task created for {len(documents_pks)} documents",
        )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("contributors", "identifiers")
            .annotate(identifiers_count=Count("identifiers__id"))
            .annotate(contributors_count=Count("contributors__id", distinct=True))
        )

    @admin.display(description="contributors count", ordering="contributors_count")
    def get_contributors(self, instance):
        return instance.contributors.count()


@admin.register(Researcher)
class ResearcherAdmin(IdentifierAminMixin, admin.ModelAdmin):
    list_display = (
        "given_name",
        "family_name",
        "user",
        "get_documents",
        "get_memberships",
        "get_employments",
        "get_identifiers",
    )
    search_fields = (
        "user__given_name",
        "user__family_name",
        "identifiers__value",
        "identifiers__harvester",
    )
    autocomplete_fields = ("user",)
    actions = ("assign_user",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user")
            .prefetch_related("identifiers", "documents")
            .annotate(identifiers_count=Count("identifiers__id"))
            .annotate(documents_count=Count("documents__id", distinct=True))
            .annotate(memberships_count=Count("memberships__id", distinct=True))
            .annotate(employments_count=Count("employments__id", distinct=True))
        )

    @admin.action(description="assign researcher on projects")
    def assign_user(self, request, queryset):
        """Assign research to user if matching user/eppn"""
        researcher_updated = []
        created = assigned = notfound = 0

        for research in queryset.prefetch_related("identifiers").select_related("user"):
            # already set
            if research.user:
                continue

            for identifier in research.identifiers.all():
                if identifier.harvester != Identifier.Harvester.LOCAL.value:
                    continue

                user = None
                email = identifier.value
                with suppress(ProjectUser.DoesNotExist):
                    user = ProjectUser.objects.get(email=email)

                if not user:
                    created += 1
                    user = ProjectUser(
                        email=email,
                        given_name=research.given_name,
                        family_name=research.family_name,
                    )
                    user.save()
                else:
                    assigned += 1

                research.user = user
                researcher_updated.append(research)
                break
            else:
                notfound += 1

        Researcher.objects.bulk_update(researcher_updated, fields=["user"])

        if created:
            messages.add_message(request, messages.INFO, f"Create {created} user.")
        if assigned:
            messages.add_message(request, messages.INFO, f"Assign {assigned} user.")
        if notfound:
            messages.add_message(
                request, messages.ERROR, f"Can't found {notfound} user with eppn."
            )

    @admin.display(description="documents count", ordering="documents_count")
    def get_documents(self, instance):
        return instance.documents_count

    @admin.display(description="number of memberships", ordering="-memberships_count")
    def get_memberships(self, instance):
        return instance.memberships_count

    @admin.display(description="number of employments", ordering="-employments_count")
    def get_employments(self, instance):
        return instance.employments_count


@admin.register(Structure)
class StructureAdmin(IdentifierAminMixin, admin.ModelAdmin):
    list_display = (
        "acronym",
        "name",
        "organization",
        "get_memberships",
        "get_employments",
        "get_identifiers",
    )
    search_fields = ("acronym", "name", "organization__code")
    autocomplete_fields = ("organization",)
    actions = ("assign_group",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return (
            super()
            .get_queryset(request)
            .select_related("organization")
            .annotate(
                memberships_count=Count("memberships__pk", distinct=True),
                employments_count=Count("employments__pk", distinct=True),
            )
        )

    @admin.action(description="create/update groups")
    def assign_group(self, request, queryset: CrisalidQuerySet):
        for structure in queryset:
            name = structure.name or structure.acronym
            if not name:
                continue

            parent = PeopleGroup.update_or_create_root(structure.organization)
            group = PeopleGroup.objects.filter(
                parent=parent, name=name, organization=structure.organization
            ).first()
            if not group:
                group = PeopleGroup(
                    name=name, parent=parent, organization=structure.organization
                )

            group.save()
            member_group = group.get_members()
            for membership in structure.memberships.select_related("user").filter(
                user__isnull=False
            ):
                membership.user.groups.add(member_group)

    @admin.display(description="number of memberships", ordering="-memberships_count")
    def get_memberships(self, instance):
        return instance.memberships_count

    @admin.display(description="number of employments", ordering="-employments_count")
    def get_employments(self, instance):
        return instance.employments_count


@admin.register(CrisalidConfig)
class CrisalidConfigAdmin(admin.ModelAdmin):
    list_display = ("organization", "active")
    search_fields = ("organization__code", "active")
    autocomplete_fields = ("organization",)
    actions = ("active_connections", "deactive_connections")

    @admin.action(description="run/reload crisalidbus connections")
    def active_connections(self, request, queryset):
        """method to change/run crisalidbus listener"""
        # we don't update directly queryset for signals dispatch
        total = queryset.count()
        for obj in queryset:
            obj.active = True
            obj.save()

        messages.add_message(
            request,
            messages.INFO,
            f"CrisalidBus listener started or reloaded ({total}).",
        )

    @admin.action(description="stop crisalidbus connections")
    def deactive_connections(self, request, queryset):
        """method to change/stop crisalidbus listener"""
        # we don't update directly queryset for signals dispatch
        total = queryset.count()
        for obj in queryset:
            obj.active = False
            obj.save()

        messages.add_message(
            request,
            messages.INFO,
            f"CrisalidBus listener stoped ({total}).",
        )
