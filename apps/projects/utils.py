from typing import Any, Dict, Tuple, TypeVar

from rest_framework import serializers
from rest_framework.utils import model_meta

from apps.organizations.models import Organization

from .models import Project

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
    except Exception:  # noqa
        return project.get_views()


def compute_project_changes(
    project: Project, new_data: Dict[str, Any]
) -> Dict[str, Tuple[T, T]]:
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
