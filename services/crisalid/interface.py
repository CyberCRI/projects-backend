import re
from typing import Any

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from services.crisalid.models import CrisalidConfig


class CrisalidService:
    QUERIES_DIRECTORY = "services/crisalid/queries"
    # nodes fragments used in a query file: #import "nodes/structure.graphql"
    IMPORT_PATTERN = re.compile(r'^#import "(.+)"$', re.MULTILINE)

    def __init__(self, config: CrisalidConfig):
        self.transport = RequestsHTTPTransport(
            url=config.apollo_url, headers={"X-API-Key": config.apollo_token}
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
        fragments = []
        for path in self.IMPORT_PATTERN.findall(query):
            with open(f"{self.QUERIES_DIRECTORY}/{path}") as f:
                fragments.append(f.read())
        return self.client.execute(
            gql("\n".join([query, *fragments])), variable_values=kwargs
        )

    def journals(
        self, limit: int = 100, offset: int = 0, **kwargs
    ) -> tuple[list[dict[str, Any]], int | None]:
        """
        Get a list of journals from the Crisalid API.

        Returns:
            - Tuple[List[Dict[str, Any]], int | None]: The list of journals and the
                next page offset.
        """
        response = self.query("journals", limit=limit, offset=offset, **kwargs)
        count = response["journalsAggregate"]["count"]
        next_page = offset + limit if offset + limit < count else None
        return response["journals"], next_page

    def organizations(
        self, limit: int = 100, offset: int = 0, **kwargs
    ) -> tuple[list[dict[str, Any]], int | None]:
        """
        Get a list of authority organizations (documents affiliations) from the Crisalid API.

        Returns:
            - Tuple[List[Dict[str, Any]], int | None]: The list of authority
                organizations and the next page offset.
        """
        response = self.query("organizations", limit=limit, offset=offset, **kwargs)
        count = response["organizationsAggregate"]["count"]
        next_page = offset + limit if offset + limit < count else None
        return response["organizations"], next_page

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
            - Tuple[List[Dict[str, Any]], int | None]: The list of people and the
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

    def documents(
        self, limit: int = 100, offset: int = 0, **kwargs
    ) -> tuple[list[dict[str, Any]], int | None]:
        """
        Get a list of documents from the Crisalid API.

        Args:
            - limit (int): The number of documents to return.
            - offset (int): The number of documents to skip.
            - kwargs: Additional query parameters.

        Returns:
            - Tuple[List[Dict[str, Any]], int | None]: The list of documents and the
                next page offset.
        """
        response = self.query("documents", limit=limit, offset=offset, **kwargs)
        count = response["documentsAggregate"]["count"]
        next_page = offset + limit if offset + limit < count else None
        return response["documents"], next_page

    def document(self, uid: str) -> dict[str, Any]:
        """
        Get a document from the Crisalid API.

        Args:
            - uid (str): The UID of the document.

        Returns:
            - Dict[str, Any]: The document.
        """
        response = self.query("documents", where={"uid_EQ": uid})
        total = response["documentsAggregate"]["count"]
        if total == 0:
            return None
        if total > 1:
            raise ValueError(f"Multiple documents found for UID: {uid}")
        return response["documents"][0]

    def structures(
        self, limit: int = 100, offset: int = 0, **kwargs
    ) -> tuple[list[dict[str, Any]], int | None]:
        """
        Get a list of structures from the Crisalid API.

        Args:
            - limit (int): The number of structures to return.
            - offset (int): The number of structures to skip.
            - kwargs: Additional query parameters.

        Returns:
            - Tuple[List[Dict[str, Any]], int | None]: The list of structures and the
                next page offset.
        """
        response = self.query("structures", limit=limit, offset=offset, **kwargs)
        count = response["structuresAggregate"]["count"]
        next_page = offset + limit if offset + limit < count else None
        return response["structures"], next_page

    def structure(self, uid: str) -> dict[str, Any]:
        """
        Get a structure from the Crisalid API.

        Args:
            - uid (str): The UID of the structure.

        Returns:
            - Dict[str, Any]: The structure.
        """
        response = self.query("structures", where={"uid_EQ": uid})
        total = response["structuresAggregate"]["count"]
        if total == 0:
            return None
        if total > 1:
            raise ValueError(f"Multiple structures found for UID: {uid}")
        return response["structures"][0]
