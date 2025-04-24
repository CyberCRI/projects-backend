import factory
from django.utils import timezone
from faker import Faker

from apps.accounts.factories import UserFactory
from apps.commons.factories import language_factory
from apps.commons.utils import get_test_image
from apps.organizations.models import Organization, ProjectCategory, Template

faker = Faker()


class OrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Organization
        django_get_or_create = ("code",)

    name = factory.Faker("pystr", min_chars=1, max_chars=50)
    dashboard_title = factory.Faker("text", max_nb_chars=255)
    dashboard_subtitle = factory.Faker("text", max_nb_chars=255)
    description = factory.Faker("text", max_nb_chars=255)
    language = language_factory()
    code = factory.Sequence(lambda n: faker.word() + str(n))
    background_color = factory.Faker("color")
    banner_image = None
    contact_email = factory.Faker("email")
    chat_url = factory.Faker("url")
    chat_button_text = factory.Faker("text", max_nb_chars=50)
    logo_image = factory.LazyFunction(get_test_image)
    website_url = factory.Faker("url")
    created_at = timezone.localtime(timezone.now())
    updated_at = timezone.localtime(timezone.now())
    parent = None

    @classmethod
    def create(cls, **kwargs):
        instance = super().create(**kwargs)
        instance.setup_permissions()
        return instance

    @factory.post_generation
    def with_admin(self, create, extracted, **kwargs):
        if create and extracted is True:
            UserFactory(groups=[self.get_admins()])


class TemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Template

    name = factory.Faker("word")
    description = factory.Faker("text")
    organization = factory.LazyFunction(lambda: OrganizationFactory())
    project_title = factory.Faker("sentence")
    project_description = factory.Faker("text")
    blogentry_title = factory.Faker("sentence")
    blogentry_content = factory.Faker("text")
    goal_title = factory.Faker("sentence")
    goal_description = factory.Faker("text")
    review_title = factory.Faker("sentence")
    review_description = factory.Faker("text")

    @factory.post_generation
    def categories(self, create, extracted, **kwargs):
        if create and extracted and len(extracted) > 0:
            self.categories.add(*extracted)


class ProjectCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectCategory

    organization = factory.LazyFunction(
        lambda: OrganizationFactory()
    )  # Subfactory seems to not trigger `create()`
    order_index = factory.Sequence(lambda n: n % 32767)
    background_color = factory.Faker("color")
    background_image = None
    description = factory.Faker("text")
    foreground_color = factory.Faker("color")
    name = factory.Faker("word")
    is_reviewable = factory.Faker("boolean")

    @factory.post_generation
    def templates(self, create, extracted, **kwargs):
        if create and extracted and len(extracted) > 0:
            self.templates.add(*extracted)


class SeedProjectCategoryFactory(ProjectCategoryFactory):
    organization = factory.fuzzy.FuzzyChoice(Organization.objects.all())
