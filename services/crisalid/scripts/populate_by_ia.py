import datetime
import json
import pathlib

from django.contrib.postgres.aggregates import StringAgg
from django.db import models
from django.db.models import F, Value
from django.db.models.functions import Concat

from apps.organizations.models import Organization
from apps.skills.models import Tag, TagClassification
from services.crisalid.models.award import Award, AwardContributor
from services.crisalid.models.funding import Funding
from services.crisalid.models.patent import Patent, PatentContributor
from services.crisalid.models.researcher import Researcher, ResearcherDomains
from services.crisalid.models.teaching import Teaching
from services.mistral.interface import MistralService

prompt = (
    pathlib.Path(__file__).resolve().parent / pathlib.Path("./prompt_ia.txt")
).read_text()
prompt_domains = (
    pathlib.Path(__file__).resolve().parent / pathlib.Path("./prompt_domains_ia.txt")
).read_text()


def format_date(date) -> datetime.date | None:
    if not date:
        return None

    for formater in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.datetime.strptime(date, formater).date()
        except Exception:
            pass
    return None


def fetch_prompt(researcher: Researcher, local_prompt: str) -> dict | None:
    print(f"researcher_pk: {researcher.pk}")

    mistral = MistralService.service
    formated_identifiers = researcher.modules.public_identifiers().aggregate(
        formated=StringAgg(
            Concat(
                Value("• "),
                F("harvester"),
                Value(" : "),
                F("value"),
                output_field=models.CharField(),
            ),
            delimiter="\n",
        )
    )["formated"]

    prompt_user = f"""**Provided Identifiers:**
- Full Name: {str(researcher)}
- Provided Identifiers:
{formated_identifiers}
"""

    messages = [
        {"content": local_prompt + "\n" + prompt_user, "role": "user"},
    ]

    print(prompt_user)
    try:
        response = mistral.beta.conversations.start(
            model="mistral-large-latest",
            inputs=messages,
            tools=[{"type": "web_search"}],
        )
        for output in response.outputs:
            if output.type == "message.output":
                print(output.content)
                return json.loads(
                    output.content.split("```")[1].removeprefix("json"),
                    strict=False,
                )
        raise ValueError("empty conversation")
    except Exception as e:
        print(e)
        return None


def populate_researcher_domains(researcher: Researcher):
    results = fetch_prompt(researcher, prompt_domains)
    print(results)
    if not results:
        return

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


def populate_researcher(researcher: Researcher):
    result = fetch_prompt(researcher, prompt)
    if not result:
        return

    content = result.get("researcher", {})

    if content.get("bibliometrics"):
        h_index = content["bibliometrics"].get("h_index", {}).get("value")
        i10_index = content["bibliometrics"].get("i10_index", {}).get("value")

        researcher.h_index = h_index
        researcher.i10_index = i10_index
        researcher.save()

    if content.get("researcherDescriptions"):
        researcher.short_bio = content["researcherDescriptions"].get("short", "")
        researcher.bio = content["researcherDescriptions"].get("long", "")
        researcher.save()

    for patent in content.get("patents", []):
        p, _ = Patent.objects.get_or_create(
            name=patent["name"],
            defaults={
                "description": patent["description"],
                "link": patent["link"],
                "date": format_date(patent["date"]),
            },
        )
        PatentContributor.objects.update_or_create(patent=p, researcher=researcher)
        print("create Patent ", p.name)

    for award_contributor in content.get("awardResearcher", []):
        if not award_contributor.get("award"):
            continue
        award, _ = Award.objects.get_or_create(
            name=award_contributor["award"]["name"],
            defaults={"description": award_contributor["award"]["description"]},
        )
        AwardContributor.objects.get_or_create(
            award=award,
            researcher=researcher,
            defaults={
                "link": award_contributor["link"],
                "description": award_contributor["description"],
                "date": format_date(award_contributor["date"]),
            },
        )
        print("create Award", award.name)

    for teaching in content.get("teaching", []):
        teaching, _ = Teaching.objects.update_or_create(
            link=teaching["link"],
            researcher=researcher,
            defaults={
                "name": teaching["name"],
                "description": teaching["description"],
                "spec": teaching["spec"],
                "level": teaching["level"],
            },
        )
        print("create teaching ", teaching.name)

    for funding in content.get("funding", []):
        fund, _ = Funding.objects.update_or_create(
            name=funding["name"],
            defaults={
                "description": funding["description"],
                "prices": funding["prices"],
                "currency": funding["currency"],
                "start_date": format_date(funding["start_date"]),
                "end_date": format_date(funding["end_date"]),
            },
        )
        fund.researchers.add(researcher)
        print("create funding ", fund.name)


def run(code: str, offset: int | None = None, limit: int | None = None):
    organization = Organization.objects.get(code=code)

    researchers = (
        Researcher.objects.filter(user__groups__organizations__in=(organization,))
        .select_related("user")
        .order_by("pk")
    )

    if offset:
        researchers = researchers[int(offset) :]
    if limit:
        researchers = researchers[: int(limit)]

    total = researchers.count()
    for idx, researcher in enumerate(researchers):
        print(f"Start {idx}/{total}")
        populate_researcher(researcher)
