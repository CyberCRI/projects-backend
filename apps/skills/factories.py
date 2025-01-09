import factory
from faker import Faker

from apps.accounts.factories import UserFactory
from apps.organizations.factories import OrganizationFactory

from .models import Mentoring, Skill, Tag, TagClassification

faker = Faker()

ESCO_BASE_URI = "http://data.europa.eu/esco"


class TagFactory(factory.django.DjangoModelFactory):
    type = Tag.TagType.CUSTOM
    title = factory.Faker("word")
    title_en = factory.Faker("word")
    title_fr = factory.Faker("word")
    description = factory.Faker("sentence")
    description_en = factory.Faker("sentence")
    description_fr = factory.Faker("sentence")

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


class TagClassificationFactory(factory.django.DjangoModelFactory):
    type = TagClassification.TagClassificationType.CUSTOM
    organization = factory.LazyFunction(
        lambda: OrganizationFactory()
    )  # Subfactory seems to not trigger `create()`
    title = factory.Faker("word")
    description = factory.Faker("sentence")

    class Meta:
        model = TagClassification

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return
        self.tags.add(*(extracted if extracted else []))


class SkillFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    tag = factory.SubFactory(TagFactory)
    level = factory.Faker("random_digit")
    level_to_reach = factory.Faker("random_digit")

    class Meta:
        model = Skill


class MentoreeCreatedMentoringFactory(factory.django.DjangoModelFactory):
    mentor = factory.SubFactory(UserFactory)
    mentoree = factory.SubFactory(UserFactory)
    skill = factory.LazyAttribute(
        lambda x: SkillFactory(user=x.mentor, can_mentor=True)
    )
    created_by = factory.LazyAttribute(lambda x: x.mentoree)

    class Meta:
        model = Mentoring


class MentorCreatedMentoringFactory(factory.django.DjangoModelFactory):
    mentor = factory.SubFactory(UserFactory)
    mentoree = factory.SubFactory(UserFactory)
    skill = factory.LazyAttribute(
        lambda x: SkillFactory(user=x.mentoree, needs_mentor=True)
    )
    created_by = factory.LazyAttribute(lambda x: x.mentor)

    class Meta:
        model = Mentoring
