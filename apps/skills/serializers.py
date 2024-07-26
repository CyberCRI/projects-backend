from rest_framework import serializers

from apps.accounts.models import ProjectUser
from apps.commons.serializers import TranslatedModelSerializer
from apps.misc.models import WikipediaTag


class WikipediaTagMentorshipSerializer(TranslatedModelSerializer):
    mentors_count = serializers.IntegerField(required=False, read_only=True)
    mentorees_count = serializers.IntegerField(required=False, read_only=True)

    class Meta:
        model = WikipediaTag
        fields = [
            "id",
            "name",
            "wikipedia_qid",
            "description",
            "mentorees_count",
            "mentors_count",
        ]
        lookup_field = "wikipedia_qid"


class UserMentorshipSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProjectUser
        fields = []
