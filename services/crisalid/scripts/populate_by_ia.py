import datetime
import json
import pathlib

from django.contrib.postgres.aggregates import StringAgg
from django.db import models
from django.db.models import F, Value
from django.db.models.functions import Concat

from apps.organizations.models import Organization
from services.crisalid.models.award import Award, AwardContributor
from services.crisalid.models.patent import Patent, PatentContributor
from services.crisalid.models.researcher import Researcher
from services.mistral.interface import MistralService

prompt = (
    pathlib.Path(__file__).resolve().parent / pathlib.Path("./prompt_ia.txt")
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
    mistral = MistralService.service
    for idx, researcher in enumerate(researchers):
        print(f"Start {idx}/{total} researcher_pk: {researcher.pk}")
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
            {"content": prompt + "\n" + prompt_user, "role": "user"},
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
                    content = json.loads(
                        output.content.split("```")[1].removeprefix("json")
                    )
                    if isinstance(content, list):
                        content = content[0]
                    if not isinstance(content, dict):
                        raise ValueError("invlaid type")
                    break
            else:
                raise ValueError("empty conversation")
        except Exception as e:
            print(e)
            continue

        content = content.get("researcher", {})

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
            PatentContributor.objects.update_or_create(
                patent=patent, researcher=researcher
            )
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
