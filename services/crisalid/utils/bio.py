from apps.skills.models import Tag, TagClassification
from services.crisalid.models import Researcher
from services.crisalid.models.researcher import ResearcherDomains
from services.mistral.models import ResearcherEmbedding


def generate_bio_from_researcher(researcher: Researcher) -> str:
    """generate bio form researcher"""
    # instantiate models instend of
    embeding = ResearcherEmbedding(item=researcher)
    return embeding.get_summary()


def generate_domains_from_researcher(researcher: Researcher):
    """generate bio form researcher"""
    # instantiate models instend of
    embeding = ResearcherEmbedding(item=researcher)
    results = embeding.get_dommains_summary()

    classification_openalex = TagClassification.get_or_create_default_classification(
        TagClassification.TagClassificationType.OPENALEX
    )
    classification_wiki = TagClassification.get_or_create_default_classification(
        TagClassification.TagClassificationType.WIKIPEDIA
    )

    for element in results:
        classification = external_id = None
        if element["wikimedia_id"]:
            classification = classification_wiki
            external_id = element["wikimedia_id"]
        elif element["openalex_id"]:
            classification = classification_openalex
            external_id = element["openalex_id"]

        # llm return empty tag id, do nothing
        if not all((external_id, classification)):
            continue

        tag, created = Tag.objects.get_or_create(
            type=classification.type,
            external_id=external_id,
            defaults={
                "title": element["title"],
                "alternative_titles": element["alternative_titles"],
                "description": element["description"],
            },
        )
        if created:
            classification.tags.add(tag)

        ResearcherDomains.objects.update_or_create(
            researcher=researcher, domain=tag, defaults={"level": element["level"]}
        )
