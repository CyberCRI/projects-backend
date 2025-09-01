from import_export import fields, resources  # type: ignore

from .models import BlogEntry, Project


class ProjectResource(resources.ModelResource):
    members_names = fields.Field()
    members_emails = fields.Field()
    categories = fields.Field()
    tags = fields.Field()

    class Meta:
        model = Project
        fields = [
            "id",
            "slug",
            "title",
            "purpose",
            "description",
            "members_names",
            "members_emails",
            "groups_names",
            "publication_status",
            "life_status",
            "categories",
            "tags",
            "sdgs",
            "language",
            "is_locked",
            "updated_at",
            "created_at",
        ]

    def dehydrate_members_names(self, project: Project):
        return ",".join([f"{u.get_full_name()}" for u in project.get_all_members()])

    def dehydrate_members_emails(self, project: Project):
        return ",".join([f"{u.email}" for u in project.get_all_members()])

    def dehydrate_groups_names(self, project: Project):
        return ",".join([f"{g.name}" for g in project.get_all_groups()])

    def dehydrate_categories(self, project: Project):
        return ",".join([f"{c.name}" for c in project.categories.all()])

    def dehydrate_tags(self, project: Project):
        return ",".join([f"{t.title}" for t in project.tags.all()])


class BlogEntryResource(resources.ModelResource):
    """Resource for exporting blog entries."""

    class Meta:
        model = BlogEntry
        fields = [
            "id",
            "title",
            "content",
            "created_at",
            "updated_at",
            "project__id",
        ]
