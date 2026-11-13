import json
import logging
from contextlib import suppress

from celery import group
from django import forms
from django.contrib import admin, messages
from django.contrib.admin.widgets import AdminFileWidget
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html
from django.views.generic import TemplateView

from apps.accounts.models import ProjectUser
from apps.commons.admin import ExtraAdminMixins, TranslateObjectAdminMixin
from apps.organizations.models import Organization
from services.crisalid.models.award import Award, AwardContributor
from services.crisalid.models.document import DocumentDomains, DocumentJournal
from services.crisalid.models.funding import Funding
from services.crisalid.models.patent import Patent, PatentContributor
from services.crisalid.models.researcher import ResearcherDomains
from services.crisalid.models.teaching import Teaching
from services.crisalid.tasks import (
    load_apollo_data,
    update_researcher_bio_ia,
    vectorize_documents,
    vectorize_researchers,
)
from services.crisalid.utils.structures import (
    sync_group_members,
    sync_structures,
    with_ancestors,
)

from .models import (
    AuthorityOrganization,
    AuthorityOrganizationIdentifier,
    CrisalidConfig,
    Document,
    DocumentContributor,
    DocumentIdentifier,
    Journal,
    JournalIdentifier,
    Researcher,
    ResearcherIdentifier,
    ResearcherStructure,
    Structure,
    StructureIdentifier,
    StructureRelation,
)

logger = logging.getLogger(__name__)


class IdentifierAdminMixin:
    @admin.display(description="identifiers count", ordering="identifiers_count")
    def get_identifiers(self, instance):
        # list all harvester name from this profile
        result = [o.harvester for o in instance.identifiers.all()]
        if not result:
            return None

        return f"{', '.join(result)} ({len(result)})"


def identifiers_inline(identifier_model):
    """identifiers are owned by the object, edited in its admin"""
    return type(
        f"{identifier_model.__name__}AdminInline",
        (admin.TabularInline,),
        {"model": identifier_model, "extra": 0},
    )


@admin.register(Journal)
class JournalAdmin(IdentifierAdminMixin, admin.ModelAdmin):
    list_display = (
        "pk",
        "title",
        "acronym",
        "get_identifiers",
    )
    search_fields = (
        "title",
        "acronym",
        "identifiers__value",
    )
    inlines = (identifiers_inline(JournalIdentifier),)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("identifiers")
            .annotate(identifiers_count=Count("identifiers", distinct=True))
        )


class DocumentDomainAdminInline(admin.StackedInline):
    model = DocumentDomains
    extra = 0


class DocumentJournalAdminInline(admin.StackedInline):
    model = DocumentJournal
    extra = 0


class DocumentContributorAdminInline(admin.StackedInline):
    model = DocumentContributor
    extra = 0


@admin.register(Document)
class DocumentAdmin(TranslateObjectAdminMixin, IdentifierAdminMixin, admin.ModelAdmin):
    list_display = (
        "title",
        "publication_date",
        "document_type",
        "get_identifiers",
        "get_contributors",
        "get_citations",
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
    inlines = (
        identifiers_inline(DocumentIdentifier),
        DocumentContributorAdminInline,
        DocumentJournalAdminInline,
        DocumentDomainAdminInline,
    )

    actions = ("vectorize",)

    def vectorize(self, request, queryset):
        # run vecotrize async in celery
        documents_pks = list(queryset.values_list("pk", flat=True))
        vectorize_documents.apply_async((documents_pks,))
        total = len(documents_pks)

        logger.info(
            "Run command `vectorize` for %s document(s) (admin=%s)",
            total,
            request.user,
        )

        messages.add_message(
            request,
            messages.INFO,
            f"Vecotrize Task created for {total} documents",
        )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("contributors", "identifiers")
            .annotate(identifiers_count=Count("identifiers", distinct=True))
            .annotate(contributors_count=Count("contributors", distinct=True))
            .annotate(citations_count=Count("journals", distinct=True))
        )

    @admin.display(description="contributors count", ordering="contributors_count")
    def get_contributors(self, instance):
        return instance.contributors_count

    @admin.display(description="citations count", ordering="citations_count")
    def get_citations(self, instance):
        return instance.citations_count


@admin.register(Award)
class AwardAdmin(TranslateObjectAdminMixin, admin.ModelAdmin):
    list_display = ("pk", "name", "get_researcher")
    search_fields = (
        "name",
        "description",
        "researchers__given_name",
        "researchers__family_name",
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return (
            super()
            .get_queryset(request)
            .annotate(ann_researcher_count=Count("researchers"))
        )

    @admin.display(
        ordering="ann_researcher_count", description="number of researcher(s)"
    )
    def get_researcher(self, instance: Award):
        return instance.ann_researcher_count


@admin.register(Patent)
class PatentAdmin(TranslateObjectAdminMixin, admin.ModelAdmin):
    list_display = ("pk", "name", "get_researcher")
    search_fields = (
        "name",
        "description",
        "researchers__given_name",
        "researchers__family_name",
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return (
            super()
            .get_queryset(request)
            .annotate(ann_researcher_count=Count("researchers"))
        )

    @admin.display(
        ordering="ann_researcher_count", description="number of researcher(s)"
    )
    def get_researcher(self, instance: Award):
        return instance.ann_researcher_count


class ResearcherDomainsAdminInline(admin.StackedInline):
    model = ResearcherDomains
    extra = 0


class ResearcherPatentInline(admin.StackedInline):
    model = PatentContributor
    extra = 0


class ResearcherAwardInline(admin.StackedInline):
    model = AwardContributor
    extra = 0


class TeachingInline(admin.StackedInline):
    model = Teaching
    extra = 0


class LinkedUser(admin.SimpleListFilter):
    title = "linked user"
    parameter_name = "linked_user"

    def lookups(self, request, model_admin):
        return [
            ("Yes", "with user linked"),
            ("No", "without user linked"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "Yes":
            return queryset.filter(user__isnull=True)
        if self.value() == "No":
            return queryset.filter(user__isnull=False)
        return queryset


class OrganizationObject(admin.SimpleListFilter):
    title = "organization"
    parameter_name = "organization"

    def lookups(self, request, model_admin):
        return list(Organization.objects.all().values_list("code", "name"))

    def queryset(self, request, queryset):
        organization = Organization.objects.filter(code=self.value()).first()
        if organization:
            return queryset.filter(user__groups__organizations__in=(organization,))
        return queryset


@admin.register(Researcher)
class ResearcherAdmin(IdentifierAdminMixin, admin.ModelAdmin):
    list_display = (
        "given_name",
        "family_name",
        "get_user",
        "get_documents",
        "get_identifiers",
        "get_citations",
    )
    search_fields = (
        "user__given_name",
        "user__family_name",
        "identifiers__value",
        "identifiers__harvester",
    )
    list_filter = (LinkedUser, OrganizationObject)
    autocomplete_fields = ("user",)
    actions = (
        "assign_user",
        "vectorize",
        "generate_description_ia",
    )
    inlines = (
        identifiers_inline(ResearcherIdentifier),
        ResearcherDomainsAdminInline,
        ResearcherPatentInline,
        ResearcherAwardInline,
        TeachingInline,
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user")
            .prefetch_related("identifiers", "documents")
        )

    def vectorize(self, request, queryset):
        # run vecotrize async in celery
        researchers_pks = list(queryset.values_list("pk", flat=True))
        vectorize_researchers.apply_async((researchers_pks,))
        total = len(researchers_pks)

        logger.info(
            "Run command `vectorize` for %s researcher(s) (admin=%s)",
            total,
            request.user.pk,
        )

        messages.add_message(
            request,
            messages.INFO,
            f"Vecotrize Task created for {total} researcher(s)",
        )

    @admin.action(description="re-generate researcher description from ia")
    def generate_description_ia(self, request, queryset):
        total = queryset.count()
        all_taks = group(update_researcher_bio_ia.s(r.pk) for r in queryset)
        all_taks.apply_async()

        logger.info(
            "Run command `generate_description_ia` for %s researcher(s) (admin=%s)",
            total,
            request.user.pk,
        )

        messages.add_message(
            request,
            messages.INFO,
            f"Launched IA description regeneration for {total} researcher(s)",
        )

    @admin.action(description="assign researcher on projects")
    def assign_user(self, request, queryset):
        """Assign research to user if matching user/eppn"""
        researcher_updated = []
        assigned = notfound = 0

        for research in queryset.prefetch_related("identifiers").select_related("user"):
            # already set
            if research.user:
                continue

            for identifier in research.identifiers.all():
                if identifier.harvester != ResearcherIdentifier.Harvester.EPPN.value:
                    continue

                user = None
                email = identifier.value
                with suppress(ProjectUser.DoesNotExist):
                    user = ProjectUser.objects.get(email=email)

                if not user:
                    continue

                logger.info(
                    "Run command `assign_user` for %s researcher (admin=%s)",
                    user,
                    request.user.pk,
                )

                research.user = user
                researcher_updated.append(research)
                assigned += 1
                break
            else:
                notfound += 1

        Researcher.objects.bulk_update(researcher_updated, fields=["user"])
        # new users are now members of their structures groups
        for structure in with_ancestors(
            Structure.objects.filter(researchers__in=researcher_updated).distinct()
        ):
            sync_group_members(structure)

        if assigned:
            messages.add_message(request, messages.INFO, f"Assign {assigned} user.")
        if notfound:
            messages.add_message(
                request,
                messages.ERROR,
                f"Can't found {notfound} user with eppn.",
            )

    @admin.display(description="documents count")
    def get_documents(self, instance):
        return instance.modules.documents().count()

    @admin.display(description="citations count")
    def get_citations(self, instance):
        return instance.modules.citations().count()

    @admin.display(description="user")
    def get_user(self, obj):
        # add user link to admin
        if obj.user:
            url = reverse("admin:accounts_projectuser_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, str(obj.user))
        return None


@admin.register(Funding)
class FundingAdmin(admin.ModelAdmin):
    list_display = ("pk", "name", "get_project", "get_researchers")
    search_fields = (
        "name",
        "description",
        "project__name",
        "project__description",
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return (
            super()
            .get_queryset(request)
            .select_related("project")
            .annotate(annotate_researchers=Count("researchers"))
        )

    @admin.display(
        description="numbers of researchers", ordering="annotate_researchers"
    )
    def get_researchers(self, instance):
        return instance.annotate_researchers

    @admin.display(description="project")
    def get_project(self, obj):
        # add user link to admin
        if obj.project:
            url = reverse("admin:projects_project_change", args=[obj.project.id])
            return format_html('<a href="{}">{}</a>', url, str(obj.project.name))
        return None


class StructureRelationAdminInline(admin.TabularInline):
    model = StructureRelation
    fk_name = "structure"
    extra = 0
    autocomplete_fields = ("related_structure",)


class ResearcherStructureAdminInline(admin.TabularInline):
    model = ResearcherStructure
    extra = 0
    autocomplete_fields = ("researcher",)


@admin.register(Structure)
class StructureAdmin(TranslateObjectAdminMixin, IdentifierAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "acronym",
        "generic_type",
        "national_type",
        "organization",
        "get_researchers",
        "get_identifiers",
    )
    list_filter = ("generic_type", "organization")
    search_fields = (
        "name",
        "acronym",
        "identifiers__value",
    )
    autocomplete_fields = ("organization", "people_group")
    inlines = (
        identifiers_inline(StructureIdentifier),
        StructureRelationAdminInline,
        ResearcherStructureAdminInline,
    )
    actions = ("sync_groups",)

    @admin.action(description="sync people groups (creation, parents and members)")
    def sync_groups(self, request, queryset):
        sync_structures(queryset.select_related("organization", "people_group"))
        messages.add_message(
            request, messages.INFO, f"{queryset.count()} structures synced."
        )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("organization")
            .prefetch_related("identifiers")
            .annotate(identifiers_count=Count("identifiers", distinct=True))
            .annotate(researchers_count=Count("researchers", distinct=True))
        )

    @admin.display(description="researchers count", ordering="researchers_count")
    def get_researchers(self, instance):
        return instance.researchers_count


@admin.register(AuthorityOrganization)
class AuthorityOrganizationAdmin(IdentifierAdminMixin, admin.ModelAdmin):
    list_display = ("name", "type", "get_identifiers")
    list_filter = ("type",)
    search_fields = ("name", "identifiers__value")
    inlines = (identifiers_inline(AuthorityOrganizationIdentifier),)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("identifiers")
            .annotate(identifiers_count=Count("identifiers", distinct=True))
        )


@admin.register(CrisalidConfig)
class CrisalidConfigAdmin(admin.ModelAdmin):
    list_display = ("pk", "get_organization", "active")
    search_fields = ("organization__code", "active")
    autocomplete_fields = ("organization", "structures_groups_root")
    actions = ("active_connections", "deactive_connections")

    @admin.action(description="run/reload crisalidbus connections")
    def active_connections(self, request, queryset):
        """method to change/run crisalidbus listener"""
        # we don't update directly queryset for signals dispatch
        total = queryset.count()
        for obj in queryset:
            logger.info(
                "CrisalidBus listener (%r) started or reloaded (admin=%s).",
                obj,
                request.user,
            )
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
            logger.info(
                "CrisalidBus listener (%r) stoped (admin=%s).",
                obj,
                request.user,
            )
            obj.active = False
            obj.save()

        messages.add_message(
            request, messages.INFO, f"CrisalidBus listener stoped ({total})."
        )

    @admin.display(description="organization")
    def get_organization(self, obj):
        url = reverse(
            "admin:organizations_organization_change",
            args=[obj.organization.id],
        )
        return format_html('<a href="{}">{}</a>', url, str(obj.organization))


class CrisalidApolloImporterForm(forms.Form):
    config = forms.ModelChoiceField(
        queryset=CrisalidConfig.objects.all(), required=True
    )
    file = forms.FileField(
        required=True,
        label="apollo files",
        widget=AdminFileWidget(),
    )

    def clean_file(self):
        """check if file is a valid json"""
        data = self.cleaned_data
        content = data["file"].read()
        try:
            return json.loads(content)
        except (TypeError, ValueError) as e:
            raise ValidationError("Invalid json files") from e


class CrisalidApolloImporter(ExtraAdminMixins, TemplateView):
    template_name = "importer.html"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx["form"] = CrisalidApolloImporterForm()
        return ctx

    def post(self, request, **kw):
        """check form and run celery task to import json/apollo result files"""
        context = self.get_context_data()

        form = CrisalidApolloImporterForm(request.POST, request.FILES)
        context["form"] = form

        if not form.is_valid():
            messages.add_message(request, messages.ERROR, "Error in forms")
            return render(request, self.template_name, context)

        config_pk = form.cleaned_data["config"].pk
        content = form.cleaned_data["file"]
        load_apollo_data.apply_async((config_pk, content))

        messages.add_message(request, messages.SUCCESS, "taks are sended")
        return render(request, self.template_name, context)


admin.site.register_extras(
    "Crisalid",
    "Apollo importer",
    CrisalidApolloImporter,
    permissions={"superuser": True},
)
