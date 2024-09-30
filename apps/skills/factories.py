import factory
from faker import Faker

from .models import Tag

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
    def set_external_id(self):
        if self.type == Tag.TagType.CUSTOM:
            self.external_id = faker.uuid4()
        if self.type == Tag.TagType.ESCO:
            if self.secondary_type is None:
                self.secondary_type = Tag.SecondaryTagType.SKILL
            self.external_id = f"{ESCO_BASE_URI}/{self.secondary_type}/{faker.uuid4()}"
        if self.type == Tag.TagType.WIKIPEDIA:
            self.external_id = f"Q{self.id}{faker.pyint()}"
