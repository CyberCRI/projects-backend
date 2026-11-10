from services.crisalid.models import Researcher
from services.mistral.models import ResearcherEmbedding


def generate_bio_from_researcher(researcher: Researcher, minimal=False) -> str:
    """generate bio form researcher"""
    # instantiate models instend of
    embeding = ResearcherEmbedding(item=researcher)
    if minimal:
        return embeding.get_summary_minimal()
    return embeding.get_summary()
