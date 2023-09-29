import factory.django

from apps.misc.models import Tag, WikipediaTag
from apps.organizations.factories import OrganizationFactory


class WikipediaTagFactory(factory.django.DjangoModelFactory):
    name_fr = factory.Faker("pystr", min_chars=1, max_chars=50)
    name_en = factory.Faker("pystr", min_chars=1, max_chars=50)
    wikipedia_qid = factory.Sequence(lambda n: f"Q{n}")

    class Meta:
        model = WikipediaTag


class TagFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("pystr", min_chars=1, max_chars=50)
    organization = factory.SubFactory(OrganizationFactory)

    class Meta:
        model = Tag
