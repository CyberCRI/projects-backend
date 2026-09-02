from django.core.management import BaseCommand

from apps.files.models import Image
from apps.projects.models import BlogEntry, Project


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform a dry run without saving changes to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        extra_projects_images = {}
        for i, project in enumerate(Project.objects.all()):
            if i % 100 == 0:
                print(f"{i}/{Project.objects.count()}")
            for image in project.images.all():
                if f"/image/{image.id}" not in project.description:
                    extra_projects_images[project.id] = extra_projects_images.get(
                        project.id, []
                    ) + [image.id]
        extra_blog_images = {}
        for i, blog in enumerate(BlogEntry.objects.all()):
            if i % 100 == 0:
                print(f"{i}/{BlogEntry.objects.count()}")
            for image in blog.images.all():
                if f"/blog-entry-image/{image.id}" not in blog.content:
                    extra_blog_images[blog.id] = extra_blog_images.get(blog.id, []) + [
                        image.id
                    ]
        impacted_project_images = sum(
            [len(images) for images in extra_projects_images.values()]
        )
        total_project_images = Image.objects.filter(projects__isnull=False).count()
        impacted_blog_images = sum(
            [len(images) for images in extra_blog_images.values()]
        )
        total_blog_images = Image.objects.filter(blog_entries__isnull=False).count()
        self.stdout.write(
            f"{len(extra_projects_images)} projects impacted out of {Project.objects.count()}"
        )
        self.stdout.write(
            f"{impacted_project_images} project images impacted out of {total_project_images}"
        )
        self.stdout.write(
            f"{len(extra_blog_images)} blogs impacted out of {BlogEntry.objects.count()}"
        )
        self.stdout.write(
            f"{impacted_blog_images} blog images impacted out of {total_blog_images}"
        )
        if not dry_run:
            for project in Project.objects.filter(id__in=extra_projects_images.keys()):
                project.images.remove(*extra_projects_images[project.id])
            for blog in BlogEntry.objects.filter(id__in=extra_blog_images.keys()):
                blog.images.remove(*extra_blog_images[blog.id])
