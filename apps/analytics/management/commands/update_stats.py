from django.core.management import BaseCommand

from apps.analytics.models import Stat
from apps.projects.models import Project


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "-i",
            "--shortid",
            type=str,
            help="Shortid of the project you wish to update",
        )

    def handle(self, *args, **options):
        shortid = options["shortid"]
        if shortid is not None:
            project = Project.objects.get(id=shortid)
            if not project:
                self.stderr.write("Error: This project does not exist.")
            else:
                self.update_stats(project)
            return
        for project in Project.objects.all():
            self.update_stats(project)

    @staticmethod
    def update_stats(project):
        if not hasattr(project, "stat"):
            stat = Stat(project=project)
            stat.save()
        stat = project.stat
        stat.comments = project.comments.filter(reply_on=None, deleted_at=None).count()
        stat.replies = (
            project.comments.filter(deleted_at=None).exclude(reply_on=None).count()
        )
        stat.follows = project.follows.count()
        stat.links = project.links.count()
        stat.files = project.files.count()
        stat.blog_entries = project.blog_entries.count()
        stat.goals = project.goals.count()
        stat.versions = project.archive.count()
        stat.description_length = len(project.description)
        stat.save()
