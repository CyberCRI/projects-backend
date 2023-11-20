import factory
from django.utils import timezone
from faker import Faker

from apps.accounts.factories import UserFactory
from apps.commons.factories import language_factory
from apps.commons.utils.create_test_image import get_test_image
from apps.organizations.models import Faq, Organization, ProjectCategory, Template

faker = Faker()


class FaqFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Faq

    title = factory.Faker("text", max_nb_chars=50)
    content = factory.Faker("text")
    organization = factory.RelatedFactory(
        "apps.organizations.factories.OrganizationFactory", factory_related_name="faq"
    )


class OrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Organization
        django_get_or_create = ("code",)

    name = factory.Faker("pystr", min_chars=1, max_chars=50)
    dashboard_title = factory.Faker("text", max_nb_chars=255)
    dashboard_subtitle = factory.Faker("text", max_nb_chars=255)
    language = language_factory()
    code = factory.Sequence(lambda n: faker.word() + str(n))
    background_color = factory.Faker("color")
    banner_image = None
    contact_email = factory.Faker("email")
    logo_image = factory.LazyFunction(get_test_image)
    website_url = factory.Faker("url")
    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)
    faq = factory.SubFactory(FaqFactory, organization=None)
    parent = None

    @classmethod
    def create(cls, **kwargs):
        instance = super().create(**kwargs)
        instance.setup_permissions(UserFactory())
        return instance


class TemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Template

    title_placeholder = factory.Faker("text", max_nb_chars=255)
    goal_placeholder = factory.Faker("text", max_nb_chars=255)
    description_placeholder = factory.Faker("text")
    blogentry_title_placeholder = factory.Faker("text")
    blogentry_placeholder = factory.Faker("text")
    project_category = None


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
    template = factory.SubFactory(TemplateFactory)


class SeedProjectCategoryFactory(ProjectCategoryFactory):
    organization = factory.fuzzy.FuzzyChoice(Organization.objects.all())
