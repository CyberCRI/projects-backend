from bs4 import BeautifulSoup

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations


def remove_domain(text):
    public_url = settings.PUBLIC_URL
    remove_len = len(public_url)
    soup = BeautifulSoup(text, features="html.parser")
    images = soup.findAll('img')
    for image_tag in images:
        image = image_tag['src']
        if image.startswith(public_url):
            text = text.replace(image, image[remove_len:])
    return text


def remove_domain_and_link_images(blog_entry, apps):
    Image = apps.get_model("files", "Image")
    public_url = settings.PUBLIC_URL
    remove_len = len(public_url)
    text = blog_entry.content
    soup = BeautifulSoup(text, features="html.parser")
    images = soup.findAll('img')
    for image_tag in images:
        image = image_tag['src']
        if image.startswith(public_url):
            image_id = image.split("/")[-1] if image[-1] != "/" else image.split("/")[-2]
            image_object = Image.objects.get(id=image_id)
            if image_object not in blog_entry.images.all():
                blog_entry.images.add(image_object)
                blog_entry.save()
            text = text.replace(image, image[remove_len:])
    return text


def remove_domain_and_update_path(faq):
    try:
        organization = faq.organization
    except ObjectDoesNotExist:
        return faq.content
    public_url = settings.PUBLIC_URL
    remove_len = len(public_url)
    text = faq.content
    soup = BeautifulSoup(text, features="html.parser")
    images = soup.findAll('img')
    for image_tag in images:
        image = image_tag['src']
        if image.startswith(public_url):
            text = text.replace(image, image[remove_len:])
    return text.replace(f"/v1/organization/{organization.id}/faq-image",
                        f"/v1/organization/{organization.code}/faq-image")


def update_urls_in_text(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    projects = apps.get_model("projects", "Project").objects.using(db_alias).all()
    blog_entries = apps.get_model("projects", "BlogEntry").objects.using(db_alias).all()
    templates = apps.get_model("organizations", "Template").objects.using(db_alias).all()
    faqs = apps.get_model("organizations", "Faq").objects.using(db_alias).all()
    comments = apps.get_model("feedbacks", "Comment").objects.using(db_alias).all()
    for project in projects:
        description = project.description
        description = remove_domain(description)
        projects.filter(pk=project.pk).update(description=description)
    for blog_entry in blog_entries:
        content = remove_domain_and_link_images(blog_entry, apps)
        blog_entries.filter(pk=blog_entry.pk).update(content=content)
    for template in templates:
        description_placeholder = template.description_placeholder
        blogentry_placeholder = template.blogentry_placeholder
        description_placeholder = remove_domain(description_placeholder)
        blogentry_placeholder = remove_domain(blogentry_placeholder)
        templates.filter(pk=template.pk).update(blogentry_placeholder=blogentry_placeholder, description_placeholder=description_placeholder)
    for faq in faqs:
        content = remove_domain_and_update_path(faq)
        faqs.filter(pk=faq.pk).update(content=content)
    for comment in comments:
        content = comment.content
        content = remove_domain(content)
        comments.filter(pk=comment.pk).update(content=content)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('files', '0004_alter_image_file'),
        ('projects', '0008_auto_20220512_1840'),
        ('organizations', '0011_default_organization_children'),
        ('feedbacks', '0002_initial')
    ]

    operations = [
        migrations.RunPython(update_urls_in_text, migrations.RunPython.noop),
    ]
