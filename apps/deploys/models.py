import logging
from datetime import timedelta

from celery.result import AsyncResult
from django.conf import settings
from django.core.management import call_command
from django.db import models
from django.db.utils import ProgrammingError
from django.utils import timezone

from .task_managers import PostDeployTask

logger = logging.getLogger(__name__)


class PostDeployProcess(models.Model):
    """
    A model to manage post deploy processes that should be executed after a deploy.
    These processes are defined in the PostDeployTask subclasses.

    The instances of this model are created when the deploy() method is called, they
    should not be created manually.
    """

    class PostDeployProcessStatus(models.TextChoices):
        SUCCESS = "SUCCESS"
        FAILURE = "FAILURE"
        PENDING = "PENDING"
        NONE = ""

    class LocalEnvironments(models.TextChoices):
        LOCAL = "local"
        TEST = "test"

    task_name = models.CharField(max_length=100, unique=True)
    priority = models.IntegerField(default=99)
    task_id = models.CharField(max_length=100, blank=True, default="")
    last_run_version = models.CharField(max_length=255, blank=True, default="")
    last_run = models.DateTimeField(null=True)
    _status = models.CharField(
        max_length=10,
        choices=PostDeployProcessStatus.choices,
        default=PostDeployProcessStatus.NONE,
    )

    _tasks = {task.task_name: task for task in PostDeployTask.__subclasses__()}

    def __str__(self):
        return self.task_name

    class Meta:
        verbose_name = "Post deploy process"
        verbose_name_plural = "Post deploy processes"
        ordering = ["priority"]

    def run_task(self):
        self._status = self.PostDeployProcessStatus.NONE
        self.last_run = timezone.localtime(timezone.now())
        self.save()
        try:
            task = self._tasks[self.task_name]
            if (
                settings.ENVIRONMENT in self.LocalEnvironments.values
                or not task.run_in_celery
            ):
                result = task.run()
            else:
                result = self._tasks[self.task_name].celery_run()
            if result:
                self.task_id = result.id
            else:
                self._status = self.PostDeployProcessStatus.SUCCESS
        except Exception:  # noqa
            self._status = self.PostDeployProcessStatus.FAILURE
        self.last_run_version = settings.VERSION
        self.save()

    @classmethod
    def recreate_processes(cls):
        if settings.ENVIRONMENT in cls.LocalEnvironments.values:
            cls._tasks = {
                key: value for key, value in cls._tasks.items() if value.run_in_tests
            }
        bulk_update_or_create = []
        for task in cls._tasks.values():
            bulk_update_or_create.append(
                cls(task_name=task.task_name, priority=task.priority)
            )

        # when using bulk_create with update_conflicts=True
        # is like when object match the "unique_fields", update the "update_fields"
        # otherwise insert
        cls.objects.bulk_create(
            bulk_update_or_create,
            update_conflicts=True,
            unique_fields=["task_name"],
            update_fields=["priority"],
        )
        cls.objects.exclude(task_name__in=cls._tasks.keys()).delete()

    @classmethod
    def get_processes_to_run(cls):
        processes = cls.objects.all()
        return [
            process
            for process in processes
            if (
                process.status == cls.PostDeployProcessStatus.FAILURE
                or (
                    (
                        not process.last_run
                        or process.last_run
                        < timezone.localtime(
                            timezone.now()
                            - timedelta(
                                minutes=cls._tasks[process.task_name].sleep_time
                            )
                        )
                    )
                    and str(process.last_run_version) != str(settings.VERSION)
                )
            )
        ]

    @classmethod
    def deploy(cls, is_retry: bool = False):
        try:
            cls.recreate_processes()
            processes_to_run = cls.get_processes_to_run()
            processes_names = "".join(
                [f"\n  * {process.task_name}" for process in processes_to_run]
            )
            logger.info(
                f"Running {len(processes_to_run)} post deploy tasks : {processes_names}"
            )
            for process in sorted(processes_to_run, key=lambda x: x.priority):
                process.refresh_from_db()
                process.run_task()
        except ProgrammingError as e:
            if is_retry:
                raise e
            call_command("migrate")
            cls.deploy(is_retry=True)

    @property
    def progress(self):
        return self._tasks[self.task_name].get_progress(self)

    @property
    def status(self):
        if self._status:
            return self._status
        if not self.task_id:
            return self.PostDeployProcessStatus.NONE
        task_result = AsyncResult(self.task_id)
        status = task_result.status
        if status in [
            self.PostDeployProcessStatus.SUCCESS,
            self.PostDeployProcessStatus.FAILURE,
        ]:
            self._status = status
            self.save()
        return status

    @property
    def error(self):
        if not self.task_id:
            return ""
        task_result = AsyncResult(self.task_id)
        traceback = task_result.traceback
        return traceback if traceback else ""
