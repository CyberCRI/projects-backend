from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.projects.models import Project


class Command(BaseCommand):
    def handle(self, *args, **options):
        groups = Group.objects.filter(name__startswith="project").filter(
            name__icontains="people_group"
        )
        groups = [group for group in groups if group.people_groups.exists()]
        for group in groups:
            project_id = group.name.split(":")[1][1:]
            project = Project.objects.get(id=project_id)
            project.member_groups.add(group.people_groups.all())
            project.set_role_group_members(project.get_member_groups())
