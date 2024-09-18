from apps.commons.serializers import TranslatedModelSerializer

from .models import EscoOccupation, EscoSkill


class EscoSkillLightSerializer(TranslatedModelSerializer):
    class Meta:
        model = EscoSkill
        fields = ["id", "title", "description"]


class EscoSkillSerializer(TranslatedModelSerializer):
    parents = EscoSkillLightSerializer(many=True, read_only=True)
    children = EscoSkillLightSerializer(many=True, read_only=True)
    essential_skills = EscoSkillLightSerializer(many=True, read_only=True)
    optional_skills = EscoSkillLightSerializer(many=True, read_only=True)

    class Meta:
        model = EscoSkill
        fields = [
            "id",
            "title",
            "description",
            "parents",
            "children",
            "essential_skills",
            "optional_skills",
        ]


class EscoOccupationLightSerializer(TranslatedModelSerializer):
    class Meta:
        model = EscoOccupation
        fields = ["id", "title", "description"]


class EscoOccupationSerializer(TranslatedModelSerializer):
    parents = EscoOccupationLightSerializer(many=True, read_only=True)
    children = EscoOccupationLightSerializer(many=True, read_only=True)
    essential_skills = EscoSkillLightSerializer(many=True, read_only=True)
    optional_skills = EscoSkillLightSerializer(many=True, read_only=True)

    class Meta:
        model = EscoOccupation
        fields = [
            "id",
            "title",
            "description",
            "parents",
            "children",
            "essential_skills",
            "optional_skills",
        ]
