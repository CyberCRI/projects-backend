from typing import List

from apps.organizations.models import Organization


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
