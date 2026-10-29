import math

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.accounts.models import PeopleGroup
from services.crisalid.interface import CrisalidService
from services.crisalid.models import (
    AuthorityOrganization,
    CrisalidConfig,
    Document,
    DocumentContributor,
    Identifier,
    Journal,
    Researcher,
    Structure,
)
from services.crisalid.populates import (
    PopulateAuthorityOrganization,
    PopulateDocument,
    PopulateJournal,
    PopulateResearcher,
    PopulateStructure,
)
from services.crisalid.populates.base import AbstractPopulate
from services.crisalid.utils.timer import timeit
from services.mistral.models import DocumentEmbedding


class Command(BaseCommand):
    help = (  # noqa: A003
        "create or update data from researcher/Document crisalid neo4j/graphql"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "organization",
            choices=CrisalidConfig.objects.filter(
                organization__code__isnull=False, active=True
            ).values_list("organization__code", flat=True),
            help="organization code",
        )
        parser.add_argument(
            "command",
            choices=(
                "organization",
                "journal",
                "structure",
                "researcher",
                "document",
                "all",
            ),
            help="elements to populate",
        )
        parser.add_argument(
            "--delete",
            help="delete all crisalid models",
            default=False,
            action="store_true",
        )
        parser.add_argument("--offset", help="offset for graphql", default=0)
        parser.add_argument("--limit", help="limit for graphql", default=100)
        parser.add_argument("--max", help="max loop for graphql", default=math.inf)

    def delete_crisalid_models(self, config: CrisalidConfig, command: str):
        """delete crisalid models of the organization, cascades only delete crisalid
        objects (relations, embeddings) and the structures groups
        """
        organization = config.organization
        documents = Document.objects.filter(
            contributors__user__groups__organizations=organization
        )
        researchers = Researcher.objects.filter(
            user__groups__organizations=organization
        )
        structures = Structure.objects.filter(organization=organization)
        organizations = AuthorityOrganization.objects.filter(documents__in=documents)
        identifiers = Identifier.objects.filter(
            Q(documents__in=documents)
            | Q(researchers__in=researchers)
            | Q(structures__in=structures)
            | Q(authority_organizations__in=organizations)
        )

        # reverse order of the import (dependent objects first)
        querysets = []
        if command in ("all", "document"):
            querysets.extend(
                (
                    DocumentEmbedding.objects.filter(item__in=documents),
                    DocumentContributor.objects.filter(document__in=documents),
                    documents,
                )
            )

        if command in ("all", "researcher"):
            # users linked to researchers are kept
            querysets.append(researchers)

        if command in ("all", "structure"):
            # groups would be duplicated on next import (structure.people_group is SET_NULL),
            # their children groups are kept
            querysets.extend(
                (PeopleGroup.objects.filter(structure__in=structures), structures)
            )

        if command in ("all", "journal"):
            querysets.append(Journal.objects.filter(documents__in=documents))

        if command in ("all", "organization"):
            querysets.append(organizations)

        if command in ("all",):
            querysets.append(identifiers)

        # filters use relations removed by previous deletions: get all pks first
        to_delete = [
            (queryset.model, list(queryset.values_list("pk", flat=True).distinct()))
            for queryset in querysets
        ]
        for model, pks in to_delete:
            deleted = model.objects.filter(pk__in=pks).delete()
            print(f"deleted {model=}: {deleted=}")

    def populate_crisalid(
        self,
        service: CrisalidService,
        populate: AbstractPopulate,
        query: str,
        where: None = None,
        **options,
    ):
        offset = int(options["offset"])
        limit = int(options["limit"])
        max_elements = float(options["max"])
        total = 0

        with timeit(print, f"Populate All Data from '{query}'"):
            while max_elements >= 1:
                with timeit(print, f"GrapQL request {query}"):
                    data = service.query(
                        query, offset=offset, limit=limit, where=where
                    )[query]
                    if not data:
                        break

                with timeit(print, "Populate data"):
                    populate.multiple(data)

                total += len(data)
                print(f"{total} done...")

                offset += limit
                max_elements -= 1

    def handle(self, **options):
        config = CrisalidConfig.objects.get(organization__code=options["organization"])
        command = options["command"]
        if options["delete"]:
            self.delete_crisalid_models(config, command)
            return

        service = CrisalidService(config)

        # missing related objects are created by each populate (node only),
        # this order avoids creating them before their own import
        if command in ("all", "organization"):
            populate = PopulateAuthorityOrganization(config)
            self.populate_crisalid(service, populate, query="organizations", **options)

        if command in ("all", "journal"):
            populate = PopulateJournal(config)
            self.populate_crisalid(service, populate, query="journals", **options)

        if command in ("all", "structure"):
            populate = PopulateStructure(config)
            self.populate_crisalid(service, populate, query="structures", **options)

        if command in ("all", "researcher"):
            populate = PopulateResearcher(config)
            self.populate_crisalid(
                service,
                populate,
                query="people",
                # populate only local researcher
                where={"external_EQ": False},
                **options,
            )

        if command in ("all", "document"):
            populate = PopulateDocument(config)
            self.populate_crisalid(service, populate, query="documents", **options)
