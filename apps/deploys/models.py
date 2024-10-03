import logging
from datetime import datetime, timedelta

from celery.result import AsyncResult
from django.conf import settings
from django.db import models
from django.utils.timezone import make_aware

from .task_managers import PostDeployTask

logger = logging.getLogger(__name__)


class PostDeployProcess(models.Model):

    task_name = models.CharField(max_length=100, unique=True)
    priority = models.IntegerField(default=99)
    task_id = models.CharField(max_length=100, blank=True, default="")

    _tasks = {task.task_name: task for task in PostDeployTask.__subclasses__()}

    def __str__(self):
        return self.task_name

    class Meta:
        verbose_name = "Post deploy process"
        verbose_name_plural = "Post deploy processes"
        ordering = ["priority"]

    def run_task(self):
        result = self._tasks[self.task_name].run()
        self.task_id = result.id
        self.save()

    @classmethod
    def recreate_processes(cls):
        if settings.ENVIRONMENT in ["test", "local", "fullstack"]:
            cls._tasks = {
                key: value for key, value in cls._tasks.items() if value.run_in_tests
            }
        for task in cls._tasks.values():
            cls.objects.update_or_create(
                task_name=task.task_name,
                defaults={"priority": task.priority},
            )
        cls.objects.exclude(task_name__in=cls._tasks.keys()).delete()

    @classmethod
    def get_processes_to_run(cls):
        processes = cls.objects.all()
        return [
            process
            for process in processes
            if (
                process.status == "FAILURE"
                or (
                    (
                        not process.last_run
                        or process.last_run
                        < make_aware(datetime.now() - timedelta(minutes=30))
                    )
                    and process.status in ["SUCCESS", "PENDING", "NONE"]
                )
            )
        ]

    @classmethod
    def deploy(cls):
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

    @property
    def progress(self):
        return self._tasks[self.task_name].get_progress(self)

    @property
    def last_run(self):
        if not self.task_id:
            return None
        task_result = AsyncResult(self.task_id)
        date_done = task_result.date_done
        return make_aware(date_done) if date_done else None

    def _status(self):
        if not self.task_id:
            return "NONE"
        task_result = AsyncResult(self.task_id)
        return task_result.status

    @property
    def status(self):
        return self._status()

    @property
    def error(self):
        if not self.task_id:
            return ""
        task_result = AsyncResult(self.task_id)
        traceback = task_result.traceback
        return traceback if traceback else ""
