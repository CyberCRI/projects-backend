from typing import List, Optional

from algoliasearch.recommend_client import RecommendClient
from django.conf import settings
from django.core.cache import cache
from django.db.models import CharField, F
from pyparsing import Union

from apps.accounts.models import AnonymousUser, ProjectUser
from apps.commons.db.functions import ArrayPosition
from apps.organizations.utils import get_hierarchy_codes
from apps.projects.models import Project


class AlgoliaRecommendService:
    """
    Interface to Algolia Recommend API.

    See https://www.algolia.com/doc/api-client/methods/recommend/
    """

    client = RecommendClient.create(
        settings.ALGOLIA["APPLICATION_ID"], settings.ALGOLIA["API_KEY"]
    )
    project_index = f"{settings.ALGOLIA['INDEX_PREFIX']}_project_"

    @classmethod
    def get_user_projects_permissions(cls, user: Union[ProjectUser, AnonymousUser]):
        public_permission = ["projects.view_public_project"]
        user_permissions = list(
            filter(
                lambda x: any(
                    x.startswith(s)
                    for s in [
                        "projects.view_project",
                        "organizations.view_project",
                        "organizations.view_org_project",
                    ]
                ),
                user.get_permissions_representations(),
            )
        )
        return [p.replace(":", "-") for p in public_permission + user_permissions]

    @classmethod
    def _get_similar_projects(cls, project, organizations_codes, limit, user):
        organizations = get_hierarchy_codes(organizations_codes)
        return cls.client.get_related_products(
            [
                {
                    "indexName": cls.project_index,
                    "objectID": project.id,
                    "maxRecommendations": limit,
                    "queryParameters": {
                        "facetFilters": [
                            [f"organizations:{o}" for o in organizations],
                            [
                                f"permissions:{p}"
                                for p in cls.get_user_projects_permissions(user)
                            ],
                        ]
                    },
                },
            ]
        )

    @classmethod
    def get_cached_similar_projects(cls, project, organizations_codes, limit, user):
        if settings.ENABLE_CACHE:
            key = f"{project.id}.{organizations_codes}.{limit}.{str(user.id)}"
            key = f"algolia_recommend.{key}"
            if key in cache.keys("*"):  # noqa: SIM118
                return cache.get(key)
            response = cls._get_similar_projects(
                project, organizations_codes, limit, user
            )
            cache.set(key, response, settings.CACHE_ALGOLIA_RECOMMEND_TTL)
            return response
        return cls._get_similar_projects(project, organizations_codes, limit, user)

    @classmethod
    def get_similar_projects(
        cls,
        project: Project,
        organizations_codes: List[str],
        limit: int,
        user: Optional[ProjectUser] = None,
    ):
        user = user or AnonymousUser()
        related_projects = cls.get_cached_similar_projects(
            project, organizations_codes, limit, user
        )
        hits = related_projects["results"][0]["hits"]
        return (
            user.get_project_queryset()
            .filter(id__in=[p["id"] for p in hits])
            .annotate(
                rank=ArrayPosition(
                    [p["id"] for p in hits],
                    F("id"),
                    base_field=CharField(max_length=8),
                )
            )
            .order_by("rank")
        )
