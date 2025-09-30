
from django import forms
from django.contrib import admin
from django.db import models
from .models import Researcher, Identifier, Document, DocumentSource

class IdentifierInline(admin.StackedInline):
    model = Identifier

class ResearcherInline(admin.StackedInline):
    model = Researcher

class DocumentSourceInline(admin.StackedInline):
    model = DocumentSource

class IdentifierAdmin(admin.ModelAdmin):
    list_display = (
        "harvester", "value"
    )


class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "publication_date",
        "get_authors"
    )
    queryset = Document.objects.prefetch_related("authors", "sources")
    inlines = (DocumentSourceInline,)

    @admin.display(description="authors count")
    def get_authors(self, instance):
        return instance.authors.count()

class ResearcherAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "display_name",
        "get_publications"
    )
    queryset = Researcher.objects.prefetch_related("identifiers", "documents").select_related("user")

    @admin.display(description="publication count")
    def get_publications(self, instance):
        return instance.documents.count()

admin.site.register(Researcher, ResearcherAdmin)
admin.site.register(Identifier, IdentifierAdmin)
admin.site.register(Document, DocumentAdmin)
