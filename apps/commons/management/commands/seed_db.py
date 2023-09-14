import factory
from django.core.management.base import BaseCommand

from apps.accounts.factories import SeedUserFactory
from apps.announcements.factories import SeedAnnouncementFactory
from apps.organizations.factories import OrganizationFactory, SeedProjectCategoryFactory
from apps.organizations.models import Organization
from apps.projects.factories import SeedProjectFactory, SeedProjectOrganizationFactory


class Command(BaseCommand):
    help = "Seed database"  # noqa: A003

    def handle(self, *args, **options):
        SeedUserFactory(email="user@fake.com")
        cri = OrganizationFactory(code="CRI")
        OrganizationFactory(code="DEFAULT")

        ##################
        #   RANDOM DATA  #
        ##################
        SeedUserFactory.create_batch(size=50)
        self.stdout.write(self.style.SUCCESS("Users generated."))

        OrganizationFactory.create_batch(
            size=5,
            parent=factory.fuzzy.FuzzyChoice(Organization.objects.exclude(id=cri.id)),
        )
        self.stdout.write(self.style.SUCCESS("Organizations generated."))

        SeedProjectCategoryFactory.create_batch(size=15)
        self.stdout.write(self.style.SUCCESS("ProjectCategory generated."))

        SeedProjectFactory.create_batch(size=50)
        SeedProjectOrganizationFactory.create_batch(size=100)
        self.stdout.write(self.style.SUCCESS("Projects generated."))

        SeedAnnouncementFactory.create_batch(size=150)
        self.stdout.write(self.style.SUCCESS("Announcement generated."))
