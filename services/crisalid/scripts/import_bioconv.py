import json
import mimetypes
import os
from functools import cache
from urllib.parse import urlparse

import requests
from django.core.files.uploadedfile import SimpleUploadedFile
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


@cache
def fetch_image(url):
    try:
        response = requests.get(url, verify=False, timeout=2)
        response.raise_for_status()
        # safe results is a images (for not redirect url)
        if "image" not in response.headers["Content-Type"]:
            return None
        return response.content
    except Exception:
        return None


def populate_member(member: dict, organization: Organization) -> ProjectUser:
    if not member["identifiers"]:
        return None

    identifiers = [
        Identifier.objects.get_or_create(**val)[0] for val in member["identifiers"]
    ]
    researcher, _ = (
        Researcher.objects.from_identifiers(identifiers)
        .select_related("user")
        .update_or_create(
            defaults={
                "given_name": member["first_name"],
                "family_name": member["last_name"],
            }
        )
    )

    user = researcher.user
    if not user:
        user, created = ProjectUser.objects.update_or_create(
            email=member["email"],
            defaults={
                "given_name": member["first_name"],
                "family_name": member["last_name"],
            },
        )
        if not created:
            privacy_settings = user.privacy_settings
            privacy_settings.publication_status = (
                PrivacySettings.PrivacyChoices.ORGANIZATION.value
            )
            privacy_settings.save()

        group_organization = organization.get_users()
        user.groups.add(group_organization)

        researcher.user = user
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
    lab: dict, group: PeopleGroup, tags_classification: TagClassification
):
    tags_title = set((*lab.get("tags", []), *lab.get("keyword", [])))
    exists_tags = list(
        Tag.objects.filter(
            type=Tag.TagType.CUSTOM,
            title__in=tags_title,
            tag_classifications=tags_classification,
        )
    )
    exists_title = [t.title for t in exists_tags]
    updated = False
    for tag_title in tags_title:
        if tag_title not in exists_title:
            tag = Tag(type=Tag.TagType.CUSTOM, title=tag_title)
            tag.save()
            tags_classification.tags.add(tag)
            exists_tags.append(tag)
            updated = True
    if updated:
        group.tags.set(exists_tags)


def populate_image(image_url: str, group: PeopleGroup):
    name = os.path.basename(urlparse(image_url).path)
    content_type, _ = mimetypes.guess_file_type(name)

    if not content_type:
        return

    content = fetch_image(image_url)
    if not content:
        return

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
    tags_classification=TagClassification,
) -> PeopleGroup:
    need_save = False
    title = " - ".join(v for v in (lab["labcode"], lab["title"]) if v)
    group, created = PeopleGroup.objects.update_or_create(
        name=title,
        defaults={
            "short_description": lab.get("short_description", "") or "",
            "description": lab.get("description", "") or "",
            "parent": parent,
            "organization": organization,
        },
    )
    if created:
        group.setup_permissions()

    # location
    if lab["address"]:
        populate_location(lab["address"], group)

    # tags
    populate_tags(lab, group, tags_classification)

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
    tags_classification, _ = TagClassification.objects.get_or_create(
        organization=organization,
        type=TagClassification.TagClassificationType.CUSTOM,
        title="crisalid",
    )

    with open(file) as f:
        datas = json.load(f)

    for idx, lab in enumerate(datas):
        print(f"{idx}/{len(datas)}")
        if lab is None:
            continue
        parent = populate_lab(
            lab["info"], orga_group, organization, tags_classification
        )
        for subidx, sublab in enumerate(lab["subgroups"]):
            print(f"\t{subidx}/{len(lab['subgroups'])}")
            populate_lab(sublab, parent, organization, tags_classification)
