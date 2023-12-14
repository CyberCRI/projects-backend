from rest_framework import serializers


class EmailAvailableSerializer(serializers.Serializer):
    available = serializers.BooleanField()
