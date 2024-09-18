from rest_framework.routers import DefaultRouter

from .views import EscoOccupationViewSet, EscoSkillViewSet

router = DefaultRouter()

router.register(
    r"esco-skill",
    EscoSkillViewSet,
    basename="EscoSkill",
)

router.register(
    r"esco-occupation",
    EscoOccupationViewSet,
    basename="EscoOccupation",
)
