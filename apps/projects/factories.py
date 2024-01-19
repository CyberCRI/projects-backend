import factory
from factory.fuzzy import FuzzyChoice, FuzzyInteger

from apps.accounts.factories import UserFactory
from apps.commons.factories import language_factory, sdg_factory
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.organizations.models import Organization

from .models import BlogEntry, LinkedProject, Location, Project


class SeedProjectFactory(factory.django.DjangoModelFactory):
    id = factory.Faker("pystr", min_chars=8, max_chars=8)
    publication_status = Project.PublicationStatus.PUBLIC
    life_status = FuzzyChoice(Project.LifeStatus.choices, getter=lambda c: c[0])
    language = language_factory()
    title = factory.Faker("sentence", nb_words=4)
    header_image = None
    description = factory.Faker("text")
    purpose = factory.Faker("text")
    is_shareable = factory.Faker("boolean")
    sdgs = factory.List([sdg_factory() for _ in range(FuzzyInteger(0, 17).fuzz())])
    main_category = None

    class Meta:
        model = Project
        django_get_or_create = ("id",)

    @classmethod
    def create(cls, **kwargs):
        instance = super().create(**kwargs)
        instance.setup_permissions(UserFactory())
        return instance


class ProjectFactory(SeedProjectFactory):
    @factory.post_generation
    def organizations(self, create, extracted):
        if not create:
            return
        if extracted:
            # A list of groups were passed in, use them
            for org in extracted:
                self.organizations.add(org)
            if len(extracted) == 0:
                self.organizations.add(OrganizationFactory())
        else:
            self.organizations.add(OrganizationFactory())

    @factory.post_generation
    def categories(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted and len(extracted) > 0:
            self.main_category = extracted[0]
            for category in extracted:
                self.categories.add(category)
        else:
            category = ProjectCategoryFactory(organization=self.organizations.first())
            self.main_category = category
            self.categories.add(category)


class BlogEntryFactory(factory.django.DjangoModelFactory):
    project = factory.LazyFunction(
        lambda: ProjectFactory()
    )  # Subfactory seems to not trigger `create()`
    title = factory.Faker("text", max_nb_chars=255)
    content = factory.Faker("text")

    class Meta:
        model = BlogEntry


class LocationFactory(factory.django.DjangoModelFactory):
    project = factory.LazyFunction(
        lambda: ProjectFactory()
    )  # Subfactory seems to not trigger `create()`
    title = factory.Faker("text", max_nb_chars=255)
    description = factory.Faker("text")
    lat = factory.Faker("pyfloat")
    lng = factory.Faker("pyfloat")
    type = FuzzyChoice(Location.LocationType.choices, getter=lambda c: c[0])

    class Meta:
        model = Location


class LinkedProjectFactory(factory.django.DjangoModelFactory):
    project = factory.SubFactory(ProjectFactory)
    target = factory.SubFactory(ProjectFactory)

    class Meta:
        model = LinkedProject
        django_get_or_create = ("project", "target")


class SeedProjectOrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project.organizations.through
        django_get_or_create = ("project", "organization")

    organization = factory.fuzzy.FuzzyChoice(Organization.objects.filter())
    project = factory.fuzzy.FuzzyChoice(Project.objects.filter())
