from django_filters import rest_framework as filters

from .models import Tag, WikipediaTag


class WikipediaTagFilter(filters.FilterSet):
    # filter by project id with query ?project=X
    project = filters.CharFilter(field_name="project__id")
    # filter by  organization code with query ?organization=X
    organization = filters.CharFilter(field_name="organization__code")
    # filter by  project category id with query ?project_category=X
    project_category = filters.CharFilter(field_name="project_category__id")
    # filter by  wikipedia qid with query ?wikipedia_qid=X
    wikipedia_qid = filters.CharFilter(field_name="wikipedia_qid")

    class Meta:
        model = WikipediaTag
        fields = ["project", "organization", "project_category", "wikipedia_qid"]


class TagFilter(filters.FilterSet):
    # filter by project id with query ?project=X
    project = filters.CharFilter(field_name="project__id")
    # filter by  organization code with query ?organization=X
    organization = filters.CharFilter(field_name="organization__code")
    # filter by  project category id with query ?project_category=X
    project_category = filters.CharFilter(field_name="project_category__id")

    class Meta:
        model = Tag
        fields = ["project", "organization", "project_category"]
