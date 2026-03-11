import json
from contextlib import suppress

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.widgets import AdminFileWidget
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.shortcuts import render
from django.views.generic import TemplateView

from apps.accounts.models import ProjectUser
from apps.commons.admin import ExtraAdminMixins, TranslateObjectAdminMixin
from services.crisalid.tasks import load_apollo_data, vectorize_documents

from .models import (
    CrisalidConfig,
    Document,
    DocumentContributor,
    Identifier,
    Researcher,
)


class IdentifierAdminMixin:
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
            .annotate(documents_count=Count("documents", distinct=True))
            .annotate(researchers_count=Count("researchers", distinct=True))
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
class DocumentAdmin(TranslateObjectAdminMixin, IdentifierAdminMixin, admin.ModelAdmin):
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
            .annotate(identifiers_count=Count("identifiers", distinct=True))
            .annotate(contributors_count=Count("contributors", distinct=True))
        )

    @admin.display(description="contributors count", ordering="contributors_count")
    def get_contributors(self, instance):
        return instance.contributors.count()


@admin.register(Researcher)
class ResearcherAdmin(IdentifierAdminMixin, admin.ModelAdmin):
    list_display = (
        "given_name",
        "family_name",
        "user",
        "get_documents",
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
            .annotate(identifiers_count=Count("identifiers", distinct=True))
            .annotate(documents_count=Count("documents", distinct=True))
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
                if identifier.harvester != Identifier.Harvester.EPPN.value:
                    continue

                user = None
                email = identifier.value
                with suppress(ProjectUser.DoesNotExist):
                    user = ProjectUser.objects.get(email=email)

                if not user:
                    continue

                research.user = user
                researcher_updated.append(research)
                assigned += 1
                break
            else:
                notfound += 1

        Researcher.objects.bulk_update(researcher_updated, fields=["user"])

        if assigned:
            messages.add_message(request, messages.INFO, f"Assign {assigned} user.")
        if notfound:
            messages.add_message(
                request,
                messages.ERROR,
                f"Can't found {notfound} user with eppn.",
            )

    @admin.display(description="documents count", ordering="documents_count")
    def get_documents(self, instance):
        return instance.documents_count


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
            request, messages.INFO, f"CrisalidBus listener stoped ({total})."
        )


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
        except (TypeError, ValueError):
            raise ValidationError("Invalid json files")


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
