from rest_framework import serializers


class WikibaseItemSerializer(serializers.Serializer):
    wikipedia_qid = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
