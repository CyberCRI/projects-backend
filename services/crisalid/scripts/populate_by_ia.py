import datetime
import json
import pathlib

from django.contrib.postgres.aggregates import StringAgg
from django.db import models
from django.db.models import F, Value
from django.db.models.functions import Concat

from apps.organizations.models import Organization
from services.crisalid.models.award import Award, AwardContributor
from services.crisalid.models.patent import Patent
from services.crisalid.models.researcher import Researcher
from services.mistral.interface import MistralService

prompt = (
    pathlib.Path(__file__).resolve().parent / pathlib.Path("./prompt_ia.txt")
).read_text()


def format_date(date) -> datetime.date | None:
    if not date:
        return None

    return datetime.datetime.strptime(date, "%Y-%m-%d").date()


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
            {"content": prompt, "role": "system"},
            {"content": prompt_user, "role": "user"},
        ]

        try:
            response = mistral.chat.complete(
                model="mistral-small-2603",
                messages=messages,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            print(e)
            continue

        content = json.loads(response.choices[0].message.content)

        if content.get("bibliometrics"):
            h_index = content["bibliometrics"].get("h_index", {}).get("value")
            i10_index = content["bibliometrics"].get("i10_index", {}).get("value")

            researcher.h_index = h_index
            researcher.i10_index = i10_index
            if any((h_index, i10_index)):
                researcher.save()
                print("save researcher")

        for patent in content.get("patents", []):
            p = Patent(
                **patent, data=format_date(patent["date"]), researcher=researcher
            )
            p.save()
            print("patent ", p.name)

        for award_contributor in content.get("awardResearcher", []):
            if not award_contributor.get("award"):
                continue
            award, _ = Award.objects.get_or_create(
                name=award_contributor["award"]["name"],
                defaults={"description": award_contributor["award"]["description"]},
            )
            AwardContributor(
                link=award_contributor["link"],
                description=award_contributor["description"],
                date=format_date(award_contributor["date"]),
                award=award,
                researcher=researcher,
            ).save()
            print("create Award", award.name)
