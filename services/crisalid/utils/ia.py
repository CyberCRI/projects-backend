import json
import logging
import pathlib

from django.contrib.postgres.aggregates import StringAgg
from django.db import models
from django.db.models import F, Value
from django.db.models.functions import Concat

from services.crisalid.models.researcher import Researcher
from services.mistral.interface import MistralService

logger = logging.getLogger(__name__)

PROMPT_DIR = pathlib.Path(__file__).resolve().absolute().parent.parent / "prompts"


def prompt_identifiers(
    researcher: Researcher,
) -> str:
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

    return f"""**Provided Identifiers:**
- Full Name: {str(researcher)}
- Provided Identifiers:
{formated_identifiers}
"""


def conversations(messages: list[dict]) -> dict | None:
    mistral = MistralService()

    logger.info("Call Mistral conversations")
    try:
        response = mistral.beta.conversations.start(
            model="mistral-large-latest",
            inputs=messages,
            tools=[{"type": "web_search"}],
        )
        for output in response.outputs:
            if output.type == "message.output":
                return json.loads(
                    output.content.split("```")[1].removeprefix("json"),
                    strict=False,
                )
        raise ValueError("Empty Mistral results")
    except Exception:
        logger.exception("Empty Mistral results")
        return None


def generate_bio_from_researcher(researcher: Researcher) -> dict | None:
    """generate bio form researcher"""

    prompt_bio = (PROMPT_DIR / "researcher-bio.txt").read_text()
    messages = [
        {"content": prompt_bio, "role": "user"},
        {"content": prompt_identifiers(researcher), "role": "user"},
    ]

    if not (results := conversations(messages)):
        return None

    researcher_descriptions = results.get("researcher", {}).get(
        "researcherDescriptions"
    )
    if not researcher_descriptions:
        return None
    return researcher_descriptions
