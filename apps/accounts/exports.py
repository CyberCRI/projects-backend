from import_export import fields, resources  # type: ignore

from .models import PeopleGroup, ProjectUser


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
            "mobile_phone",
            "landline_phone",
            "portals",
            "language",
            "location",
            "sdgs",
            "created_at",
            "last_login",
        ]
        model = ProjectUser

    def dehydrate_portals(self, user: ProjectUser) -> str:
        organizations = user.get_related_organizations()
        return ",".join([f"{o.code}" for o in organizations])


class PeopleGroupResource(resources.ModelResource):
    parent_id = fields.Field()

    class Meta:
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "email",
            "sdgs",
            "parent_id",
            "organization",
            "publication_status",
            "created_at",
            "updated_at",
        ]
        model = PeopleGroup

    def dehydrate_organization(self, people_group: PeopleGroup) -> str:
        return people_group.organization.code

    def dehydrate_parent_id(self, people_group: PeopleGroup) -> int | None:
        return people_group.parent.id if people_group.parent else None
