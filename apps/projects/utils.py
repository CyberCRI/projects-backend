from collections import defaultdict
from collections.abc import Iterable
from typing import Any, TypeVar

from django.db.models import CharField, QuerySet, Value
from django.db.models.functions import Cast
from rest_framework import serializers
from rest_framework.utils import model_meta

from apps.organizations.models import Organization, Template, TemplateTab
from services.translator.serializers import prefix_fields_langs

from .models import Project, ProjectTab

T = TypeVar("T")


def get_views_from_serializer(
    serializer: serializers.Serializer, project: Project
) -> int:
    """Retrieve the views of a Project within a serializer's method.

    If you want to only count the views of the organization within the request's
    filter, you should add the request to the serializer's context using
    view's `get_serializer_context`.
    """
    request = serializer.context.get("request")
    if request is None:
        return project.get_views()

    if "organization" in request.query_params:
        code = request.query_params["organization"]
    elif "organizations" in request.query_params:
        codes = request.query_params["organizations"].split(",")
        if len(codes) > 1:
            return project.get_views()
        code = codes[0]
    else:
        return project.get_views()

    try:
        return project.get_views_organizations([Organization.objects.get(code=code)])
    except Exception:
        return project.get_views()


def compute_project_changes(
    project: Project, new_data: dict[str, Any]
) -> dict[str, tuple[T, T]]:
    """Return the changes between `project` and `new_data`.

    Return
    ------
    Dict[str, Tuple[T, T]]
        A dictionary mapping the name of each attribute changed to a tuple
        containing old and new value.
    """
    changes = {}
    info = model_meta.get_field_info(project)
    for attr, value in new_data.items():
        if (
            not (attr in info.relations and info.relations[attr].to_many)
            and attr not in ("header_image")
            and (old := str(getattr(project, attr))) != (new := str(value))
        ):
            changes[attr] = (old, new)

    return changes


def annotate_queryset_location(*querysets: QuerySet) -> QuerySet:
    """annoate queryset for lazy load linked elements"""

    all_qs: QuerySet = None
    fields = (
        "id",
        "lat",
        "lng",
        "type",
        "content_id",
        "content_type",
        "title",
        "description",
        # add generate field text
        *prefix_fields_langs(("title", "description")),
    )

    for queryset in querysets:
        model = queryset.model
        content = model.get_related_content()
        qs = queryset.annotate(
            # cast linked object to string (project is slug so string, but news/events is pk so int)
            content_id=Cast(f"{content}_id", output_field=CharField()),
            content_type=Value(content),
        ).values(*fields)

        all_qs = qs if all_qs is None else all_qs.union(qs)

    return all_qs


def sync_project_tabs(projects: Iterable[Project], tabs: Iterable[TemplateTab]):
    """Update only projects/tabs (used in signal)"""

    all_uuids = [tab.uuid for tab in tabs]
    exists_tabs = defaultdict(set)

    for uuid, project_id in ProjectTab.objects.filter(
        uuid__in=all_uuids, project__in=projects
    ).values_list("uuid", "project"):
        exists_tabs[project_id].add(uuid)

    for project in projects:
        tabs_exists = exists_tabs[project.id]
        for tab in tabs:
            # tab already exists
            if tab.uuid in tabs_exists:
                continue

            # TODO: we use .save() to generate slug
            # we need to change that to use bulk_create, and generate slug in db
            tab = ProjectTab(
                uuid=tab.uuid,
                project=project,
                title=tab.title,
                description=tab.description,
                type=tab.type,
                icon=tab.icon,
                show_preview=tab.show_preview,
            )
            tab.save()


def sync_project_template():
    """Sync all projects tabs templates"""

    for template in Template.objects.prefetch_related("tabs").all():
        sync_project_tabs(
            Project.objects.filter(template=template), template.tabs.all()
        )
