import bisect
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

from django.db.models import CharField, F, QuerySet
from django.utils.timezone import utc

from apps.commons.db.functions import ArrayPosition
from apps.organizations.models import Organization

from .models import Project


def projects_views(
    queryset: "QuerySet[Project]", organizations: Optional[List[Organization]] = None
) -> Dict[str, int]:
    """Retrieve the views of project within `queryset`.
    Views is computed differently according to `organization`:
        * If `organizations` is falsy, use the global views of the projects.
        * If only one organization was given, use the views inside that
          organization.
        * If multiple organization were given, use the maximum view count
          of that project between all these organizations.
    Parameters
    ----------
    queryset: QuerySet[Project]
        A queryset of Project.
    organizations: List[Organization], optional
        An optional list of organizations.
    Returns
    -------
    Dict[str, int]
        A dictionary mapping each project's id to their views. The view count
        can be `-1` if it could not be retrieved or an error occurred.
    """
    if not organizations:
        views = Project.get_queryset_total_views(queryset)
    elif len(organizations) == 1:
        views = Project.get_queryset_organization_views(queryset, organizations[0])
    else:
        views = defaultdict(int)
        for organization in organizations:
            for project, v in Project.get_queryset_organization_views(
                queryset, organization
            ).items():
                views[project] = max(v, views[project])
    return views


def popularity(value: Dict[str, Union[int, str]], views: int) -> float:
    """Compute the popularity of a project.

    popularity = `(C + F + V + Cr) / 4`
        * `C`  - Root comment count.
        * `F`  - Follower count.
        * `V`  - Views count.
        * `Cr` - Replies count.
    """
    for key, val in value.items():
        value[key] = val if val else 0
    return (
        value["stat__comments"]
        + value["stat__follows"]
        + views
        + value["stat__replies"]
    ) / 4


def completeness(value: Dict[str, Union[int, str]]) -> float:
    """Compute the completeness of a project.

    completeness = `(R + B + D + O) / 4`
        * `R` - Resource count.
        * `B` - Blog entry count.
        * `D` - Size of the description.
        * `O` - Objectives count.
    """
    for key, val in value.items():
        value[key] = val if val else 0
    keys = [
        "stat__links",
        "stat__files",
        "stat__blog_entries",
        "stat__description_length",
        "stat__goals",
    ]
    return sum(value[key] for key in value.keys() if key in keys) / 5


def activity(value: Dict[str, Union[int, str]]) -> float:
    """Compute the activity of the project.

    activity = A / (1 + Ad)
        * `Ad` - Day count between the last update of the project and the current time.
        * `A`  - Update count.
    """
    now = datetime.utcnow().replace(tzinfo=utc)
    last_update = value["stat__last_update"] if value["stat__last_update"] else now
    return value["stat__versions"] / (1 + (now - last_update).days)


def compute_score(value: Dict[str, Union[int, str]], views: int) -> float:
    """Compute the score of a project.

    score = `(popularity + completeness + activity) / 3`
    """
    return (popularity(value, views) + completeness(value) + activity(value)) / 3


def top_project(
    queryset: "QuerySet[Project]", organizations: Optional[List[Organization]] = None
) -> Tuple["QuerySet[Project]", Dict[str, float]]:
    """Compute a queryset of the top projects.

    Returns
    -------
    Tuple['QuerySet[Project]', Dict[str, float]]
        Return the queryset ordered by score and a dict mapping project's id
        to their score.
    """
    values = queryset.values(
        "pk",
        "stat__comments",
        "stat__replies",
        "stat__follows",
        "stat__links",
        "stat__files",
        "stat__blog_entries",
        "stat__description_length",
        "stat__goals",
        "stat__versions",
        "stat__last_update",
    )

    # Create a sorted list of the top projects' PK.
    scores = []
    views = projects_views(queryset, organizations)
    for value in values:
        score = compute_score(value, views[value["pk"]])
        bisect.insort(scores, (score, value["pk"]))
    top = [t[1] for t in reversed(scores)]

    # Return a queryset of Project sorted with `top`.
    ordering = ArrayPosition(top, F("pk"), base_field=CharField(max_length=8))

    qs = queryset.annotate(ordering=ordering).order_by("ordering")
    scores_map = dict(map(lambda x: (x[1], round(x[0], 4)), scores))
    return qs, scores_map
