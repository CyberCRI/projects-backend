from typing import List

from apps.organizations.models import Organization


def get_below_hierarchy_codes(codes: List[str]) -> List:
    """
    Get all the codes of the organizations below in the hierarchy of the given codes
    """
    hierarchy_codes = []
    while len(codes) > 0:
        hierarchy_codes += codes
        codes = (
            Organization.objects.values("code")
            .filter(parent__code__in=codes, is_logo_visible_on_parent_dashboard=True)
            .values_list("code", flat=True)
        )
    return hierarchy_codes


def get_above_hierarchy_codes(organization: Organization) -> List[Organization]:
    """
    Get all the codes of the organizations above in the hierarchy of the given codes
    """
    parents_codes = [organization]
    while organization.parent and organization.is_logo_visible_on_parent_dashboard:
        organization = organization.parent
        parents_codes.append(organization)
    return parents_codes
