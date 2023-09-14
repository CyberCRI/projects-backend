# Generated by Django 3.2.13 on 2022-05-23 16:43

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import migrations, models
import django.db.models.deletion

from services.keycloak.interface import KeycloakService


BASE_ACTIONS = ("create", "retrieve", "list", "destroy", "update", "partial_update")
ADDITIONAL_ACTIONS = ("image", "member", "group")
SUBSCOPES = (
    "stats:list", "organization-directory", "organization-directory:image", "faq", "faq:image", "project-category",
    "project-category:image", "tag", "project", "project:image", "project:member", "project:duplicate",
    "project-private", "project-org", "goal", "announcement", "follow", "comment", "review", "attachment-link",
    "attachment-file", "blog-entry", "blog-entry:image", "location", "linked-project",
)
MEMBERS_PERMISSIONS = (
    "retrieve", "list", "project-category:retrieve", "project-category:list", "tag:retrieve", "tag:list",
    "project:create", "project:retrieve", "project:list", "project-org:retrieve", "project-org:list",
)


def create_instance_permissions(apps, project, ct):
    Permission = apps.get_model("accounts", "Permission")  # noqa
    permissions = []
    scope = 'organization'
    pk = project.pk

    for action in BASE_ACTIONS:
        permissions.append(Permission(scope=scope, action=action, model=ct, object_pk=pk))

    for action in ADDITIONAL_ACTIONS:
        permissions.append(Permission(scope=scope, action=action, model=ct, object_pk=pk))

    for representation in SUBSCOPES:
        if ":" in representation:
            subscope, action = representation.split(":", maxsplit=1)
            permissions.append(Permission(scope=scope, subscope=subscope, action=action, model=ct, object_pk=pk,))
        else:
            for action in BASE_ACTIONS:
                permission = Permission(scope=scope, subscope=representation, action=action, model=ct, object_pk=pk,)
                permissions.append(permission)

    Permission.objects.bulk_create(permissions, ignore_conflicts=True)


def get_permissions_objects(apps, permissions, organization, ct):
    Permission = apps.get_model("accounts", "Permission")  # noqa
    permission_objects = list()
    for p in permissions:
        if ":" in p:
            subscope, action = p.split(":", maxsplit=1)
            permission_objects.append(Permission.objects.get(
                scope="organization", subscope=subscope, action=action, object_pk=organization.pk, model=ct
            ))
        else:
            if p in BASE_ACTIONS + ADDITIONAL_ACTIONS:
                permission_objects.append(Permission.objects.get(
                    scope="organization", subscope="", action=p, object_pk=organization.pk, model=ct
                ))
            else:
                for action in BASE_ACTIONS:
                    permission_objects.append(Permission.objects.get(
                        scope="organization", subscope=p, action=action, object_pk=organization.pk, model=ct
                    ))

    return set(permission_objects)


def get_default_admins_permissions(apps, organization, ct):
    Permission = apps.get_model("accounts", "Permission")  # noqa
    return Permission.objects.filter(object_pk=str(organization.pk), model=ct)


def get_default_facilitators_permissions(apps, organization, ct):
    filtered_scopes = ["tag", "review", "faq", "project-category", ""]
    Permission = apps.get_model("accounts", "Permission")  # noqa
    organization_permissions = Permission.objects.filter(
        object_pk=str(organization.pk), model=ct
    )
    main_rights = organization_permissions.exclude(
        subscope__in=filtered_scopes
    )
    additional_read_rights = organization_permissions.filter(
        subscope__in=filtered_scopes, action__in=["retrieve", "list"]
    )
    return main_rights | additional_read_rights


def get_default_users_permissions(apps, organization, ct):
    permissions = MEMBERS_PERMISSIONS
    return get_permissions_objects(apps, permissions, organization, ct)


def get_or_import_user(keycloak_id, queryset, project_user) -> dict:
    user = queryset.filter(keycloak_id=keycloak_id)
    if user.exists():
        return user.first()
    keycloak_user = KeycloakService.get_user(keycloak_id)
    people_id = keycloak_user.get("attributes", {}).get("pid", [None])[0]
    if people_id and project_user.objects.filter(people_id=people_id).exists():
        people_id = None
    return project_user.objects.create(
        keycloak_id=keycloak_user.get("id", ""),
        people_id=people_id,
        email=keycloak_user.get("username", ""),
        given_name=keycloak_user.get("firstName", ""),
        family_name=keycloak_user.get("lastName", ""),
    )


def give_organization_rights(apps, schema_editor):
    ContentTypeAlias = apps.get_model("contenttypes", "ContentType")  # noqa
    Group = apps.get_model("accounts", "Group")  # noqa
    ProjectUser = apps.get_model("accounts", "ProjectUser")  # noqa
    Organization = apps.get_model("organizations", "Organization")  # noqa
    OrganizationMember = apps.get_model("organizations", "OrganizationMember")  # noqa

    organizations = Organization.objects.all()

    for count, organization in enumerate(organizations):
        print(f"Importing users from {organization.code} ({count + 1}/{len(organizations)})")
        ct = ContentType.objects.get_for_model(Organization)
        ct_alias = ContentTypeAlias.objects.get(pk=ct.pk)
        create_instance_permissions(apps, organization, ct_alias)

        admins, _ = Group.objects.get_or_create(
            name="admins",
            model=ct_alias,
            object_pk=organization.pk,
        )
        admins.permissions.add(*get_default_admins_permissions(apps, organization, ct_alias))

        facilitators, _ = Group.objects.get_or_create(
            name="facilitators",
            model=ct_alias,
            object_pk=organization.pk,
        )
        facilitators.permissions.add(*get_default_facilitators_permissions(apps, organization, ct_alias))

        users, _ = Group.objects.get_or_create(
            name="users",
            model=ct_alias,
            object_pk=organization.pk,
        )
        users.permissions.add(*get_default_users_permissions(apps, organization, ct_alias))

        keycloak_users = list(set([
            get_or_import_user(user["id"], ProjectUser.objects.all(), ProjectUser)
            for user in KeycloakService.get_members_from_organization(organization.code, "users")
        ]))
        keycloak_admins = list(set([
            get_or_import_user(user["id"], ProjectUser.objects.all(), ProjectUser)
            for user in KeycloakService.get_members_from_organization(organization.code, "administrators")
        ]))

        organization.groups.add(admins, facilitators, users)
        admins.users.add(*keycloak_admins)
        users.users.add(*keycloak_users)
        organization.members.add(*list(set((keycloak_users + keycloak_admins))))


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_auto_20220410_0513'),
        ('organizations', '0018_auto_20220607_0948'),
        ('projects', '0014_auto_20220523_1643')
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='groups',
            field=models.ManyToManyField(related_name='organizations', to='accounts.Group'),
        ),
        migrations.CreateModel(
            name='OrganizationMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='organizations.organization')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='accounts.projectuser', to_field='keycloak_id')),
            ],
            options={
                'unique_together': {('user', 'organization')},
            },
        ),
        migrations.AddField(
            model_name='organization',
            name='members',
            field=models.ManyToManyField(related_name='organizations', through='organizations.OrganizationMember', to='accounts.ProjectUser'),
        ),
        migrations.RunPython(give_organization_rights, migrations.RunPython.noop)
    ]
