from functools import cached_property

from django.http import QueryDict
from rest_framework import serializers


class ModulesSerializers(serializers.ModelSerializer):
    """Modules serializers to return how many elements is linked to objects"""

    modules = serializers.SerializerMethodField()

    @cached_property
    def __modules_keys(self):
        request = self.context.get("request")
        query = request.query_params if request else QueryDict()

        modules_keys = None
        # if modules is set queryparams , return list elements (for multiples modules)
        if "modules" in query:
            modules_keys = query.getlist("modules")
        # if modules is not set, get "default" values from Meta serializer
        if modules_keys is None:
            modules_keys = getattr(self.Meta, "modules_keys", None)

        if modules_keys is not None and "all" in modules_keys:
            modules_keys = self.Meta.model.get_related_module().modules_keys()

        return tuple(modules_keys) if modules_keys is not None else None

    def get_modules(self, instance):
        request = self.context.get("request")
        organization = self.context.get("organization")

        return instance.modules_by_user(request.user, organization=organization).count(
            self.__modules_keys
        )
