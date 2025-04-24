from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.urls import reverse

from apps.files.models import Image
from apps.organizations.models import ProjectCategory, Template


class Command(BaseCommand):
    def handle(self, *args, **options):
        for category in ProjectCategory.objects.all():
            if category.template:
                template = category.template
                template.categories.add(category)
                template.organization = category.organization
                template.save()
        for template in Template.objects.all():
            for field in [
                "description",
                "project_description",
                "blogentry_content",
                "goal_description",
                "review_description",
            ]:
                text = getattr(template, field)
                soup = BeautifulSoup(text, features="html.parser")
                images_tags = soup.findAll("img")
                for image_tag in images_tags:
                    image_url = image_tag["src"]
                    if (
                        image_url.startswith("/v1/category/")
                        and "/template-image/" in image_url
                    ):
                        image_id = (
                            image_url.split("/")[-1]
                            if image_url[-1] != "/"
                            else image_url.split("/")[-2]
                        )
                image = Image.objects.get(id=image_id)
                template.images.add(image)
                text = text.replace(
                    image_url,
                    reverse(
                        "Template-images-detail",
                        args=(template.organization.code, template.id, image.id),
                    ),
                )
                setattr(template, field, text)
                template.save()
