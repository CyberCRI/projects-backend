from factory.fuzzy import FuzzyChoice

from apps.commons.models import SDG, Language


def language_factory():
    return FuzzyChoice(Language.choices, getter=lambda c: c[0])


def sdg_factory():
    return FuzzyChoice(SDG.choices, getter=lambda c: c[0])
