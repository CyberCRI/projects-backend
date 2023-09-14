import uuid

from django.conf import settings
from django.core.files import File
from django.db import migrations


def get_image_file(path: str) -> File:
    return File(open(path, 'rb'))


def logo_upload_to(instance, filename) -> str:
    return f'organization/logo/{uuid.uuid4()}#{instance.name}'


def banner_upload_to(instance, filename) -> str:
    return f'organization/banner/{uuid.uuid4()}#{instance.name}'


def upload_image_from_assets(path, apps, upload_to):
    """Return an Image instance."""
    model = apps.get_model("files", "Image")
    file = get_image_file(path)
    image = model(name=f"{uuid.uuid4()}.png", file=file)
    image._upload_to = upload_to
    image.save()
    return image


def create_default_organization(apps, schema_editor):
    model = apps.get_model("organizations", "Organization")
    db_alias = schema_editor.connection.alias
    default_organization = model.objects.filter(code='DEFAULT')
    if default_organization.exists():
        banner = upload_image_from_assets(f'{settings.BASE_DIR}/assets/default_banner.jpeg', apps, banner_upload_to)
        logo = upload_image_from_assets(f'{settings.BASE_DIR}/assets/default_logo.png', apps, logo_upload_to)
        default_organization.update(
            name='Main organization',
            background_color='#FFFFFF',
            banner_image=banner,
            logo_image=logo,
            dashboard_title='Bienvenue sur notre annuaire de projets',
            dashboard_subtitle='Le savoir est la seule matière qui s\'accroît quand on la partage - Socrate',
            contact_email='projects.platform@learningplanetinstitute.org',
            website_url='https://projects.directory',
            main_org_logo_visibility=False
        )
        add_to_default = [
            'CRI', 'SAVANTURIERS', 'LEARNINGPLANET', 'EDUNUM', 'AGREENIUM', 'LEARNIN', 'PROFSCHERCHEURS', 'UPARIS',
            'DIGIUR', 'UNIVIE', 'CATI'
        ]
        model.objects.using(db_alias).filter(code__in=add_to_default).update(parent=default_organization.first())


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0010_auto_20220513_0854'),
    ]

    operations = [
        migrations.RunPython(create_default_organization, migrations.RunPython.noop),
    ]
