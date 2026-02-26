from rest_framework import serializers


class ModulesSerializers(serializers.ModelSerializer):
    """Modules serializers to return how many elements is linked to objects"""

    modules = serializers.SerializerMethodField()

    def get_modules(self, instance):
        request = self.context.get("request")

        modules_keys = None
        if "modules" in request.query_params:
            modules_keys = request.query_params.getlist("modules")
        if modules_keys is None:
            modules_keys = getattr(self.Meta, "modules_keys", None)

        modules_manager = instance.get_related_module()
        return modules_manager(instance, user=request.user).count(modules_keys)
