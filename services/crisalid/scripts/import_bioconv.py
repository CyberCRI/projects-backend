import io
import json
import mimetypes
import os
import sys
from contextlib import suppress
from functools import cache
from urllib.parse import urlparse

import requests
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image as PilImage
from PIL import ImageFile

from apps.accounts.models import (
    PeopleGroup,
    PeopleGroupLocation,
    PrivacySettings,
    ProjectUser,
)
from apps.files.models import Image, people_group_images_directory_path
from apps.organizations.models import Organization
from apps.skills.models import Tag, TagClassification
from services.crisalid.models import Identifier, Researcher

# for truncate ico
ImageFile.LOAD_TRUNCATED_IMAGES = True


GUARDIANSHIPS = {
    "Assistance Publique – Hôpitaux de Paris": "AP-HP",
    "AgroParisTech": "APT",
    "Commissariat à l’énergie atomique et aux énergies alternatives": "CEA",
    "Centre national de la recherche scientifique": "CNRS",
    "CentraleSupélec": "CS",
    "Généthon": "GENETHON",
    "Institut national de recherche pour l’agriculture: l’alimentation et l’environnement": "INRAE",
    "Institut national de la santé et de la recherche médicale": "INSERM",
    "Institut Curie": "IC",
    "Institut Gustave Roussy": "IGR",
    "Institut Pasteur": "IP",
    "Institut de Recherche Biomédicale des Armées": "IRBA",
    "Institut de recherche pour le développement": "IRD",
    "Ministère des Armées": "MINARM",
    "Muséum national d’histoire naturelle": "MNHN",
    "Service de santé des armées": "SSA",
    "Sorbonne Université": "SU",
    "Université Paris Sciences et Lettres": "PSL",
    "Université Paris Cité": "UPCité",
    "Université Paris-Saclay": "UPSaclay",
    "Université d’Évry (Évry Paris-Saclay)": "UEVE",
    "Université de Versailles Saint-Quentin-en-Yvelines": "UVSQ",
    "École nationale vétérinaire d’Alfort": "EnvA",
    "École normale supérieure": "ENS",
    "École supérieure de physique et de chimie industrielles de la Ville de Paris": "ESPCI",
}


@cache
def fetch_image(url):
    try:
        response = requests.get(url, verify=False, timeout=2)
        response.raise_for_status()
        # safe results is a images (for not redirect url)
        if "image" not in response.headers["Content-Type"]:
            return None
        return response.content
    except Exception:  # noqa: PIE786
        return None


def populate_member(member: dict, organization: Organization) -> ProjectUser:
    if not member["identifiers"]:
        return None

    identifiers = [
        Identifier.objects.get_or_create(**val)[0] for val in member["identifiers"]
    ]

    researcher = None
    with suppress(Researcher.DoesNotExist):
        researcher = (
            Researcher.objects.from_identifiers(identifiers)
            .select_related("user")
            .get()
        )
    if not researcher:
        researcher = Researcher()

    researcher.given_name = member["first_name"]
    researcher.family_name = member["last_name"]

    user = researcher.user
    if not user:
        user, created = ProjectUser.objects.update_or_create(
            email=member["email"],
            defaults={
                "given_name": member["first_name"],
                "family_name": member["last_name"],
            },
        )
        if created:
            privacy_settings = user.privacy_settings
            privacy_settings.publication_status = (
                PrivacySettings.PrivacyChoices.ORGANIZATION.value
            )
            privacy_settings.save()

        group_organization = organization.get_users()
        user.groups.add(group_organization)

        researcher.user = user
        try:
            researcher.save()
        except Exception:
            print(researcher, "|", user)
            raise
    else:
        researcher.save()

    researcher.identifiers.add(*identifiers)
    return researcher.user


def populate_location(address: dict, group: PeopleGroup):
    PeopleGroupLocation.objects.update_or_create(
        people_group=group,
        defaults={
            "title": address["title"],
            "lat": address["lat"],
            "lng": address["long"],
            "type": PeopleGroupLocation.LocationType.ADDRESS.value,
        },
    )


def populate_tags(
    tags_values: list[str],
    group: PeopleGroup,
    tags_classification: TagClassification,
    tags_description: dict[str, str] = None,
):
    tags_description = tags_description or {}
    exists_tags = list(
        Tag.objects.filter(
            type=Tag.TagType.CUSTOM,
            title__in=tags_values,
            tag_classifications=tags_classification,
        )
    )
    exists_title = [t.title for t in exists_tags]
    updated = False
    for tag_title in tags_values:
        if tag_title not in exists_title:
            description = tags_description.get(tag_title) or ""
            tag = Tag(type=Tag.TagType.CUSTOM, title=tag_title, description=description)
            tag.save()
            tags_classification.tags.add(tag)
            exists_tags.append(tag)
            updated = True
    if updated:
        group.tags.add(*exists_tags)


def populate_image(image_url: str, group: PeopleGroup):
    name = os.path.basename(urlparse(image_url).path)
    content_type, _ = mimetypes.guess_file_type(name)

    if not content_type:
        return False

    content = fetch_image(image_url)
    if not content:
        return False

    # ignore small image
    width, height = PilImage.open(io.BytesIO(content)).size
    if width <= 120 or height <= 120:
        print(width, height, "IGNORED", image_url)
        return False

    file = SimpleUploadedFile(name=name, content=content, content_type=content_type)
    image = Image(
        file=file, name="logo", natural_ratio=2, scale_y=1, scale_x=1, left=0, top=0
    )
    image._upload_to = people_group_images_directory_path
    image.save()
    group.header_image = image
    return True


def populate_lab(
    lab: dict,
    parent: PeopleGroup,
    organization: Organization,
    tags_themes: TagClassification,
    tags_guardianships: TagClassification,
) -> PeopleGroup:
    need_save = False
    title = " - ".join(v for v in (lab["labcode"], lab["title"]) if v)

    description = [lab.get("description", "") or ""]
    short_description = lab.get("short_description", "") or ""

    if lab.get("patents"):
        description.append(f"<h3>Patents:</h3>\n{lab['patents']}")

    if lab.get("school"):
        school = "\n".join(f"<li>{school}</li>" for school in lab.get("school"))
        description.append(f"<h3>Doctoral school:</h3>\n<ul>{school}</ul>")

    if lab.get("partners"):
        partners = "\n".join(f"<li>{partners}</li>" for partners in lab.get("partners"))
        description.append(f"<h3>Partners:</h3>\n<ul>{partners}</ul>")

    description = "\n\n".join(v.strip() for v in description if v.strip()).strip()

    group, created = PeopleGroup.objects.update_or_create(
        name=title,
        parent=parent,
        organization=organization,
        defaults={
            "short_description": short_description,
            "description": f"<p>{description}</p>" if description else "",
        },
    )
    if created:
        group.setup_permissions()

    # location
    if lab["address"]:
        populate_location(lab["address"], group)

    # tags
    tags = set((*lab.get("tags", []), *lab.get("keyword", []), *lab.get("macro", [])))
    populate_tags(tags, group, tags_themes)

    # guardianships / tutelle
    guardianships = set((*lab.get("guardianships", []),))
    populate_tags(
        guardianships, group, tags_guardianships, tags_description=GUARDIANSHIPS
    )

    # image
    if lab.get("image") and not group.header_image:
        need_save = populate_image(lab["image"], group) or need_save

    if lab["leader"]:
        leader = populate_member(lab["leader"], organization)
        if leader:
            group.leaders.add(leader)

            if group.email != leader.email:
                group.email = leader.email
                need_save = True

    if need_save:
        group.save()

    return group


def run(code, file):
    """populate bioconv datas
    argv[1] = orga
    argv[2] = file datas
    """

    organization = Organization.objects.get(code=code)
    orga_group = PeopleGroup.update_or_create_root(organization)
    tags_themes, _ = TagClassification.objects.get_or_create(
        organization=organization,
        type=TagClassification.TagClassificationType.CUSTOM,
        title="Labs Themes",
    )
    tags_guardianships, _ = TagClassification.objects.get_or_create(
        organization=organization,
        type=TagClassification.TagClassificationType.CUSTOM,
        title="Labs Guardianships",
    )
    tags_guardianships.tags.clear()

    res = input(f"Are you sure to import json for {organization!r} ?\n").lower().strip()
    if res not in ["y", "yes"]:
        sys.exit("Exit...")

    with open(file) as f:
        datas = json.load(f)

    for idx, lab in enumerate(datas):
        print(f"{idx}/{len(datas)}")
        if lab is None:
            continue
        parent = populate_lab(
            lab["info"], orga_group, organization, tags_themes, tags_guardianships
        )
        for subidx, sublab in enumerate(lab["subgroups"]):
            print(f"\t{subidx}/{len(lab['subgroups'])}")
            populate_lab(sublab, parent, organization, tags_themes, tags_guardianships)
