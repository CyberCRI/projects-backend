from django.core.management.base import BaseCommand

from apps.accounts.models import ProjectUser


class Command(BaseCommand):
    def handle(self, *args, **options):
        personnal_header = {
            "en": "<p><strong>Personal Description</strong></p>",
            "fr": "<p><strong>Description personnelle</strong></p>",
        }
        professional_header = {
            "en": "<p><strong>Professional Description</strong></p>",
            "fr": "<p><strong>Description professionnelle</strong></p>",
        }
        for user in ProjectUser.objects.all():
            language = user.language
            if language not in ["en", "fr"]:
                language = "en"
            if user.personal_description and user.professional_description:
                description = (
                    professional_header[language]
                    + user.professional_description
                    + "<p></p>"
                    + personnal_header[language]
                    + user.personal_description
                )
                ProjectUser.objects.filter(id=user.id).update(description=description)
            elif user.personal_description and not user.professional_description:
                description = user.personal_description
            elif not user.personal_description and user.professional_description:
                description = user.professional_description
            else:
                description = ""
            ProjectUser.objects.filter(id=user.id).update(description=description)
