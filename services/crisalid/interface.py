from typing import Any, Dict

from django.conf import settings
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport


class CrisalidService:
    QUERIES_DIRECTORY = "services/crisalid/queries"

    def __init__(self):
        self.transport = RequestsHTTPTransport(
            url=f"{settings.CRISALID_API_URL}/graphql",
            headers={"Authorization": settings.CRISALID_API_TOKEN},
        )
        self.client = Client(transport=self.transport, fetch_schema_from_transport=True)

    def query(self, query_file: str, **kwargs) -> Dict[str, Any]:
        with open(f"{self.QUERIES_DIRECTORY}/{query_file}.graphql") as f:
            query = f.read()
        return self.client.execute(gql(query), variable_values=kwargs)

    def people(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        return self.query("people", limit=limit, offset=offset)
