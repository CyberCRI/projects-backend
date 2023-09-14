from rest_framework_nested.routers import DefaultRouter

from .views import (
    MultipleSearchViewSet,
    PeopleGroupSearchViewSet,
    ProjectSearchViewSet,
    UserSearchViewSet,
)

router = DefaultRouter()

router.register(
    r"search/user",
    UserSearchViewSet,
    basename="UserSearch",
)
router.register(
    r"search/people-group",
    PeopleGroupSearchViewSet,
    basename="PeopleGroupSearch",
)
router.register(
    r"search/project",
    ProjectSearchViewSet,
    basename="ProjectSearch",
)
router.register(
    r"search/global",
    MultipleSearchViewSet,
    basename="GlobalSearch",
)
