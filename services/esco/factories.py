import factory
from faker import Faker

from .models import EscoTag

faker = Faker()


class EscoTagFactory(factory.django.DjangoModelFactory):
    type = EscoTag.EscoTagType.SKILL
    uri = factory.Sequence(lambda n: f"{faker.uri()}{n}")
    title = factory.Faker("sentence")
    title_en = factory.Faker("sentence")
    title_fr = factory.Faker("sentence")
    description = factory.Faker("text")
    description_en = factory.Faker("text")
    description_fr = factory.Faker("text")

    class Meta:
        model = EscoTag

    @factory.post_generation
    def parents(self, create, extracted, **kwargs):
        if create and extracted:
            self.parents.add(*extracted)

    @factory.post_generation
    def essential_skills(self, create, extracted, **kwargs):
        if create and extracted:
            self.essential_skills.add(*extracted)

    @factory.post_generation
    def optional_skills(self, create, extracted, **kwargs):
        if create and extracted:
            self.optional_skills.add(*extracted)
