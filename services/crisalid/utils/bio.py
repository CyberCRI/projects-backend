from services.crisalid.models import Researcher
from services.mistral.models import ResearcherEmbedding


def generate_bio_from_researcher(researcher: Researcher) -> str:
    """generate bio form researcher"""
    # instantiate models instend of
    embeding = ResearcherEmbedding(item=researcher)
    return embeding.get_summary()
