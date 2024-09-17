import factory

from .models import EscoOccupation, EscoSkill


class EscoSkillFactory(factory.django.DjangoModelFactory):
    uri = factory.Faker("url")
    title = factory.Faker("sentence")
    title_en = factory.Faker("sentence")
    title_fr = factory.Faker("sentence")
    description = factory.Faker("text")
    description_en = factory.Faker("text")
    description_fr = factory.Faker("text")

    class Meta:
        model = EscoSkill


class EscoOccupationFactory(factory.django.DjangoModelFactory):
    uri = factory.Faker("url")
    title = factory.Faker("sentence")
    title_en = factory.Faker("sentence")
    title_fr = factory.Faker("sentence")
    description = factory.Faker("text")
    description_en = factory.Faker("text")
    description_fr = factory.Faker("text")

    class Meta:
        model = EscoOccupation
