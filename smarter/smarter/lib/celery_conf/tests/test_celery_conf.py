"""Tests of each worker's task registry, in :mod:`smarter.lib.celery_conf`."""

from unittest import mock

from celery import Celery
from celery.exceptions import NotRegistered
from django.apps import apps

from smarter.apps.infrastructure.startup import TOOL_WORKER_CHECKS, WORKER_CHECKS
from smarter.apps.llmtool.tasks import run_tool_call
from smarter.common.conf import smarter_settings
from smarter.common.conf.settings import Settings
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib.celery_conf import (
    APP,
    CELERY_BUILTIN_TASK_PREFIX,
    TOOL_WORKER_TASK_PACKAGES,
    TOOL_WORKER_TASKS,
    configure_tool_worker,
    consumed_queue_names,
    keep_only_queue_tasks,
    keep_only_tasks,
    keep_only_tool_worker_tasks,
    queue_task_names,
    restrict_worker_tasks,
    run_worker_startup_checks,
    task_packages,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

OTHER_TASK = "smarter.apps.llmclient.tasks.deploy_default_api.deploy_default_api"
"""A task of another worker's, which the tool worker must never run: an infrastructure task."""

OPERATIONAL_TASK = "smarter.apps.prompt.tasks.create_prompt_history"
"""A task of the operational queue's, which the infrastructure worker must never run."""

OPERATIONAL_QUEUE = "default_celery_task_queue"
INFRASTRUCTURE_QUEUE = "infrastructure_celery_task_queue"
TOOLS_QUEUE = "tools_celery_task_queue"

THROWAWAY_TASK_QUEUES = {
    TOOL_WORKER_TASKS[0]: TOOLS_QUEUE,
    OTHER_TASK: INFRASTRUCTURE_QUEUE,
    OPERATIONAL_TASK: OPERATIONAL_QUEUE,
}
"""The throwaway app's tasks, and the queue each declares, as the platform's do."""


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


def throwaway_app(consumed_queues: tuple[str, ...] = ()) -> Celery:
    """
    Build a Celery app with a task of each queue's, as the platform's declare them, and Celery's own.

    Its tasks aren't shared (``shared=False``), so that they stay out of the platform's app.

    :param consumed_queues: The queues that the app's worker consumes, as ``-Q`` selects them. Empty: the
        app's default queue, as a worker started without ``-Q``.
    :returns: The app, finalized.
    """
    app = Celery("test_celery_conf", set_as_current=False)
    for name, queue in THROWAWAY_TASK_QUEUES.items():
        app.task(name=name, queue=queue, shared=False)(do_nothing)
    app.finalize()
    # finalizing adds every shared task, e.g. the platform's: leave only the app's own, and Celery's.
    keep_only_tasks(app, list(THROWAWAY_TASK_QUEUES))
    if consumed_queues:
        # what the worker does with -Q, before it sends worker_init.
        app.amqp.queues.select(list(consumed_queues))
    return app


def platform_task_names(app: Celery) -> list[str]:
    """
    Name the app's tasks that aren't Celery's own.

    :param app: The Celery app.
    :returns: The tasks' names, sorted.
    """
    names = []
    for name in sorted(app.tasks.keys()):
        if not name.startswith(CELERY_BUILTIN_TASK_PREFIX):
            names.append(name)
    return names


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

    def test_restrict_in_the_tool_worker(self):
        """A worker without a database keeps the tool worker's list, not its queue's tasks."""
        with (
            mock.patch("smarter.lib.celery_conf.keep_only_tool_worker_tasks") as keep_only_tools,
            mock.patch("smarter.lib.celery_conf.keep_only_queue_tasks") as keep_only_queue,
            in_the_tool_worker(),
        ):
            restrict_worker_tasks()
        keep_only_tools.assert_called_once_with(APP)
        keep_only_queue.assert_not_called()

    def test_restrict_in_the_other_workers(self):
        """A worker with a database keeps its queues' tasks, and logs how many."""
        with (
            mock.patch("smarter.lib.celery_conf.keep_only_tool_worker_tasks") as keep_only_tools,
            mock.patch("smarter.lib.celery_conf.keep_only_queue_tasks", return_value=[OTHER_TASK]) as keep_only_queue,
            mock.patch("smarter.lib.celery_conf.consumed_queue_names", return_value=[OPERATIONAL_QUEUE]),
            mock.patch("smarter.lib.celery_conf.queue_task_names", return_value=[OPERATIONAL_TASK]),
            self.assertLogs("smarter.lib.celery_conf", level="INFO") as logs,
        ):
            restrict_worker_tasks()
        keep_only_queue.assert_called_once_with(APP)
        keep_only_tools.assert_not_called()
        self.assertIn(f"runs only the 1 tasks of {OPERATIONAL_QUEUE}", logs.output[0])
        self.assertIn("1 other tasks are unregistered", logs.output[0])


class TestQueueTasks(SmarterTestBase):
    """Each worker with a database registers only its own queues' tasks (ADR-030, rule 6)."""

    def test_consumed_queue_names(self):
        """The queues are the worker's -Q; without it, the app's default queue."""
        app = throwaway_app((INFRASTRUCTURE_QUEUE,))
        self.assertEqual(consumed_queue_names(app), [INFRASTRUCTURE_QUEUE])
        app = throwaway_app()
        self.assertEqual(consumed_queue_names(app), [app.conf.task_default_queue])

    def test_queue_task_names(self):
        app = throwaway_app()
        self.assertEqual(queue_task_names(app, [OPERATIONAL_QUEUE]), [OPERATIONAL_TASK])
        self.assertEqual(queue_task_names(app, [INFRASTRUCTURE_QUEUE]), [OTHER_TASK])
        both = queue_task_names(app, [OPERATIONAL_QUEUE, INFRASTRUCTURE_QUEUE])
        self.assertEqual(both, sorted([OPERATIONAL_TASK, OTHER_TASK]))

    def test_a_task_without_a_queue_is_the_default_queues(self):
        app = throwaway_app()
        app.task(name="smarter.apps.example.tasks.undeclared", shared=False)(do_nothing)
        self.assertIn("smarter.apps.example.tasks.undeclared", queue_task_names(app, [app.conf.task_default_queue]))
        self.assertNotIn("smarter.apps.example.tasks.undeclared", queue_task_names(app, [OPERATIONAL_QUEUE]))

    def test_the_operational_worker(self):
        """Smarter-worker can't run an infrastructure task, e.g. one pushed onto its queue."""
        app = throwaway_app((OPERATIONAL_QUEUE,))
        builtins = [name for name in app.tasks if name.startswith(CELERY_BUILTIN_TASK_PREFIX)]
        removed = keep_only_queue_tasks(app)
        self.assertEqual(removed, sorted([OTHER_TASK, TOOL_WORKER_TASKS[0]]))
        self.assertEqual(platform_task_names(app), [OPERATIONAL_TASK])
        for name in builtins:
            self.assertIn(name, app.tasks)
        # what the worker does with a message for a task it doesn't have: "Received unregistered task".
        with self.assertRaises(NotRegistered):
            app.tasks[OTHER_TASK]  # pylint: disable=pointless-statement

    def test_the_infrastructure_worker(self):
        """Smarter-worker-infrastructure can't run an operational task with the cluster's credentials."""
        app = throwaway_app((INFRASTRUCTURE_QUEUE,))
        keep_only_queue_tasks(app)
        self.assertEqual(platform_task_names(app), [OTHER_TASK])
        with self.assertRaises(NotRegistered):
            app.tasks[OPERATIONAL_TASK]  # pylint: disable=pointless-statement

    def test_a_worker_of_two_queues_keeps_both(self):
        app = throwaway_app((OPERATIONAL_QUEUE, INFRASTRUCTURE_QUEUE))
        keep_only_queue_tasks(app)
        self.assertEqual(platform_task_names(app), sorted([OPERATIONAL_TASK, OTHER_TASK]))

    def test_a_worker_of_no_platform_queue_is_an_error(self):
        """A worker started without -Q would run nothing, so it refuses to start."""
        app = throwaway_app()
        with self.assertRaises(SmarterConfigurationError) as raised:
            keep_only_queue_tasks(app)
        self.assertIn(app.conf.task_default_queue, str(raised.exception))
        # nothing was removed.
        self.assertEqual(len(platform_task_names(app)), len(THROWAWAY_TASK_QUEUES))

    def test_keep_only_tasks(self):
        app = throwaway_app()
        removed = keep_only_tasks(app, [OPERATIONAL_TASK])
        self.assertEqual(removed, sorted([OTHER_TASK, TOOL_WORKER_TASKS[0]]))
        self.assertEqual(platform_task_names(app), [OPERATIONAL_TASK])

    def test_every_platform_task_declares_a_workers_queue(self):
        """A task whose queue no worker consumes would never run: each of the platform's names one."""
        workers_queues = (
            smarter_settings.app_llmclient_tasks_celery_task_queue,
            smarter_settings.app_infrastructure_tasks_celery_task_queue,
            smarter_settings.app_tools_tasks_celery_task_queue,
        )
        names = platform_task_names(APP)
        self.assertTrue(names)
        for name in names:
            with self.subTest(task=name):
                declared_queue = getattr(APP.tasks[name], "queue", None)
                self.assertIn(declared_queue, workers_queues)

    def test_each_workers_queue_has_tasks(self):
        """The operational and infrastructure workers each keep tasks: neither would refuse to start."""
        for queue in (
            smarter_settings.app_llmclient_tasks_celery_task_queue,
            smarter_settings.app_infrastructure_tasks_celery_task_queue,
        ):
            with self.subTest(queue=queue):
                self.assertTrue(queue_task_names(APP, [queue]))
        self.assertIn(OTHER_TASK, queue_task_names(APP, [smarter_settings.app_infrastructure_tasks_celery_task_queue]))
        self.assertIn(OPERATIONAL_TASK, queue_task_names(APP, [smarter_settings.app_llmclient_tasks_celery_task_queue]))

    def test_startup_checks(self):
        """A worker runs the workers' startup checks; the tool worker its own, then sums them up."""
        with (
            mock.patch("smarter.apps.infrastructure.startup.run_startup_checks") as run,
            mock.patch("smarter.apps.infrastructure.startup.log_tool_worker_readiness") as readiness,
        ):
            run_worker_startup_checks()
            run.assert_called_once_with(WORKER_CHECKS)
            readiness.assert_not_called()
            run.reset_mock()
            run.return_value = {"check_tool_worker_isolation": True, "check_tool_worker_redis": True}
            with in_the_tool_worker():
                run_worker_startup_checks()
            run.assert_called_once_with(TOOL_WORKER_CHECKS)
            readiness.assert_called_once()
            results, tasks, queue = readiness.call_args.args
            self.assertEqual(results, run.return_value)
            self.assertIn(TOOL_WORKER_TASKS[0], tasks)
            for name in tasks:
                self.assertFalse(name.startswith("celery."), name)
            self.assertEqual(queue, "tools_celery_task_queue")

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


class TestToolWorkerQueue(SmarterTestBase):
    """The tool worker consumes its queue without declaring it, and takes no remote control (ADR-030, rule 8)."""

    def test_in_the_tool_worker(self):
        """Its queue is no_declare, so it never writes kombu's routing set, and remote control is off."""
        app = Celery("test_celery_conf_queue", set_as_current=False)
        with in_the_tool_worker():
            configure_tool_worker(app)
        queues = list(app.conf.task_queues)
        names = [queue.name for queue in queues]
        # both workers without a database: -Q picks each one's own (issue #1077).
        self.assertEqual(names, ["tools_celery_task_queue", "extensions_celery_task_queue"])
        for queue in queues:
            with self.subTest(queue=queue.name):
                self.assertEqual(queue.routing_key, queue.name)
                self.assertEqual(queue.exchange.name, queue.name)
                self.assertTrue(queue.no_declare)
        self.assertFalse(app.conf.worker_enable_remote_control)

    def test_other_workers_are_unchanged(self):
        """A worker with a database keeps Celery's queues and its remote control."""
        app = Celery("test_celery_conf_queue", set_as_current=False)
        configure_tool_worker(app)
        self.assertIsNone(app.conf.task_queues)
        self.assertTrue(app.conf.worker_enable_remote_control)
