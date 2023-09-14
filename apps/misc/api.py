import requests
from django.conf import settings

from .models import Language, WikipediaTag


def get_query_from_wikipedia_gw(query_params):
    return requests.get(
        f"{settings.WIKIPEDIA_GATEWAY_URL}/api/v1/wikipedia/page",
        params=query_params,
        timeout=settings.REQUESTS_DEFAULT_TIMEOUT,
    )


def get_disambiguation_page_from_wikipedia_gw(page_id, query_params):
    return requests.get(
        f"{settings.WIKIPEDIA_GATEWAY_URL}/api/v1/wikipedia/disambiguation-page/{page_id}",
        params=query_params,
        timeout=settings.REQUESTS_DEFAULT_TIMEOUT,
    )


def get_tag_from_wikipedia_gw(qid):
    return requests.get(
        f"{settings.WIKIPEDIA_GATEWAY_URL}/api/v1/wikipedia/page/{qid}",
        params={"lang": [language.lower() for language in Language.values]},
        timeout=settings.REQUESTS_DEFAULT_TIMEOUT,
    )


def create_tag_from_wikipedia_gw(qid):
    response = get_tag_from_wikipedia_gw(qid)
    names = ["name_en", *[f"name_{lang}" for lang in settings.REQUIRED_LANGUAGES]]
    for name in names:
        name_en = response.json().get(name)
        if name_en:
            break
    defaults = {
        "name_fr": response.json().get("name_fr", None),
        "name_en": name_en,
    }
    tag, _ = WikipediaTag.objects.update_or_create(wikipedia_qid=qid, defaults=defaults)
    return tag
