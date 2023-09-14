from typing import List

from apps.organizations.models import Organization


def get_hierarchy_codes(codes: List[str]) -> List:
    hierarchy_codes = []
    while len(codes) > 0:
        hierarchy_codes += codes
        codes = (
            Organization.objects.values("code")
            .filter(parent__code__in=codes)
            .values_list("code", flat=True)
        )
    return hierarchy_codes
