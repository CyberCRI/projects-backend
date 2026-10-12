from services.crisalid.models import Researcher


def generate_bio_from_researcher(researcher: Researcher) -> str:
    """generate bio form researcher"""
    return researcher.embedding.get_summary()
