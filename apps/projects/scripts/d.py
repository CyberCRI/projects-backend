import time
from pprint import pprint

from django.db import connection
from django.db.models import Count, OuterRef, Subquery

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.projects.models import Project


class Query:
    base = 0
    time = 0

    def __enter__(self):
        self.base = len(connection.queries)
        self.time = time.monotonic_ns()
        return self

    def __exit__(self, *ar, **kw):
        diff = len(connection.queries) - self.base
        diff_time = time.monotonic_ns() - self.time

        print(f"number query db: {diff}")
        print(f"time: {diff_time:,}ns")


def run():
    # p = Project.objects.get(id="i3nXMhG3")
    # print(p)

    # print("----[new]----")
    # with Query():
    #     pprint(p.modules.annotate(), indent=4)

    # print()

    # print("----[old]----")
    # with Query():
    #     pprint(p.modules.count(), indent=4)

    user = ProjectUser.objects.first()

    model = PeopleGroup

    print("model count=", model.objects.count())

    with Query():
        r = model.objects.all().annotate_modules(user, outout_key="annotate_modules")
        with open("dd.sql", "w") as f:
            f.write(str(r.query))
        for p2 in r:
            an = p2.annotate_modules
            # print(an, p2.similars().count())

    with Query():
        r = model.objects.all()
        for p2 in r:
            p2.modules.count()
