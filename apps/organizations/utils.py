from typing import List

from apps.organizations.models import Organization, ProjectCategory


def get_below_hierarchy_codes(codes: List[str]) -> List[str]:
    """
    Get all the codes of the organizations below in the hierarchy of the given codes
    """
    hierarchy_codes = []
    while len(codes) > 0:
        hierarchy_codes += codes
        codes = (
            Organization.objects.values("code")
            .filter(parent__code__in=codes)
            .values_list("code", flat=True)
        )
    return hierarchy_codes


def get_above_hierarchy_codes(codes: List[str]) -> List[str]:
    """
    Get all the codes of the organizations above in the hierarchy of the given codes
    """
    hierarchy_codes = []
    while len(codes) > 0:
        hierarchy_codes += codes
        visible_on_parent_dashboard = Organization.objects.filter(
            code__in=codes, is_logo_visible_on_parent_dashboard=True
        )
        codes = Organization.objects.filter(
            children__in=visible_on_parent_dashboard
        ).values_list("code", flat=True)
    return hierarchy_codes


def get_below_categories_hierarchy_ids(ids: List[int]) -> List[int]:
    """
    Get all the ids of the categories below in the hierarchy of the given ids
    """
    hierarchy_ids = []
    while len(ids) > 0:
        hierarchy_ids += ids
        ids = (
            ProjectCategory.objects.values("id")
            .filter(parent__id__in=ids)
            .values_list("id", flat=True)
        )
    return hierarchy_ids


def get_above_categories_hierarchy_ids(ids: List[int]) -> List[int]:
    """
    Get all the ids of the categories above in the hierarchy of the given ids
    """
    hierarchy_ids = []
    while len(ids) > 0:
        hierarchy_ids += ids
        ids = ProjectCategory.objects.filter(children__id__in=ids).values_list(
            "id", flat=True
        )
    return hierarchy_ids
