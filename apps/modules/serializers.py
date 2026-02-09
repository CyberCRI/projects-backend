from rest_framework import serializers


class ModulesSerializers(serializers.ModelSerializer):
    """Modules serializers to return how many elements is linked to objects"""

    modules = serializers.SerializerMethodField()

    def get_modules(self, instance):
        request = self.context.get("request")

        modules_manager = instance.get_related_module()
        return modules_manager(instance, user=request.user).count()
