from typing import Any, Dict, Tuple, TypeVar

import pymupdf
from rest_framework import serializers
from rest_framework.utils import model_meta

from apps.commons.utils import extract_pdf_data
from apps.organizations.models import Organization
from services.mistral.interface import MistralService

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
    except Exception:  # noqa: PIE786
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


def create_project_from_pdf(pdf_data: pymupdf.Document) -> Project:
    """Create a Project instance from a PDF file.

    Parameters
    ----------
    pdf_data : pymupdf.Document
        The PDF file to be converted into a Project instance.

    Returns
    -------
    Project
        The Project instance created from the PDF file.
    """
    text, images = extract_pdf_data(pdf_data)
    system = [
        "CONTEXT : Our user provides a PDF file with the following extracted text.",
        "OBJECTIVE : We want to turn that text into a project's description.",
        "STYLE: Similar to the one used in the original text.",
        "LANGUAGE: Same as the original text.",
        "AUDIENCE : People that don't know the project and will want to learn about it.",
        """
        RESPONSE : A json object with the following keys:
            - title (str): The title of the project.
            - description (str): The description of the project.
        """,
        "IMPORTANT : DO NOT MAKE UP ANY FACTS, EVEN IF IT MEANS RETURNING VERY LITTLE INFORMATION.",
    ]
    prompt = [text]
    return MistralService.get_json_chat_response(system=system, prompt=prompt)
