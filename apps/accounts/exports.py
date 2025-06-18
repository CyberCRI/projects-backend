from import_export import fields, resources  # type: ignore

from .models import ProjectUser


class UserResource(resources.ModelResource):
    portals = fields.Field()

    class Meta:
        fields = [
            "id",
            "slug",
            "email",
            "given_name",
            "family_name",
            "job",
            "portals",
            "language",
            "location",
            "sdgs",
            "created_at",
            "last_login",
        ]
        model = ProjectUser

    def dehydrate_portals(self, user: ProjectUser):
        organizations = user.get_related_organizations()
        return ",".join([f"{o.code}" for o in organizations])
