import logging
from collections import defaultdict
from collections.abc import Callable
from functools import wraps

from celery import Task

from services.crisalid.bus.constant import CrisalidEventEnum, CrisalidTypeEnum

logger = logging.getLogger(__name__)


class CrisalidConsumer:
    """class to register callback on rabitmqt event"""

    def __init__(self):
        # initial cosumer dict
        self.clean()

    def clean(self):
        """remove all registered callback"""
        self._consumers: dict[CrisalidTypeEnum, dict[CrisalidEventEnum, Callable]] = (
            defaultdict(lambda: defaultdict(lambda: None))
        )

    def add_callback(
        self,
        crisalid_type: CrisalidTypeEnum,
        crisalid_event: CrisalidEventEnum,
        callback: Callable,
    ):
        assert (
            crisalid_event.value not in self._consumers[crisalid_type.value]
        ), f"Event {crisalid_type}::{crisalid_event}, is already set"

        # add callback
        self._consumers[crisalid_type.value][crisalid_event.value] = callback
        return callback

    def __getitem__(self, key):
        return self._consumers[key]


crisalid_consumer = CrisalidConsumer()


# check methods is celery
def is_task_celery(func):
    return isinstance(func, Task) or (
        hasattr(func, "__wrapped__") and isinstance(func.__wrapped__, Task)
    )


# easy decorator method
def on_event(crisalid_type: CrisalidTypeEnum, crisalid_event: CrisalidEventEnum):
    """shortcut decorator to crisalid_bus.add_callback

    :param crisalid_type: crisalid type name
    :param crisalid_event: crisalid event name
    """

    def _wraps(func):
        original_func = func
        if is_task_celery(func):

            # if is a task, add correct seriliazer for data
            @wraps(func)
            def _tasks(*args):
                logger.info("post task celery %s", original_func)
                return original_func.apply_async(args)

            func = _tasks
        crisalid_consumer.add_callback(crisalid_type, crisalid_event, func)
        return original_func

    return _wraps
