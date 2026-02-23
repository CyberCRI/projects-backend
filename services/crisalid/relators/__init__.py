import json
import os

# relator files from loc.gov
# values from https://id.loc.gov/vocabulary/relators.json

RELATORS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "relators.json"
)

with open(RELATORS_FILE) as f:
    relators = json.load(f)

# convert relators json to "readable json"
dict_relators = {}
for relator in relators:
    url = relator["@id"]
    if any(
        (
            "http://www.loc.gov/mads/rdf/v1#code" not in relator,
            "http://www.loc.gov/mads/rdf/v1#authoritativeLabel" not in relator,
        )
    ):
        continue

    dict_relators[url] = {
        "key": relator["http://www.loc.gov/mads/rdf/v1#code"][0]["@value"].upper(),
        "value": relator["http://www.loc.gov/mads/rdf/v1#authoritativeLabel"][0][
            "@value"
        ],
    }

del relators

# choices for django models
choices = [(dtc["key"], dtc["value"]) for dtc in dict_relators.values()]
