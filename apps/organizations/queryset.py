from typing import TYPE_CHECKING

from django.db.models import Exists, OuterRef, Subquery, Value
from django.db.models.functions import JSONObject

from apps.commons.queryset import MultipleIdsQuerySet

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser


class ProjectCategoryQuerySet(MultipleIdsQuerySet):
    def annotate_follow(self, user: "ProjectUser"):
        """annotate follow informations from user"""

        from apps.organizations.models import CategoryFollow

        if user.is_anonymous:
            return self.annotate(
                annotate_follow=JSONObject(
                    is_followed=Value(False), follow_id=Value(None)
                )
            )

        follow = CategoryFollow.objects.filter(
            category=OuterRef("pk"),
            follower=user,
        )

        return self.annotate(
            annotate_follow=JSONObject(
                is_followed=Exists(follow),
                follow_id=Subquery(follow.values("id")[:1]),
            )
        )
