from typing import List, Union

from apps.search.models import SearchObject
from apps.skills.models import Tag


class MockedTagHit:
    def __init__(self, tag: Tag, query: str):
        self.id = tag.id
        fields = {
            field: getattr(tag, field, "")
            for field in ["name_fr", "name_en", "description_fr", "description_en"]
        }
        self.highlight = {
            key: value.replace(query, f"<em>{query}</em>")
            for key, value in fields.items()
            if query in value
        }


class MockedSearchObjectHit:
    def __init__(self, search_object: SearchObject, query: str):
        self.search_object_id = search_object.id
        fields = {field: getattr(search_object, field, "") for field in []}
        self.highlight = {
            key: value.replace(query, f"<em>{query}</em>")
            for key, value in fields.items()
            if query in value
        }


class MockedResponse:
    def __init__(self, hits: List[Union[MockedSearchObjectHit, MockedTagHit]]):
        self.hits = hits


class SearchTestCaseMixin:
    def opensearch_tags_mocked_return(self, tags: List[Tag]) -> List[MockedTagHit]:
        hits = [MockedTagHit(tag=tag, query="") for tag in tags]
        return MockedResponse(hits=hits)

    def opensearch_search_objects_mocked_return(
        self, search_objects: List[SearchObject]
    ) -> List[MockedSearchObjectHit]:
        hits = [
            MockedSearchObjectHit(search_object=search_object, query="")
            for search_object in search_objects
        ]
        return MockedResponse(hits=hits)
