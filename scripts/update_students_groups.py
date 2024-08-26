from django.db.models import Q

from apps.accounts.models import PeopleGroup, ProjectUser
from services.google.tasks import (
    create_google_group,
    update_google_account,
    update_google_group,
)


def update_students_groups(
    new_groups_data, old_groups_data, students_to_update, dry_run=True
):
    """
    TODO : handle students' creation

    Update the students groups in the database.

    * args:
        - new_groups_data: list of dicts with keys 'group_slug' and 'group_email' to create
            the new groups in Google (the groups must exist in Projects).
        - old_groups_data: dict with keys 'old_group_slug' and 'alumni_group_slug' to get the
            students from and add them to the alumni group if needed.
        - students_to_update: list of dicts with keys 'student_email' and 'group_slug' to
            add the student to the new group.

    * example:
        - new_groups_data = [
            {'group_slug': group-1, 'group_email': 'group1@email.com'},
            {'group_slug': group-2, 'group_email': 'group2@email.com'},
        ]
        - old_groups_data = [
            {'old_group_slug': group-3, 'alumni_group_slug': group-4},
            {'old_group_slug': group-5, 'alumni_group_slug': group-6},
        ]
        - students_to_update = [
            {'student_email': user1@email.com, 'group_slug': group-1},
            {'student_email': user2@email.com, 'group_slug': group-2},
        ]
    """
    # Check that user data is correct
    students_to_update_emails = [
        student["student_email"] for student in students_to_update
    ]
    students_to_update = ProjectUser.objects.filter(
        Q(email__in=students_to_update_emails)
        | Q(personal_email__in=students_to_update_emails)
    ).distinct()
    if students_to_update.count() != len(students_to_update_emails):
        if dry_run:
            for s in students_to_update_emails:
                if not ProjectUser.objects.filter(
                    Q(email=s) | Q(personal_email=s)
                ).exists():
                    print(f"User with email {s} does not exist.")
        else:
            raise Exception("Some students do not exist in the database.")

    # Check that group data is correct
    old_groups_slugs = [group["old_group_slug"] for group in old_groups_data]
    alumni_groups_slugs = [group["alumni_group_slug"] for group in old_groups_data]
    new_groups_slugs = [group["group_slug"] for group in new_groups_data]
    all_slugs = old_groups_slugs + alumni_groups_slugs + new_groups_slugs
    all_groups = PeopleGroup.objects.filter(slug__in=all_slugs).distinct()
    if all_groups.count() != len(all_slugs):
        if dry_run:
            for g in all_slugs:
                if not PeopleGroup.objects.filter(slug=g).exists():
                    print(f"Group with slug {g} does not exist.")
        else:
            raise Exception("Some old groups do not exist in the database.")

    # Create the groups in Google
    for group in new_groups_data:
        if dry_run:
            print(
                f"Creating group {group['group_slug']} with email {group['group_email']}"
            )
        else:
            group = PeopleGroup.objects.get(slug=group["group_slug"])
            group.email = group["group_email"]
            group.save()
            create_google_group(group)

    # put the alumni students in the alumni group
    for group in old_groups_data:
        old_group = PeopleGroup.objects.get(slug=group["old_group_slug"])
        alumni_group = PeopleGroup.objects.get(slug=group["alumni_group_slug"])
        for user in old_group.get_all_members():
            if students_to_update.filter(id=user.id).exists():
                if dry_run:
                    print(
                        f"Adding user {user.email} to the alumni group {alumni_group.slug} and to the alumni Google group."
                    )
                else:
                    user.groups.add(alumni_group.get_members())
                    update_google_account(user, "/CRI/Alumni")

    # put the students in the new group
    for student in students_to_update:
        user = (
            ProjectUser.objects.filter(
                Q(email=student["student_email"])
                | Q(personal_email=student["student_email"])
            )
            .distinct()
            .get()
        )
        group = PeopleGroup.objects.get(slug=student["group_slug"])
        if dry_run:
            print(f"Adding user {user.email} to the group {group.slug}")
        else:
            user.groups.add(group.get_members())

    # sync changes with Google
    for slug in all_slugs:
        g = PeopleGroup.objects.get(slug=slug)
        if dry_run:
            print(f"Updating group in Google {g.slug}")
        else:
            update_google_group(g)
