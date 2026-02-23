from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.urls import reverse

from apps.files.models import Image
from apps.organizations.models import ProjectCategory, Template
from apps.projects.models import Project


class Command(BaseCommand):
    def _update_templates_organization(self):
        for template in Template.objects.all():
            category = ProjectCategory.objects.filter(template=template)
            if category.exists():
                category = category.get()
                organization = category.organization
                print(f"Adding organization {organization} to template {template.id}")
                template.organization = organization
                template.save()

    def _update_template_image_url(
        self, template: Template, field: str, text: str, image_url: str
    ) -> str:
        if image_url.startswith("/v1/category/") and "/template-image/" in image_url:
            image_id = (
                image_url.split("/")[-1]
                if image_url[-1] != "/"
                else image_url.split("/")[-2]
            )
            image = Image.objects.filter(id=image_id)
            if image.exists():
                image = image.get()
                template.images.add(image)
            else:
                print(f"Image with id {image_id} not found")
            new_url = reverse(
                "Template-images-detail",
                args=(template.organization.code, template.id, image_id),
            )
            text = text.replace(image_url, new_url)
            setattr(template, field, text)
            template.save()
            print(f"Updated {field} for template {template.id}")
            print(f"replaced {image_url} with {new_url}")
            template.refresh_from_db()
            print(f"Success : {image_url not in getattr(template, field)}")
            print("--------------------")
        return text

    def _update_template_images_urls(self):
        for template in Template.objects.all():
            if template.organization:
                print(
                    f"Updating template {template.id} for organization {template.organization.code}"
                )
                for field in [
                    "description",
                    "project_description",
                    "project_purpose",
                    "blogentry_content",
                    "goal_description",
                    "review_description",
                    "comment_content",
                ]:
                    text = getattr(template, field)
                    soup = BeautifulSoup(text, features="html.parser")
                    images_tags = soup.findAll("img")
                    for image_tag in images_tags:
                        image_url = image_tag["src"]
                        text = self._update_template_image_url(
                            template, field, text, image_url
                        )
            else:
                print(f"Template {template.id} has no organization")

    def _add_project_template(self):
        for project in Project.objects.all():
            if project.main_category and project.main_category.template:
                Project.objects.filter(id=project.id).update(
                    template=project.main_category.template
                )
        no_main_category = Project.objects.filter(main_category__isnull=True).count()
        print(f"Projects with no main category: {no_main_category}")
        no_template = Project.objects.filter(template__isnull=True).count()
        print(f"Projects with no template: {no_template}")
        with_template = Project.objects.filter(template__isnull=False).count()
        print(f"Projects with template: {with_template}")
        total_projects = Project.objects.count()
        print(f"Total projects: {total_projects}")

    def handle(self, *args, **options):
        self._update_templates_organization()
        print("====================")
        self._update_template_images_urls()
        print("====================")
        self._add_project_template()
