from django.contrib import admin
from django.db.models import Count

from .models import Identifier, Publication, Researcher


class IdentifierAdmin(admin.ModelAdmin):
    list_display = ("harvester", "value", "get_researcher", "get_publications")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("researchers", "publications")
            .annotate(publications_count=Count("publications__id"))
            .annotate(researchers_count=Count("researchers__id"))
        )

    @admin.display(description="researchers assosiate", ordering="researchers_count")
    def get_researcher(self, instance):
        return instance.researchers_count

    @admin.display(description="publications assosiate", ordering="publications_count")
    def get_publications(self, instance):
        return instance.publications_count


class PublicationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "publication_date",
        "publication_type",
        "get_contributors",
        "get_identifiers",
    )
    search_fields = (
        "title",
        "publication_date",
        "publication_type",
        "contributors__display_name",
        "identifiers__value",
        "identifier__harvester",
    )

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
        "get_publications",
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
            .prefetch_related("identifiers", "publications")
            .annotate(identifiers_count=Count("identifiers__id"))
            .annotate(publications_count=Count("publications__id"))
        )

    @admin.display(description="publication count", ordering="publications_count")
    def get_publications(self, instance):
        return instance.publications_count

    @admin.display(description="identifiers count", ordering="identifiers_count")
    def get_identifiers(self, instance):
        # list all harvester name from this profile
        result = [o.harvester for o in instance.identifiers.all()]
        if not result:
            return None

        return f"{', '.join(result)} ({len(result)})"


admin.site.register(Researcher, ResearcherAdmin)
admin.site.register(Identifier, IdentifierAdmin)
admin.site.register(Publication, PublicationAdmin)
