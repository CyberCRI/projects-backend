import json
import os
import pathlib

import requests
from django.core.management.base import BaseCommand

OUTPUT = pathlib.Path(__file__).parent.parent.parent


class Command(BaseCommand):
    help = "this script generate a choices.py for relators choices (from json relators)"  # noqa: A003

    def handle(self, **options):
        response = requests.get("https://id.loc.gov/vocabulary/relators.json")
        relators = response.json()

        # convert relators json to "readable json"
        dict_relators = {}
        for relator in relators:
            url = relator["@id"]
            if "http://www.loc.gov/mads/rdf/v1#code" not in relator:
                continue

            value = None
            if "http://www.loc.gov/mads/rdf/v1#authoritativeLabel" in relator:
                value = relator["http://www.loc.gov/mads/rdf/v1#authoritativeLabel"][0][
                    "@value"
                ]

            dict_relators[url] = {
                "key": relator["http://www.loc.gov/mads/rdf/v1#code"][0][
                    "@value"
                ].lower(),
                "value": value,
            }

        del relators

        template = f"""
from django.db import models
from django.utils.translation import gettext_lazy as _

\"""
    this file is a generated file from command `generate_crisalid_relators`
\"""

raw = {json.dumps(dict_relators)}

class RolesChoices(models.TextChoices):
    \"""
        values generated from https://id.loc.gov/vocabulary/relators.json
    \"""
"""

        # choices for django models
        choices = [(dtc["key"], dtc["value"]) for dtc in dict_relators.values()]

        for key, value in sorted(choices, key=lambda x: x[0]):
            template += f'    {key.upper()} = "{key.lower()}", _("{value}")\n'

        with open(os.path.join(OUTPUT, "relators.py"), "w") as f:
            f.write(template)
