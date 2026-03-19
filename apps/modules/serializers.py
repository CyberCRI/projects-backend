from django.http import QueryDict
from rest_framework import serializers


class ModulesSerializers(serializers.ModelSerializer):
    """Modules serializers to return how many elements is linked to objects"""

    modules = serializers.SerializerMethodField()

    def __init__(self, *ar, **kw):
        super().__init__(*ar, **kw)

        if "modules_keys" not in self.context:
            request = self.context.get("request")
            query = request.query_params if request else QueryDict()

            modules_keys = None
            # if modules is set queryparams , return list elements (for multiples modules)
            if "modules" in query:
                modules_keys = query.getlist("modules")
            # if modules is not set, get "default" values from Meta serializer
            if modules_keys is None:
                modules_keys = getattr(self.Meta, "modules_keys", None)
            self.context["modules_keys"] = (
                tuple(modules_keys) if modules_keys is not None else None
            )

    def get_modules(self, instance):
        request = self.context.get("request")
        modules_keys = self.context.get("modules_keys")

        modules_manager = instance.get_related_module()
        return modules_manager(instance, user=request.user).count(modules_keys)
