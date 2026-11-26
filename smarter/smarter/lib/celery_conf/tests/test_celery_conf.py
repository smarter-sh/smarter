"""Tests of the tool worker's task registry, in :mod:`smarter.lib.celery_conf`."""

from unittest import mock

from celery import Celery
from django.apps import apps

from smarter.apps.infrastructure.startup import TOOL_WORKER_CHECKS, WORKER_CHECKS
from smarter.apps.llmtool.tasks import run_tool_call
from smarter.common.conf.settings import Settings
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib.celery_conf import (
    APP,
    TOOL_WORKER_TASK_PACKAGES,
    TOOL_WORKER_TASKS,
    keep_only_tool_worker_tasks,
    restrict_tool_worker_tasks,
    run_worker_startup_checks,
    task_packages,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

OTHER_TASK = "smarter.apps.llmclient.tasks.deploy_default_api.deploy_default_api"
"""A task of another worker's, which the tool worker must never run."""


def in_the_tool_worker():
    """
    Patch the settings so that this process looks like the tool worker, which has no database.

    The settings are frozen, so their class is patched.

    :returns: The patch, as a context manager.
    """
    patch = mock.patch.object(
        Settings, "database_unavailable", new_callable=mock.PropertyMock, return_value=True, create=True
    )
    return patch


def do_nothing() -> None:
    """The body of the throwaway app's tasks."""


def throwaway_app() -> Celery:
    """
    Build a Celery app with the tool worker's task, another worker's, and Celery's own.

    Its tasks aren't shared (``shared=False``), so that they stay out of the platform's app.

    :returns: The app, finalized.
    """
    app = Celery("test_celery_conf", set_as_current=False)
    for name in (TOOL_WORKER_TASKS[0], OTHER_TASK):
        app.task(name=name, shared=False)(do_nothing)
    app.finalize()
    return app


class TestToolWorkerTasks(SmarterTestBase):
    """The tool worker registers only its own task; the other workers register every task."""

    def test_tool_worker_task_is_run_tool_call(self):
        """The allowlist names the task that the app sends, so that a rename can't leave the tool worker idle."""
        self.assertEqual(TOOL_WORKER_TASKS, (run_tool_call.name,))

    def test_keep_only_tool_worker_tasks(self):
        """Another worker's task is removed; the tool worker's and Celery's own are kept."""
        app = throwaway_app()
        builtins = [name for name in app.tasks if name.startswith("celery.")]
        self.assertTrue(builtins)
        removed = keep_only_tool_worker_tasks(app)
        self.assertIn(OTHER_TASK, removed)
        self.assertNotIn(OTHER_TASK, app.tasks)
        self.assertNotIn(TOOL_WORKER_TASKS[0], removed)
        for name in app.tasks:
            kept = name in TOOL_WORKER_TASKS or name.startswith("celery.")
            self.assertTrue(kept, name)
        for name in builtins:
            self.assertIn(name, app.tasks)

    def test_missing_tool_worker_task_is_an_error(self):
        """Without its own task the tool worker would run nothing, so it refuses to start."""
        app = throwaway_app()
        app.tasks.unregister(TOOL_WORKER_TASKS[0])
        with self.assertRaises(SmarterConfigurationError):
            keep_only_tool_worker_tasks(app)

    def test_restrict_only_in_the_tool_worker(self):
        """The signal handler restricts the registry only in a worker without a database."""
        with mock.patch("smarter.lib.celery_conf.keep_only_tool_worker_tasks") as keep_only:
            restrict_tool_worker_tasks()
            keep_only.assert_not_called()
            with in_the_tool_worker():
                restrict_tool_worker_tasks()
            keep_only.assert_called_once_with(APP)

    def test_startup_checks(self):
        """A worker runs the workers' startup checks; the tool worker only its isolation check."""
        with mock.patch("smarter.apps.infrastructure.startup.run_startup_checks") as run:
            run_worker_startup_checks()
            run.assert_called_once_with(WORKER_CHECKS)
            run.reset_mock()
            with in_the_tool_worker():
                run_worker_startup_checks()
            run.assert_called_once_with(TOOL_WORKER_CHECKS)

    def test_task_packages(self):
        """The tool worker discovers only llmtool's tasks; the other workers every installed app's."""
        installed = [config.name for config in apps.get_app_configs()]
        self.assertEqual(task_packages(), installed)
        with in_the_tool_worker():
            self.assertEqual(task_packages(), list(TOOL_WORKER_TASK_PACKAGES))

    def test_platform_app_keeps_every_task(self):
        """Outside the tool worker, the platform's app still has other workers' tasks."""
        self.assertIn(run_tool_call.name, APP.tasks)
        self.assertIn(OTHER_TASK, APP.tasks)
