from typing import Any

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from services.crisalid.models import CrisalidConfig


class CrisalidService:
    QUERIES_DIRECTORY = "services/crisalid/queries"

    def __init__(self, config: CrisalidConfig):
        self.transport = RequestsHTTPTransport(
            url=config.apollo_url,
            headers={"X-API-Key": config.apollo_token},
        )
        self.client = Client(
            transport=self.transport, fetch_schema_from_transport=False
        )

    def query(self, query_file: str, **kwargs) -> dict[str, Any]:
        """
        Execute a query from the queries directory.

        Args:
            - query_file (str): The name of the query file.
            - kwargs: The variables to pass to the query.

        Returns:
            - Dict[str, Any]: The query result.
        """
        with open(f"{self.QUERIES_DIRECTORY}/{query_file}.graphql") as f:
            query = f.read()
        return self.client.execute(gql(query), variable_values=kwargs)

    def profiles(
        self, limit: int = 100, offset: int = 0, **kwargs
    ) -> tuple[list[dict[str, Any]], int | None]:
        """
        Get a list of profiles from the Crisalid API.

        Args:
            - limit (int): The number of profiles to return.
            - offset (int): The number of profiles to skip.
            - kwargs: Additional query parameters.

        Returns:
            - Tuple[List[Dict[str, Any]], Optional[int]]: The list of people and the
                next page offset.
        """
        response = self.query("people", limit=limit, offset=offset, **kwargs)
        count = response["peopleAggregate"]["count"]
        next_page = offset + limit if offset + limit < count else None
        return response["people"], next_page

    def profile(self, uid: str) -> dict[str, Any]:
        """
        Get a profile from the Crisalid API.

        Args:
            - uid (str): The UID of the profile.

        Returns:
            - Dict[str, Any]: The profile.
        """
        response = self.query("people", where={"uid_EQ": uid})
        total = response["peopleAggregate"]["count"]
        if total == 0:
            return None
        if total > 1:
            raise ValueError(f"Multiple people found for UID: {uid}")
        return response["people"][0]

    def textual_documents(
        self, limit: int = 100, offset: int = 0, **kwargs
    ) -> tuple[list[dict[str, Any]], int | None]:
        """
        Get a list of textual documents from the Crisalid API.

        Args:
            - limit (int): The number of textual documents to return.
            - offset (int): The number of textual documents to skip.
            - kwargs: Additional query parameters.

        Returns:
            - Tuple[List[Dict[str, Any]], Optional[int]]: The list of textual documents
                and the next page offset.
        """
        response = self.query("textual_documents", limit=limit, offset=offset, **kwargs)
        count = response["textualDocumentsAggregate"]["count"]
        next_page = offset + limit if offset + limit < count else None
        return response["textualDocuments"], next_page

    def textual_document(self, uid: str) -> dict[str, Any]:
        """
        Get a textual document from the Crisalid API.

        Args:
            - uid (str): The UID of the textual document.

        Returns:
            - Dict[str, Any]: The textual document.
        """
        response = self.query("textual_documents", where={"uid_EQ": uid})
        total = response["textualDocumentsAggregate"]["count"]
        if total == 0:
            return None
        if total > 1:
            raise ValueError(f"Multiple textual documents found for UID: {uid}")
        return response["textualDocuments"][0]
