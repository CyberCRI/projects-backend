from django.contrib import admin

from .models import Document, DocumentSource, Identifier, Researcher


class IdentifierInline(admin.StackedInline):
    model = Identifier


class ResearcherInline(admin.StackedInline):
    model = Researcher


class DocumentSourceInline(admin.StackedInline):
    model = DocumentSource


class IdentifierAdmin(admin.ModelAdmin):
    list_display = ("harvester", "value", "get_researcher", "get_documents")

    def get_queryset(self, request):
        return (
            super().get_queryset(request).prefetch_related("researchers", "documents")
        )

    @admin.display(description="researchers assosiate")
    def get_researcher(self, instance):
        return instance.researchers.count()

    @admin.display(description="documents assosiate")
    def get_documents(self, instance):
        return instance.documents.count()


class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "publication_date", "get_authors", "get_identifiers")
    inlines = (DocumentSourceInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("authors", "sources")

    @admin.display(description="authors count")
    def get_authors(self, instance):
        return instance.authors.count()

    @admin.display(description="identifiers count")
    def get_identifiers(self, instance):
        # list all harvester name from this profile
        result = [iden.identifier.harvester for iden in instance.sources.all()]

        return f"{', '.join(result)} ({len(result)})"


class ResearcherAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "get_publications", "get_identifiers")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user")
            .prefetch_related("identifiers", "documents")
        )

    @admin.display(description="publication count")
    def get_publications(self, instance):
        return instance.documents.count()

    @admin.display(description="identifiers count")
    def get_identifiers(self, instance):
        # list all harvester name from this profile
        result = [iden.harvester for iden in instance.identifiers.all()]

        return f"{', '.join(result)} ({len(result)})"


admin.site.register(Researcher, ResearcherAdmin)
admin.site.register(Identifier, IdentifierAdmin)
admin.site.register(Document, DocumentAdmin)
