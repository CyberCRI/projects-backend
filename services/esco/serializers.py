from apps.commons.serializers import TranslatedModelSerializer

from .models import EscoTag


class EscoTagLightSerializer(TranslatedModelSerializer):
    class Meta:
        model = EscoTag
        fields = ["id", "title", "description"]


class EscoTagSerializer(TranslatedModelSerializer):
    parents = EscoTagLightSerializer(many=True, read_only=True)
    children = EscoTagLightSerializer(many=True, read_only=True)
    essential_skills = EscoTagLightSerializer(many=True, read_only=True)
    optional_skills = EscoTagLightSerializer(many=True, read_only=True)

    class Meta:
        model = EscoTag
        fields = [
            "id",
            "title",
            "description",
            "parents",
            "children",
            "essential_skills",
            "optional_skills",
        ]
