import itertools
import logging
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Collection,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from algoliasearch.exceptions import AlgoliaException
from algoliasearch_django import AlgoliaIndex as BaseAlgoliaIndex
from algoliasearch_django.models import AlgoliaIndexError
from django.conf import settings as django_settings
from django.db.models import Model, QuerySet

if TYPE_CHECKING:
    from algoliasearch.search_client import SearchClient

logger = logging.getLogger(__name__)

T = TypeVar("T")
B = TypeVar("B", bound="AlgoliaIndex")

DEBUG = django_settings.ALGOLIA.get("RAISE_EXCEPTIONS", django_settings.DEBUG)


def _getattr(obj: object, name: str, default: Any = None) -> Any:
    """Allow to use 'partial()' on 'getattr()'."""
    return getattr(obj, name, default)


class AlgoliaIndex(BaseAlgoliaIndex):
    """An index in the Algolia backend."""

    # Used to specify the fields that should be included in the index.
    fields = None

    # Used to specify the geo-fields that should be used for location search.
    # The attribute should be a callable that returns a tuple.
    geo_field = None

    # Used to specify the field that should be used for filtering by tag.
    tags = None

    # Used to specify the index to target on Algolia.
    index_name = None

    # Used to specify the settings of the index.
    settings = None

    # Suffix used to define function processing a given field before indexation.
    prepare_prefix = "prepare_"

    def __init__(  # noqa
        self, model: Type[Model], client: "SearchClient", settings: Dict[str, Any]
    ):
        self._init_index(client, model, settings)

        self.model = model
        self._client = client
        self._fields = {}

        # Only set settings if the actual index class does not define some
        if self.settings is None:
            self.settings = {}

        self._fields = self._check_fields()

        # Check tags
        if self.tags:
            self.tags = self._get_value_func(self.tags)

        # Check geo_field
        if self.geo_field:
            self.geo_field = self._get_value_func(self.geo_field)

    def _init_index(self, client, model, settings):
        if not self.index_name:
            self.index_name = model.__name__

        tmp_index_name = f"{self.index_name}_tmp"

        if "INDEX_PREFIX" in settings:
            self.index_name = settings["INDEX_PREFIX"] + "_" + self.index_name
            tmp_index_name = f"{settings['INDEX_PREFIX']}_{tmp_index_name}"
        if "INDEX_SUFFIX" in settings:
            self.index_name += "_" + settings["INDEX_SUFFIX"]
            tmp_index_name = f"{tmp_index_name}_{settings['INDEX_SUFFIX']}"

        self.tmp_index_name = tmp_index_name

        self._index = client.init_index(self.index_name)
        self._tmp_index = client.init_index(self.tmp_index_name)

    def _wraps_attr_getter(
        self: B, func: Callable[[Model], T]
    ) -> Callable[[B, Model], T]:
        """Allow any given function to receive an unused first argument.

        Allows a common interface between functions retrieving attributes directly
        on the model and methods of 'AlgoliaIndex'.
        """

        def wrapper(index: B, instance: Model) -> T:  # noqa
            return func(instance)

        return wrapper

    def _get_value_func(self: B, field: str) -> Callable[[B, Model], Any]:
        """Get the function returning the value to index for a given field."""
        prepare_func_name = "{}{}".format(self.prepare_prefix, field)
        func = getattr(self.__class__, prepare_func_name, None)
        attr = getattr(self.model, field, None)

        # '{cls.prepare_prefix}{field}' is defined within the index
        if func is not None:
            if not callable(func):
                raise AlgoliaIndexError(
                    f"'{self.__class__.__name__}.{prepare_func_name}' should be a callable taking an instance of "
                    f"'{self.model}' as argument"
                )
            return func

        # 'field' is a valid attribute of 'model'
        if attr is not None:
            # 'attr' is not callable (such as field), make it a callable using getattr
            if not callable(attr):
                attr = partial(_getattr, name=field)
            return self._wraps_attr_getter(attr)

        raise AlgoliaIndexError(
            f"'{field}' is not an attribute of '{self.model}' and '{self.__class__.__name__}.{prepare_func_name}' "
            f"was not defined"
        )

    def _check_fields(self) -> Dict[str, Callable[[B, Model], T]]:
        """Check 'fields' attribute is correctly set."""
        if self.fields is None:
            raise AlgoliaIndexError(
                "'{}' should include a 'fields' attribute".format(self.__class__)
            )
        if isinstance(self.fields, (list, tuple, set)):
            self.fields = tuple(self.fields)
        else:
            raise AlgoliaIndexError(
                "'{}.fields' must be a list, tuple or set".format(self.__class__)
            )

        # Retrieve the functions returning the value of each field
        fields = {}
        for field in self.fields:
            if not isinstance(field, str):
                raise AlgoliaIndexError(
                    f"field must be str, received: {field} (type: {type(field)})"
                )
            fields[field] = self._get_value_func(field)

        return fields

    def generate_object_id(self, instance: Model) -> Union[str, int]:
        """Generate the objectID from the instance.

        Default behavior is to use the Django object's pk as the objectID.

        If needed, this method can be overloaded to change this default
        behavior.
        """
        return instance.pk

    def should_index(self, instance: Model) -> bool:
        """Return whether this instance should be indexed."""
        return True

    @classmethod
    def _validate_geolocation(cls, geolocation) -> None:
        """Make sure we have the proper geolocation format."""
        if set(geolocation) != {"lat", "lng"}:
            raise AlgoliaIndexError(
                f'Invalid geolocation format, requires "lat" and "lng" keys only got {geolocation}'
            )

    def generate_raw_records(self, instance: Model) -> List[Dict[str, Any]]:
        """Generate the raw record corresponding to 'instance'."""
        record = {"objectID": self.generate_object_id(instance)}

        for key, value in self._fields.items():
            record[key] = value(self, instance)

        if self.geo_field:
            loc = self.geo_field(self, instance)
            if isinstance(loc, tuple):
                record["_geoloc"] = {"lat": loc[0], "lng": loc[1]}
            elif isinstance(loc, dict):
                self._validate_geolocation(loc)
                record["_geoloc"] = loc
            elif isinstance(loc, list):
                [self._validate_geolocation(geo) for geo in loc]
                record["_geoloc"] = loc
            else:
                raise AlgoliaIndexError(
                    f"field must be tuple, list or dict, received: {loc} (type: {type(loc)})"
                )

        if self.tags:
            record["_tags"] = self.tags(self, instance)

        logger.debug("BUILD %s FROM %s", record["objectID"], self.model)
        return [record]

    def save_record(self, instance, **kwargs):
        """Save the record."""
        if not self.should_index(instance):
            # Delete any record that should not be indexed anymore
            self.delete_record(instance)
            return None

        records = []
        try:
            records = self.generate_raw_records(instance)
            return self._index.save_objects(records)
        except AlgoliaException as e:
            if DEBUG:
                raise e
            logger.warning(
                "%s FROM %s NOT SAVED: %s",
                [o["objectID"] for o in records],
                self.model,
                e,
            )
        return None

    def delete_record(self, instance):
        """Delete the record."""
        object_id = self.generate_object_id(instance)
        try:
            self._index.delete_object(object_id)
        except AlgoliaException as e:
            if DEBUG:
                raise e
            logger.warning("%s FROM %s NOT DELETED: %s", object_id, self.model, e)

    def update_records(self, qs, batch_size=1000, **kwargs):
        """
        Update multiple records.

        This method is optimized for speed. It takes a QuerySet and the same
        arguments as QuerySet.update().
        Optionally, you can specify the size of the batch send to Algolia with
        `batch_size` (default to 1000).
        """
        raw_record = {}
        for key, value in kwargs.items():
            if key in self._fields:
                raw_record[key] = value

        batch = []
        for instance in qs:
            raw_record["objectID"] = self.generate_object_id(instance)
            batch.append(dict(raw_record))

            if len(batch) >= batch_size:
                self._index.partial_update_objects(batch)
                batch = []

        if len(batch) > 0:
            self._index.partial_update_objects(batch)

    def raw_search(self, query="", params=None):
        """Perform a search query and returns the parsed JSON."""
        if params is None:
            params = {}

        try:
            return self._index.search(query, params)
        except AlgoliaException as e:
            if DEBUG:
                raise e
            logger.warning("ERROR DURING SEARCH ON %s: %s", self.index_name, e)

    def get_settings(self):
        """Return the settings of the index."""
        try:
            logger.info("GET SETTINGS ON %s", self.index_name)
            return self._index.get_settings()
        except AlgoliaException as e:
            if DEBUG:
                raise e
            logger.warning("ERROR DURING GET_SETTINGS ON %s: %s", self.model, e)

    def set_settings(self):
        """Apply the settings to the index."""
        if not self.settings:
            return

        try:
            self._index.set_settings(self.settings)
            logger.info("APPLY SETTINGS ON %s", self.index_name)
        except AlgoliaException as e:
            if DEBUG:
                raise e
            logger.warning("SETTINGS NOT APPLIED ON %s: %s", self.model, e)

    def clear_objects(self):
        """Clear all objects of an index."""
        try:
            self._index.clear_objects()
            logger.info("CLEAR INDEX %s", self.index_name)
        except AlgoliaException as e:
            if DEBUG:
                raise e
            logger.warning("%s NOT CLEARED: %s", self.model, e)

    def wait_task(self, task_id):
        """Wait the Algolia's task corresponding to `task_id`."""
        try:
            self._index.wait_task(task_id)
            logger.info("WAIT TASK %s", self.index_name)
        except AlgoliaException as e:
            if DEBUG:
                raise e
            logger.warning("%s NOT WAIT: %s", self.model, e)

    def delete(self):
        """Delete the index."""
        self._index.delete()
        if self._tmp_index:
            self._tmp_index.delete()

    def get_indexing_queryset(self) -> QuerySet:
        """Queryset used when reindexing all records.

        You can override this method if you want to use a custom Queryset to
        retrieve the instances to be indexed.

        This can be used to improve performance using `select_related()` and
        `prefetch_related()` according to the fields you want to index.
        """
        return self.model.objects.all()

    def reindex_all(self, batch_size=1000):
        """Reindex all the records."""
        should_keep_synonyms = False
        should_keep_rules = False
        try:
            if not self.settings:
                self.settings = self.get_settings()
                logger.debug(
                    "Got settings for index %s: %s", self.index_name, self.settings
                )
            else:
                logger.debug(
                    "index %s already has settings: %s", self.index_name, self.settings
                )
        except AlgoliaException as e:
            if any("Index does not exist" in arg for arg in e.args):
                pass  # Expected, let's clear and recreate from scratch
            else:
                raise e  # Unexpected error while getting settings

        settings = self.settings or {}
        replicas = settings.get("replicas", None)
        slaves = settings.get("slaves", None)
        should_keep_replicas = replicas is not None
        should_keep_slaves = slaves is not None

        try:
            if should_keep_replicas:
                self.settings["replicas"] = []
                logger.debug("REMOVE REPLICAS FROM SETTINGS")
            if should_keep_slaves:
                self.settings["slaves"] = []
                logger.debug("REMOVE SLAVES FROM SETTINGS")

                self._tmp_index.set_settings(self.settings).wait()
                logger.debug("APPLY SETTINGS ON %s_tmp", self.index_name)
            rules = []
            synonyms = []
            for r in self._index.browse_rules():
                rules.append(r)
            for s in self._index.browse_synonyms():
                synonyms.append(s)
            if rules:
                logger.debug("Got rules for index %s: %s", self.index_name, rules)
                should_keep_rules = True
            if synonyms:
                logger.debug("Got synonyms for index %s: %s", self.index_name, rules)
                should_keep_synonyms = True

            self._tmp_index.clear_objects()
            logger.debug("CLEAR INDEX %s_tmp", self.index_name)

            counts = 0
            batch = []

            qs = self.get_indexing_queryset()

            for instance in qs:
                if not self.should_index(instance):
                    continue  # should not index
                batch += self.generate_raw_records(instance)
                if len(batch) >= batch_size:
                    self._tmp_index.save_objects(batch)
                    logger.info(
                        "SAVE %d OBJECTS TO %s_tmp", len(batch), self.index_name
                    )
                    batch = []
                counts += 1
            if len(batch) > 0:
                self._tmp_index.save_objects(batch)
                logger.info("SAVE %d OBJECTS TO %s_tmp", len(batch), self.index_name)

            self._client.move_index(self.tmp_index_name, self.index_name)
            logger.info("MOVE INDEX %s_tmp TO %s", self.index_name, self.index_name)

            if self.settings:
                if should_keep_replicas:
                    self.settings["replicas"] = replicas
                    logger.debug("RESTORE REPLICAS")
                if should_keep_slaves:
                    self.settings["slaves"] = slaves
                    logger.debug("RESTORE SLAVES")
                if should_keep_replicas or should_keep_slaves:
                    self._index.set_settings(self.settings)
                if should_keep_rules:
                    response = self._index.save_rules(
                        rules, {"forwardToReplicas": True}
                    )
                    response.wait()
                    logger.info(
                        "Saved rules for index %s with response: {}".format(response),
                        self.index_name,
                    )
                if should_keep_synonyms:
                    response = self._index.save_synonyms(
                        synonyms, {"forwardToReplicas": True}
                    )
                    response.wait()
                    logger.info(
                        "Saved synonyms for index %s with response: {}".format(
                            response
                        ),
                        self.index_name,
                    )
            self._index.set_settings(self.settings)
            return counts
        except AlgoliaException as e:
            if DEBUG:
                raise e
            logger.warning("ERROR DURING REINDEXING %s: %s", self.model, e)


class AlgoliaSplittingIndex(AlgoliaIndex):
    """An index in the Algolia backend allowing to split large records.

    With this class, 'fields' must be a dictionary specifying how the record
    must be split. It should contain a 'multiple' key containing list of
    dictionaries indicating which fields must be split to create each record and
    which fields are common to each record.

    For instance to index a Wikipedia page by splitting the page in multiple
    sections, as explained on
    https://www.algolia.com/doc/guides/sending-and-managing-data/prepare-your-data/how-to/indexing-long-documents/,
    we could define 'fields' as follow :
    {
      "multiple": [
        {
          "id_suffix": "sec",
          "split": ["content", "section"]
          "commons": ["id", "title", "permalink"]
        }
      ]
    }

    Each field within a 'split' key must define a '{split_suffix}{field}'
    method returning a collection of value. If not every split method of a
    same 'split' list return a collection of the same size,
    'split_fill_value' will be used to fill missing value (same behaviour as
    'itertools.zip_longest').

    'id_suffix' is used to make the 'objectID' unique for each record. The
    `objectID` is defined as follows :
        * '{generate_object_id()}-{id_suffix}-{n}'
    Where 'n' is the record number.

    A 'unique' key can optionally be defined at the same level of 'multiple'
    to define fields which should be indexed only one time in their own
    records.

    Continuing on the Wikipedia example, we could want to index the page's
    metadata (date, author, id, ...), but only in one record, we can do that
    using 'unique' :

    '''
    fields = {
      "unique": {"id", "date", "author", "id", ...}
      "multiple": [
        {
          "id_suffix": "sec",
          "split": ["content", "section"]
          "commons": ["id", "title", "permalink"]
        }
      ]
    }
    '''

    You may now define the 'attributeForDistinct' to 'id' to retrieve the
    corresponding page if any of the record matched.
    """

    fields = None

    # Suffix used to define function splitting a given field
    split_suffix = "split_"

    # Value used to fill missing value when all split fields within a 'multiple'
    # have different length
    split_fill_value = None

    def _get_split_func(
        self: B, field: str
    ) -> Optional[Callable[[B, Model], Collection[str]]]:
        """Return the method used to split."""
        split_func_name = f"{self.split_suffix}{field}"
        func = getattr(self.__class__, split_func_name, None)

        if func is None:
            raise AlgoliaIndexError(
                f"'{self.__class__.__name__}' must declare a '{split_func_name}' method taking an instance of "
                f"'{self.model}' as argument"
            )

        if not callable(func):
            raise AlgoliaIndexError(
                f"'{self.__class__.__name__}.{split_func_name}' should be a method taking an instance of "
                f"'{self.model}' as argument"
            )

        return func

    def _check_fields(self) -> Dict[str, Callable[[B, Model], T]]:
        """Check 'fields' attribute is correctly set."""
        if not isinstance(self.fields, dict):
            raise AlgoliaIndexError("'{}.fields' must be a dict".format(self.__class__))
        if self.fields is None:
            raise AlgoliaIndexError(
                "'{}' should include a 'fields' attribute".format(self.__class__)
            )

        simple_field = set()
        fields = {}

        # Check unique fields
        for field in self.fields.get("unique", ()):
            if not isinstance(field, str):
                raise AlgoliaIndexError(
                    "'{}.fields['unique']' must only contain str".format(self.__class__)
                )
            fields[field] = self._get_value_func(field)
            simple_field.add(field)

        # Check multiple fields
        for i, multiple in enumerate(self.fields.get("multiple", ())):
            if not isinstance(multiple, dict):
                raise AlgoliaIndexError(
                    "'{}.fields['multiple']' must only contain dict".format(
                        self.__class__
                    )
                )

            # Check multiple's commons field
            for field in multiple.get("commons", ()):
                if not isinstance(field, str):
                    raise AlgoliaIndexError(
                        f"'{self.__class__}.fields['multiple'][{i}]['commons']' must only contain str"
                    )
                if field not in self.fields:
                    fields[field] = self._get_value_func(field)
                    simple_field.add(field)

            # Check multiple's split fields
            for field in multiple.get("split", ()):
                if not isinstance(field, str):
                    raise AlgoliaIndexError(
                        f"'{self.__class__}.fields['multiple'][{i}]['split']' must only contain str"
                    )
                if field not in self.fields:
                    fields[field] = self._get_split_func(field)
                if field in simple_field:
                    raise AlgoliaIndexError(
                        f"'{field}' was present in both a 'unique'/'commons' list and a 'split' list"
                    )

        return fields

    def _wrap_split_func(
        self, field: str, collection: Collection[Any]
    ) -> Collection[Tuple[str, Any]]:
        """Yield the field name alongside each element of the collection."""
        collection = list(collection)
        for element in collection:
            yield field, element

    def generate_raw_records(self, instance: Model) -> List[Dict[str, Any]]:
        """Generate the raw record corresponding to 'instance'."""
        object_id = str(self.generate_object_id(instance))
        records = []

        # Add a record for unique fields
        if "unique" in self.fields:
            record = {"objectID": object_id}
            for field in self.fields["unique"]:
                record[field] = self._fields[field](self, instance)
            records.append(record)

        # Create a multiple record for each 'multiple'
        for m in self.fields.get("multiple", ()):
            # Retrieve common values
            commons = {}
            for field in m["commons"]:
                commons[field] = self._fields[field](self, instance)

            # Add records with common + split values
            collections = [
                self._wrap_split_func(field, self._fields[field](self, instance))
                for field in m["split"]
            ]
            for i, splits in enumerate(itertools.zip_longest(*collections)):
                records.append(
                    {
                        **commons,
                        **{"objectID": f"{object_id}-{m['id_suffix']}-{i}"},
                        **{field: element for field, element in splits},
                    }
                )

        loc = None
        if self.geo_field:
            loc = self.geo_field(self, instance)

        tags = None
        if self.tags:
            tags = self.tags(self, instance)

        if loc is not None or tags is not None:
            for record in records:
                if loc:
                    record["_geoloc"] = loc
                if tags:
                    record["_tags"] = tags

        logger.debug("BUILD %s FROM %s", [r["objectID"] for r in records], self.model)
        return records

    def delete_record(self, instance):
        """Delete the record."""
        objects_ids = [
            record["objectID"] for record in self.generate_raw_records(instance)
        ]
        for object_id in objects_ids:
            try:
                self._index.delete_object(object_id)
            except AlgoliaException as e:
                if DEBUG:
                    raise e
                logger.warning("%s FROM %s NOT DELETED: %s", object_id, self.model, e)
