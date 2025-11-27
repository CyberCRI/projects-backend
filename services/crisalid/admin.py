from django.contrib import admin
from django.db.models import Count

from apps.accounts.models import ProjectUser

from .models import Document, DocumentContributor, Identifier, Researcher


class IdentifierAdmin(admin.ModelAdmin):
    list_display = ("harvester", "value", "get_researcher", "get_documents")
    search_fields = ("harvester", "value")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("researchers", "documents")
            .annotate(documents_count=Count("documents__id"))
            .annotate(researchers_count=Count("researchers__id"))
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


class DocumentAdmin(admin.ModelAdmin):
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
        "contributors__display_name",
        "identifiers__value",
        "identifiers__harvester",
    )
    inlines = (DocumentContributorAdminInline,)

    actions = ["vectorize"]

    def vectorize(self, request, queryset):
        for document in queryset:
            document.vectorize()

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("contributors", "identifiers")
            .annotate(identifiers_count=Count("identifiers__id"))
            .annotate(contributors_count=Count("contributors__id"))
        )

    @admin.display(description="contributors count", ordering="contributors_count")
    def get_contributors(self, instance):
        return instance.contributors.count()

    @admin.display(description="identifiers count", ordering="identifiers_count")
    def get_identifiers(self, instance):
        # list all harvester name from this profile
        result = [o.harvester for o in instance.identifiers.all()]
        if not result:
            return None
        return f"{', '.join(result)} ({len(result)})"


class ResearcherAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "user",
        "get_documents",
        "get_identifiers",
    )
    search_fields = (
        "display_name",
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
            .annotate(documents_count=Count("documents__id"))
        )

    @admin.action(description="assign researcher on projects")
    def assign_user(self, request, queryset):
        """Assign research to user if matching user/eppn"""
        researcher_updated = []

        for research in queryset.prefetch_related("identifiers").select_related("user"):
            # already set
            if research.user:
                continue

            for identifier in research.identifiers.all():
                if identifier.harvester != Identifier.Harvester.EPPN.value:
                    continue

                user = ProjectUser.objects.filter(email=identifier.value)
                if not user:
                    # TODO(remi): create 2 field in models researcher ?
                    given_name, family_name = "", ""
                    splitter = research.display_name.split(" ", 1)
                    if len(splitter) >= 1:
                        given_name = splitter[0]
                    if len(splitter) >= 2:
                        given_name = " ".join(splitter[1:])

                    user = ProjectUser(
                        email=identifier.value,
                        given_name=given_name,
                        family_name=family_name,
                    )
                    user.save()

                research.user = user
                researcher_updated.append(research)

        Researcher.objects.bulk_update(researcher_updated, fields=["user"])

    @admin.display(description="documents count", ordering="documents_count")
    def get_documents(self, instance):
        return instance.documents_count

    @admin.display(description="identifiers count", ordering="identifiers_count")
    def get_identifiers(self, instance):
        # list all harvester name from this profile
        result = [o.harvester for o in instance.identifiers.all()]
        if not result:
            return None

        return f"{', '.join(result)} ({len(result)})"


admin.site.register(Researcher, ResearcherAdmin)
admin.site.register(Identifier, IdentifierAdmin)
admin.site.register(Document, DocumentAdmin)
