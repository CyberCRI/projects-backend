from collections import defaultdict
from multiprocessing import Value
from django.core.management.base import BaseCommand

from services.crisalid.interface import CrisalidService
import json

from services.crisalid.models import DocumentSource, Document, Identifier, Researcher
import datetime
from functools import cache

class Command(BaseCommand):
    help = "get data from crisalid neo4j/graphql"

    def bulk_update_or_create(self, obj: list, ignore_conflicts=False):
        if not obj:
            return
        
        model = type(obj[0])

        unique_fields = ["crisalid_uid"]

        if model is Researcher:
            update_fields = ["display_name"]
        elif model is Document:
            update_fields = ["title", "publication_date"]
        elif model is DocumentSource:
            update_fields = ["document_type", "value", "harvester", "document"]
        elif model is Identifier:
            update_fields = ["harvester", "value"]
            unique_fields = update_fields

        if ignore_conflicts:
            model.objects.bulk_create(
                obj, ignore_conflicts=True
            )
        else:
            model.objects.bulk_create(
                obj,
                update_conflicts=True,
                unique_fields=unique_fields,
                update_fields=update_fields,
            )
    
    def sanitize_languages(self, values: list[dict[str, str]]) -> str:
        maps_languages = {}

        for value in values:
            maps_languages[value['language']] = value["value"]

        if not maps_languages:
            return ""

        return (
            maps_languages.get("en") or
            maps_languages.get("fr") or
            next(iter(maps_languages.values()))
        )

    def sanitize_date(self, value: str | None) -> datetime.datetime | None:
        FORMAT_DATE = (
            "%Y",
            "%Y-%m",
            "%Y-%m-%d",
        )
        if value is None:
            return 

        for format in FORMAT_DATE:
            try:
                return datetime.datetime.strptime(value, format)
            except (TypeError, ValueError):
                continue
        raise ValueError(f"invalid date {value}")

    @cache
    def cache_model(self, model, **fields):
        try:
            return model.objects.get(**fields)
        except model.DoesNotExist:
            return model(**fields)
    
    def save(self, model, **fields):
        updated = False
        for field, value in fields.items():
            if hasattr(model, field) and getattr(model, field) == value:
                continue
            setattr(model, field, value)
            updated = True
        if updated or not model.pk:
            model.save()

    def handle(self, **opts):
        service = CrisalidService()

        print(Document.objects.all().delete())
        print(DocumentSource.objects.all().delete())
        print(Identifier.objects.all().delete())
        print(Researcher.objects.all().delete())
        
        bulk_document: list[Document] = []
        bulk_document_source: list[DocumentSource] = []
        bulk_identifier: list[Identifier] = []
        bulk_researcher: list[Researcher] = []
        m2m_identifiers : list = []

        offset = 0
        limit = 100
        while True:
            data = service.query("document", offset=offset, limit=limit)["documents"]
            if not data:
                break

            for element in data:
                document = self.cache_model(Document, crisalid_uid=element["uid"])
                self.save(document, 
                    title=self.sanitize_languages(element["titles"]),
                    publication_date=self.sanitize_date(element["publication_date"])
                )

                for recorded in element["recorded_by"]:
                    identifier = self.cache_model(Identifier,
                        value=recorded["uid"],
                        harvester=recorded["harvester"].lower(),
                    )
                    self.save(identifier)

                    doc_sources = self.cache_model(DocumentSource, crisalid_uid=recorded["uid"])
                    self.save(doc_sources,
                        identifier=identifier,
                        document=document,
                        document_type=None,
                    )

                    harvested_for = []
                    for user in recorded["harvested_for"]:
                        researcher = self.cache_model(Researcher, crisalid_uid=user["uid"])
                        self.save(researcher, display_name=user["display_name"])
                        harvested_for.append(researcher)

                        user_identifiers=[]
                        for iden in user["identifiers"]:
                            id_researcher = self.cache_model(Identifier,
                                value=iden["value"],
                                harvester=iden["type"].lower(),
                            )
                            self.save(id_researcher)
                            user_identifiers.append(id_researcher)
                        
                        self.save(researcher)
                        researcher.identifiers.set(user_identifiers)
                    
                    document.authors.set(harvested_for)

            offset += limit
            break

        print("bulk_document=", len(bulk_document))
        print("bulk_document_source=", len(bulk_document_source))
        print("bulk_researcher=", len(bulk_researcher))
        print("bulk_identifier=", len(bulk_identifier))
        print("m2m_identifiers=", len(m2m_identifiers))

        # self.bulk_update_or_create(bulk_identifier, ignore_conflicts=True)
        # self.bulk_update_or_create(bulk_researcher)
        # self.bulk_update_or_create(bulk_document)
        # self.bulk_update_or_create(bulk_document_source)
        # for researcher, identifiers in m2m_identifiers:
        #     researcher.identifiers.set(*identifiers)