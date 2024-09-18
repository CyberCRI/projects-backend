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
