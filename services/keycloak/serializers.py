from rest_framework import serializers

from apps.files.serializers import ImageSerializer

from .models import IdentityProvider


class IdentityProviderSerializer(serializers.ModelSerializer):
    logo = ImageSerializer(read_only=True)

    class Meta:
        model = IdentityProvider
        fields = (
            "id",
            "alias",
            "logo",
            "enabled",
        )
