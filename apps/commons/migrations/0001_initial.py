from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.RunSQL(
            'ALTER TEXT SEARCH CONFIGURATION english_conf '
            'ALTER MAPPING FOR numword, numhword, hword_numpart '
            'WITH unaccent, english_stem;'
        ),
        TrigramExtension(),
    ]
