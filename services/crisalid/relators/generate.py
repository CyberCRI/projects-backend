import os

from . import choices

"""
this script generate a choices.py for relators choices (from json relators)
"""


BASE = os.path.dirname(os.path.abspath(__file__))

template = """
class RolesChoices(models.TextChoices):
    \"""
        values from https://id.loc.gov/vocabulary/relators.json
    \"""
"""

for key, value in sorted(choices, key=lambda x: x[0]):
    template += f'    {key.upper()} = "{key.upper()}", _("{value}")\n'

with open(os.path.join(BASE, "choices.py"), "w") as f:
    f.write(template)
