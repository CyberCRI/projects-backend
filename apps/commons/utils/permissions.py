import itertools
from typing import Optional


def get_permissions_from_subscopes(subscopes):
    permissions = (
        (
            ("view_" + subscope[0], "Can view " + subscope[1]),
            ("add_" + subscope[0], "Can add " + subscope[1]),
            ("change_" + subscope[0], "Can change " + subscope[1]),
            ("delete_" + subscope[0], "Can delete " + subscope[1]),
        )
        for subscope in subscopes
    )
    return tuple(itertools.chain.from_iterable(permissions))


def get_write_permissions_from_subscopes(subscopes):
    permissions = (
        (
            ("add_" + subscope[0], "Can add " + subscope[1]),
            ("change_" + subscope[0], "Can change " + subscope[1]),
            ("delete_" + subscope[0], "Can delete " + subscope[1]),
        )
        for subscope in subscopes
    )
    return tuple(itertools.chain.from_iterable(permissions))


def map_action_to_permission(action: str, codename: str) -> Optional[str]:
    return {
        "list": f"view_{codename}",
        "retrieve": f"view_{codename}",
        "create": f"add_{codename}",
        "update": f"change_{codename}",
        "partial_update": f"change_{codename}",
        "destroy": f"delete_{codename}",
    }.get(action, None)
