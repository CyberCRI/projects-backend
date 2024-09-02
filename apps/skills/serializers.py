from rest_framework import serializers


class MentorshipContactSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    content = serializers.CharField()
    reply_to = serializers.EmailField()
