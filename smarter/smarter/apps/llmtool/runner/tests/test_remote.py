"""Test the remote tool runner, the tool worker's task, and what keeps the tool worker without a database."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from unittest import mock

from cache_results import lazy_cache
from celery.exceptions import TimeoutError as CeleryTimeoutError

from smarter.apps.llmtool import tasks
from smarter.apps.llmtool.extension.loader import archive_cache_key
from smarter.apps.llmtool.extension.tests.mixins import ExtensionTestMixin
from smarter.apps.llmtool.extension.toolkit import ExtensionToolkit
from smarter.apps.llmtool.plugin.tests.base_classes import FakeWebHost, mock_web_host
from smarter.apps.llmtool.runner import (
    EXTENSION_KIND,
    TOOL_CALL_MODELS,
    TOOL_EXECUTORS,
    InProcessToolRunner,
    RemoteToolRunner,
    ToolCall,
    ToolCallLabel,
    ToolCallResult,
    call_model_for,
    carry_tool_call_label,
    current_tool_call_label,
    get_tool_runner,
    kind_runs_in_this_worker,
    labeled_tool_calls,
    queue_for_kind,
    running_in_tool_worker,
)
from smarter.apps.llmtool.runner.http import HttpToolCall, fetch_with_runner
from smarter.apps.llmtool.runner.runner import (
    MAX_REMOTE_TIMEOUT_SECONDS,
    call_timeout,
    remote_timeout,
)
from smarter.apps.llmtool.tasks import (
    describe_tool_call_label,
    describe_tool_call_outcome,
    run_tool_call,
)
from smarter.common.conf import smarter_settings
from smarter.common.conf.settings import Settings
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib import json
from smarter.lib.celery_conf import (
    APP,
    HideTaskDataFilter,
    hide_tool_calls_from_logs,
    set_result_backend,
)
from smarter.lib.django.waffle.is_active import switches_can_be_read
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.narrowing import json_object

SETTINGS_PATCH = "smarter.apps.llmtool.runner.runner.smarter_settings"
URL = "https://api.example.com/search"
LABEL = ToolCallLabel(tool="stackademy_sql", llmclient="stackademy (12)", session="****a1b2c3", request_id="r-1")


def eager_apply_async(args, **kwargs):
    """Run the tool worker's task here, as Celery would there, and return its EagerResult."""
    return run_tool_call.apply(args=args)


class TestRemoteToolRunner(SmarterTestBase):
    """Test the remote runner, and the tool worker's task."""

    def test_registries_name_the_same_kinds(self):
        """Every kind has both an executor and a model, and each model's kind is its key."""
        self.assertEqual(set(TOOL_CALL_MODELS), set(TOOL_EXECUTORS))
        for kind in TOOL_CALL_MODELS:
            model = call_model_for(kind)
            self.assertTrue(issubclass(model, ToolCall), kind)
            self.assertEqual(model.model_fields["kind"].default, kind)
        with self.assertRaises(SmarterConfigurationError):
            call_model_for("no-such-kind")

    def test_get_tool_runner_follows_the_setting(self):
        """The setting chooses the runner, and inside the tool worker every call runs in process."""
        with mock.patch(SETTINGS_PATCH) as settings:
            settings.app_llmtool_tool_runner = "in_process"
            self.assertIsInstance(get_tool_runner(), InProcessToolRunner)
            settings.app_llmtool_tool_runner = "remote"
            self.assertIsInstance(get_tool_runner(), RemoteToolRunner)
            with running_in_tool_worker():
                self.assertIsInstance(get_tool_runner(), InProcessToolRunner)
            self.assertIsInstance(get_tool_runner(), RemoteToolRunner)

    def test_each_kind_has_its_queue(self):
        """Extensions' calls go to the Extensions queue, every other kind to the tools queue (issue #1077)."""
        self.assertEqual(queue_for_kind(EXTENSION_KIND), smarter_settings.app_extensions_tasks_celery_task_queue)
        for kind in TOOL_EXECUTORS:
            if kind == EXTENSION_KIND:
                continue
            with self.subTest(kind=kind):
                self.assertEqual(queue_for_kind(kind), smarter_settings.app_tools_tasks_celery_task_queue)

    def test_each_worker_runs_its_own_kind(self):
        """The tool worker runs every kind but an Extension's; the Extension worker only an Extension's."""
        self.assertTrue(kind_runs_in_this_worker("http"))
        self.assertFalse(kind_runs_in_this_worker(EXTENSION_KIND))
        with in_the_extension_worker():
            self.assertTrue(kind_runs_in_this_worker(EXTENSION_KIND))
            self.assertFalse(kind_runs_in_this_worker("http"))

    def test_an_extension_call_goes_to_the_extensions_queue(self):
        """The remote runner sends an Extension's call to its own queue."""
        answer = ToolCallResult(value="ok").model_dump_json()
        sent = mock.Mock()
        sent.get.return_value = answer
        with mock.patch.object(run_tool_call, "apply_async", return_value=sent) as apply_async:
            result = RemoteToolRunner().run(ToolCall(kind=EXTENSION_KIND))
        self.assertEqual(result.value, "ok")
        queue = apply_async.call_args.kwargs["queue"]
        self.assertEqual(queue, smarter_settings.app_extensions_tasks_celery_task_queue)

    def test_a_worker_refuses_the_other_kind(self):
        """In a worker without a database, a call of the other worker's kind is a failure, not run."""
        with in_the_tool_worker_without_a_database():
            result = ToolCallResult.model_validate_json(run_tool_call(EXTENSION_KIND, "{}"))
        self.assertEqual(result.failure, "this worker doesn't run extension calls")
        with in_the_extension_worker():
            result = ToolCallResult.model_validate_json(run_tool_call("http", "{}"))
        self.assertEqual(result.failure, "this worker doesn't run http calls")

    def test_timeouts(self):
        """A call's own timeout, or its endpoint's, is multiplied for the remote wait, with a margin and a cap."""
        self.assertEqual(call_timeout(HttpToolCall(url=URL, timeout=7)), 7)
        self.assertEqual(call_timeout(ToolCall(kind="other")), 30)
        endpoint = mock.Mock(timeout=12)
        self.assertEqual(call_timeout(mock.Mock(spec=["endpoint"], endpoint=endpoint)), 12)
        self.assertEqual(remote_timeout(HttpToolCall(url=URL, timeout=10)), 55)
        self.assertEqual(remote_timeout(HttpToolCall(url=URL, timeout=1000)), MAX_REMOTE_TIMEOUT_SECONDS)

    def test_remote_round_trip(self):
        """A call reaches the task as JSON, on the tools queue, and its result comes back the same, through Celery."""
        host = FakeWebHost()
        host.add(URL, b'{"ok": true}', headers={"Content-Type": "application/json"})
        call = HttpToolCall(url=URL, headers={"X-Subscription-Token": "k"})
        with (
            mock.patch.object(run_tool_call, "apply_async", side_effect=eager_apply_async) as apply_async,
            mock_web_host(host),
        ):
            result = RemoteToolRunner().run(call)
        self.assertIsNone(result.failure, result.failure)
        self.assertEqual(result.status_code, 200)
        kind, call_json, label_json = apply_async.call_args.kwargs["args"]
        self.assertEqual(kind, "http")
        self.assertIsNone(label_json)
        self.assertEqual(HttpToolCall.model_validate_json(call_json), call)
        self.assertEqual(apply_async.call_args.kwargs["queue"], smarter_settings.app_tools_tasks_celery_task_queue)
        self.assertEqual(host.calls[0]["headers"]["X-Subscription-Token"], "k")

    def test_label_travels_with_the_call_and_is_logged(self):
        """A labeled call's label reaches the task, which logs it with the call's outcome, but not its credential."""
        host = FakeWebHost()
        host.add(URL, b'{"ok": true}', headers={"Content-Type": "application/json"})
        call = HttpToolCall(url=URL, headers={"X-Subscription-Token": "the-credential"})
        with (
            mock.patch.object(run_tool_call, "apply_async", side_effect=eager_apply_async) as apply_async,
            mock.patch.object(tasks, "tool_worker_logger") as tool_worker_logger,
            mock_web_host(host),
            labeled_tool_calls(LABEL),
        ):
            RemoteToolRunner().run(call)
        label_json = apply_async.call_args.kwargs["args"][2]
        self.assertEqual(ToolCallLabel.model_validate_json(label_json), LABEL)
        level, template, *args = tool_worker_logger.log.call_args.args
        line = template % tuple(args)
        self.assertEqual(level, logging.INFO)
        self.assertIn("http call", line)
        self.assertIn("succeeded (HTTP 200)", line)
        self.assertIn("tool=stackademy_sql llmclient=stackademy (12) session=****a1b2c3 request=r-1", line)
        self.assertNotIn("the-credential", line)
        self.assertNotIn(URL, line)

    def test_failed_call_is_a_warning_without_its_failure_text(self):
        """A call that couldn't be made is logged as a warning, by its outcome only, and unlabeled calls say so."""
        with mock.patch.object(tasks, "tool_worker_logger") as tool_worker_logger:
            run_tool_call("http", HttpToolCall(url="https://10.0.0.1/?key=k", timeout=1).model_dump_json())
        level, template, *args = tool_worker_logger.log.call_args.args
        line = template % tuple(args)
        self.assertEqual(level, logging.WARNING)
        self.assertIn("failed", line)
        self.assertIn("unlabeled", line)
        self.assertNotIn("key=k", line)

    def test_outcome_and_label_descriptions(self):
        """Each outcome is described by its kind and status, and a label that can't be read never stops a call."""
        self.assertEqual(describe_tool_call_outcome(ToolCallResult(value=1)), "succeeded")
        self.assertEqual(describe_tool_call_outcome(ToolCallResult(value="no", is_error=True)), "tool error")
        failed = ToolCallResult(failure="denied: pw=x", status_code=401)
        self.assertEqual(describe_tool_call_outcome(failed), "failed (HTTP 401)")
        self.assertEqual(describe_tool_call_label(None), "unlabeled")
        self.assertEqual(describe_tool_call_label("{not json"), "unreadable label")
        self.assertEqual(ToolCallLabel().describe(), "tool=- llmclient=- session=- request=-")

    def test_label_is_carried_into_threads(self):
        """A thread doesn't inherit the label, unless its function is wrapped by carry_tool_call_label()."""
        with labeled_tool_calls(LABEL), ThreadPoolExecutor(max_workers=1) as executor:
            bare = executor.submit(current_tool_call_label).result()
            carried = executor.submit(carry_tool_call_label(current_tool_call_label)).result()
        self.assertIsNone(bare)
        self.assertEqual(carried, LABEL)
        self.assertIsNone(current_tool_call_label())
        self.assertIsNone(carry_tool_call_label(current_tool_call_label)())

    def test_fetch_with_runner_through_the_remote_runner(self):
        """A caller of fetch_with_runner() gets the same response when the runner is remote."""
        host = FakeWebHost()
        host.add(URL, b"\x00binary\xff")
        with (
            mock.patch(SETTINGS_PATCH) as settings,
            mock.patch.object(run_tool_call, "apply_async", side_effect=eager_apply_async),
            mock_web_host(host),
        ):
            settings.app_llmtool_tool_runner = "remote"
            settings.app_tools_tasks_celery_task_queue = "tools_celery_task_queue"
            response = fetch_with_runner(URL)
        self.assertEqual(response.content, b"\x00binary\xff")

    def test_worker_that_does_not_answer(self):
        """A worker that doesn't answer in time is a failure for the LLM, and the result is forgotten."""
        async_result = mock.MagicMock()
        async_result.get.side_effect = CeleryTimeoutError("timed out")
        with mock.patch.object(run_tool_call, "apply_async", return_value=async_result):
            result = RemoteToolRunner().run(HttpToolCall(url=URL, timeout=1))
        self.assertIn("did not answer within 19 seconds", result.failure or "")
        async_result.forget.assert_called_once()

    def test_task_that_fails(self):
        """A task that fails, or a queue that can't be reached, is a failure for the LLM."""
        async_result = mock.MagicMock()
        async_result.get.side_effect = RuntimeError("worker lost")
        with (
            mock.patch.object(run_tool_call, "apply_async", return_value=async_result),
            mock.patch("smarter.apps.llmtool.runner.runner.logger") as runner_logger,
            labeled_tool_calls(LABEL),
        ):
            result = RemoteToolRunner().run(HttpToolCall(url=URL))
        self.assertIn("RuntimeError: worker lost", result.failure or "")
        template, *args = runner_logger.warning.call_args.args
        line = template % tuple(args)
        self.assertIn("RuntimeError", line)
        self.assertIn("tool=stackademy_sql", line)
        self.assertNotIn("worker lost", line)

    def test_task_with_an_unreadable_call(self):
        """The task reports a call that it can't rebuild, without its content, rather than raising."""
        result = ToolCallResult.model_validate_json(run_tool_call("http", '{"kind": "http", "secret": "x"}'))
        self.assertIn("could not read the http call", result.failure or "")
        self.assertNotIn("secret", result.failure or "")
        result = ToolCallResult.model_validate_json(run_tool_call("no-such-kind", "{}"))
        self.assertIsNotNone(result.failure)

    def test_task_runs_nested_calls_in_process(self):
        """Inside the task, a call that an executor makes itself runs in process, even when the setting says remote."""
        host = FakeWebHost()
        host.add(URL, b"ok")
        call = HttpToolCall(url=URL)
        with (
            mock.patch(SETTINGS_PATCH) as settings,
            mock.patch.object(run_tool_call, "apply_async") as apply_async,
            mock_web_host(host),
        ):
            settings.app_llmtool_tool_runner = "remote"
            result = ToolCallResult.model_validate_json(run_tool_call("http", call.model_dump_json()))
        self.assertIsNone(result.failure)
        apply_async.assert_not_called()

    def test_result_backend_is_the_broker(self):
        """Task results go to the broker's Redis, unless a result backend is configured, and are ignored by default."""
        conf = mock.MagicMock()
        conf.result_backend = None
        conf.broker_url = "redis://broker:6379/0"
        set_result_backend(mock.MagicMock(conf=conf))
        conf.update.assert_called_once_with(result_backend="redis://broker:6379/0")
        conf.result_backend = "redis://elsewhere:6379/3"
        conf.update.reset_mock()
        set_result_backend(mock.MagicMock(conf=conf))
        conf.update.assert_not_called()
        self.assertTrue(APP.conf.task_ignore_result)
        self.assertFalse(run_tool_call.ignore_result)
        self.assertEqual(json.loads(ToolCallResult(value=1).model_dump_json())["value"], 1)

    def test_switches_without_the_database(self):
        """In the tool worker, which has no database, every waffle switch reads as off, without a query."""
        self.assertTrue(switches_can_be_read("any_switch"))
        with (
            mock.patch.object(
                Settings, "database_unavailable", new_callable=mock.PropertyMock, return_value=True, create=True
            ),
            mock.patch("smarter.lib.django.waffle.is_active.is_database_ready") as is_database_ready,
        ):
            self.assertFalse(switches_can_be_read("any_switch"))
        is_database_ready.assert_not_called()

    def test_task_whose_executor_raises(self):
        """An executor that raises is a failure for the LLM, by the exception's type only, which may name a credential."""
        with mock.patch(
            "smarter.apps.llmtool.runner.runner.InProcessToolRunner.run", side_effect=ValueError("https://x/?key=k")
        ):
            result = ToolCallResult.model_validate_json(run_tool_call("http", HttpToolCall(url=URL).model_dump_json()))
        self.assertEqual(result.failure, "the tool worker could not run the http call: ValueError")

    def test_log_filter_hides_task_data(self):
        """Celery's records of a task's success keep its name, without its result or arguments; its pool's are dropped."""
        context = {"id": "1", "name": "run_tool_call", "return_value": "rows", "args": "('sql', 'pw')", "runtime": 1}
        record = logging.LogRecord(
            "celery.app.trace", logging.INFO, "", 0, "Task %(name)s: %(return_value)s", None, None
        )
        record.args = context
        record.data = dict(context)
        self.assertTrue(HideTaskDataFilter().filter(record))
        self.assertEqual(record.getMessage(), "Task run_tool_call: (hidden)")
        self.assertEqual(record.data["args"], "(hidden)")  # type: ignore[attr-defined]
        pool = logging.LogRecord("celery.pool", logging.DEBUG, "", 0, "TaskPool: Apply %s", ("x",), None)
        self.assertFalse(HideTaskDataFilter().filter(pool))
        other = logging.LogRecord("celery.pool", logging.DEBUG, "", 0, "started", None, None)
        self.assertTrue(HideTaskDataFilter().filter(other))

    def test_log_filter_only_in_the_tool_worker(self):
        """The filter is installed, once, only in a worker without a database."""
        trace_logger = logging.getLogger("celery.app.trace")
        hide_tool_calls_from_logs()
        self.assertFalse(any(isinstance(f, HideTaskDataFilter) for f in trace_logger.filters))
        with mock.patch.object(
            Settings, "database_unavailable", new_callable=mock.PropertyMock, return_value=True, create=True
        ):
            hide_tool_calls_from_logs()
            hide_tool_calls_from_logs()
        filters = [f for f in trace_logger.filters if isinstance(f, HideTaskDataFilter)]
        for f in filters:
            trace_logger.removeFilter(f)
            logging.getLogger("celery.pool").removeFilter(f)
        for f in [f for f in logging.getLogger("celery.pool").filters if isinstance(f, HideTaskDataFilter)]:
            logging.getLogger("celery.pool").removeFilter(f)
        self.assertEqual(len(filters), 1)


TOOL_WORKER_WAIT_SECONDS = 120
"""How long the round trips wait for a tool worker to start."""


TOOL_WORKER_PROBE_KIND = "no-such-kind"
"""A kind of call that the tool worker can't read, which it answers at once with a failure, without the network."""


def tool_worker_answers(timeout: float, kind: str = TOOL_WORKER_PROBE_KIND) -> bool:
    """
    Whether a worker takes a task from a kind's queue and answers it, within the timeout.

    The tool worker and the Extension worker take no remote control, whose keys their Redis users can't reach
    (ADR-030, rule 8), so ``celery inspect`` can't find them. Instead, each is sent a call that it can't read:
    a kind that doesn't exist, on the tools queue, or an Extension's call without its fields, on the Extensions
    queue. ``run_tool_call`` answers it with a failure.

    :param timeout: Seconds to wait for the answer.
    :param kind: The call's kind, which chooses its queue (:func:`queue_for_kind`).
    :returns: True if it answered.
    """
    sent = run_tool_call.apply_async(args=(kind, "{}"), queue=queue_for_kind(kind))
    try:
        answer = sent.get(timeout=timeout)
    except CeleryTimeoutError:
        sent.forget()
        return False
    result = json.loads(answer)
    answered = "failure" in json_object(result)
    return answered


def in_the_tool_worker_without_a_database():
    """
    Patch the settings so that this process looks like the tool worker: no database, the tools queue.

    The settings are frozen, so their class is patched.

    :returns: The patch, as a context manager.
    """
    return mock.patch.object(
        Settings, "database_unavailable", new_callable=mock.PropertyMock, return_value=True, create=True
    )


def in_the_extension_worker():
    """
    Patch the settings so that this process looks like the Extension worker: no database, the Extensions queue.

    :returns: The patches, as one context manager.
    """
    stack = ExitStack()
    stack.enter_context(in_the_tool_worker_without_a_database())
    stack.enter_context(
        mock.patch.object(
            Settings,
            "app_tools_worker_queue",
            new_callable=mock.PropertyMock,
            return_value="extensions_celery_task_queue",
            create=True,
        )
    )
    return stack


def remote_runner():
    """Patch the setting that chooses the runner to ``remote``.

    The settings are frozen, so their class is patched.
    """
    return mock.patch.object(
        Settings, "app_llmtool_tool_runner", new_callable=mock.PropertyMock, return_value="remote", create=True
    )


class TestThroughTheToolWorker(ExtensionTestMixin):
    """
    Send tool calls through the broker to the tool worker, ``smarter-worker-tools``, and back.

    Unlike :class:`TestRemoteToolRunner`, nothing here is eager or patched between the app and the worker:
    each call is a task in Redis, which a worker without a database (``SMARTER_DATABASE_UNAVAILABLE``)
    takes, runs and answers through the result backend. Each test stack runs one (docker-compose.shard.yml,
    and docker-compose.yml in CI).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # the test stack waits for its api, not for its workers, which start Django in about 30 seconds.
        workers = ((TOOL_WORKER_PROBE_KIND, "smarter-worker-tools"), (EXTENSION_KIND, "smarter-worker-extensions"))
        for kind, worker in workers:
            deadline = time.monotonic() + TOOL_WORKER_WAIT_SECONDS
            answered = tool_worker_answers(timeout=5, kind=kind)
            while not answered and time.monotonic() < deadline:
                answered = tool_worker_answers(timeout=5, kind=kind)
            if not answered:
                raise AssertionError(
                    f"no worker consumes {queue_for_kind(kind)}: these tests need {worker} running "
                    "(docker-compose.yml, docker-compose.shard.yml)."
                )

    def test_call_refused_in_the_worker(self):
        """A call that safe_http refuses comes back with the worker's failure, through Redis."""
        result = RemoteToolRunner().run(HttpToolCall(url="https://10.0.0.1/", timeout=5))
        self.assertIn("public address", result.failure or "")
        self.assertIsNone(result.status_code)

    def test_page_fetched_by_the_worker(self):
        """A page that the worker fetches comes back with its status and body, through Redis."""
        with remote_runner():
            response = fetch_with_runner("https://example.com/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Example Domain", response.content)

    def test_another_kind_refused_by_the_extension_worker(self):
        """A call of another kind, put on the Extensions queue, is refused there: it wasn't sent by the app."""
        call = HttpToolCall(url="https://example.com/", timeout=5)
        sent = run_tool_call.apply_async(args=(call.kind, call.model_dump_json()), queue=queue_for_kind(EXTENSION_KIND))
        result = ToolCallResult.model_validate_json(sent.get(timeout=30))
        self.assertEqual(result.failure, "this worker doesn't run http calls")

    def test_extension_tool_run_by_the_worker(self):
        """
        An Extension's tool runs in the Extension worker, which loads its code from the cache, where the app published it.

        The archive is removed from the cache first, so that the call publishes it, and the worker, which
        has no database, can only find it there.
        """
        extension = self.enable_echo()
        version = extension.installed_version
        assert version is not None
        lazy_cache.delete(archive_cache_key(version.sha256))
        self.addCleanup(lazy_cache.delete, archive_cache_key(version.sha256))
        toolkit = ExtensionToolkit([extension], account=self.account, user_profile=self.user_profile).load()
        with remote_runner():
            result = json_object(toolkit.call("ext_echo_echo", {"text": "from the tool worker"}))
        self.assertEqual(result.get("echo"), "hello from the tool worker", result)
        self.assertIsNotNone(lazy_cache.get(archive_cache_key(version.sha256)))
