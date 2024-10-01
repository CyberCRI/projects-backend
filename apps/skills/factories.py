import factory
from faker import Faker

from apps.accounts.factories import UserFactory

from .models import Skill, Tag

faker = Faker()

ESCO_BASE_URI = "http://data.europa.eu/esco"


class TagFactory(factory.django.DjangoModelFactory):
    type = Tag.TagType.CUSTOM
    title = factory.Faker("sentence")
    title_en = factory.Faker("sentence")
    title_fr = factory.Faker("sentence")
    description = factory.Faker("text")
    description_en = factory.Faker("text")
    description_fr = factory.Faker("text")

    class Meta:
        model = Tag

    @factory.post_generation
    def set_external_id(self, create, extracted, **kwargs):
        if create:
            if self.type == Tag.TagType.CUSTOM:
                self.external_id = faker.uuid4()
            if self.type == Tag.TagType.ESCO:
                if self.secondary_type is None:
                    self.secondary_type = Tag.SecondaryTagType.SKILL
                self.external_id = (
                    f"{ESCO_BASE_URI}/{self.secondary_type}/{faker.uuid4()}"
                )
            if self.type == Tag.TagType.WIKIPEDIA:
                self.external_id = f"Q{self.id}{faker.pyint()}"


class SkillFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    tag = factory.SubFactory(TagFactory)
    level = factory.Faker("random_digit")
    level_to_reach = factory.Faker("random_digit")

    class Meta:
        model = Skill
