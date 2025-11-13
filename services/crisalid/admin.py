from django.contrib import admin
from django.db.models import Count

from .models import Document, Identifier, Researcher


class IdentifierAdmin(admin.ModelAdmin):
    list_display = ("harvester", "value", "get_researcher", "get_documents")

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
        "identifier__harvester",
    )

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
        "identifier__harvester",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user")
            .prefetch_related("identifiers", "documents")
            .annotate(identifiers_count=Count("identifiers__id"))
            .annotate(documents_count=Count("documents__id"))
        )

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
