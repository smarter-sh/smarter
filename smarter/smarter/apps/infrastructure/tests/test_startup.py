"""
Test :mod:`smarter.apps.infrastructure.startup`.

Nothing reaches the cluster, the internet or the instance metadata service: the facade is replaced
with fakes, so kubectl never runs, and connections are faked with :func:`fake_can_connect`. The
database and cache checks use the test stack's own database and Redis.
"""

import os
import uuid
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, PropertyMock, patch

from django.conf import settings
from django.db import OperationalError
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import NoPermissionError

from smarter.apps.infrastructure.services import (
    InMemoryKubernetesService,
    KubectlKubernetesService,
)
from smarter.apps.infrastructure.startup import (
    INSTANCE_METADATA_SERVICE,
    INTERNET_HOST,
    TOOL_WORKER_CHECKS,
    WEB_SERVER_CHECKS,
    WORKER_CHECKS,
    can_connect,
    check_broker,
    check_cache,
    check_database,
    check_kubernetes,
    check_tool_worker_isolation,
    check_tool_worker_redis,
    credential_variables,
    error_description,
    kubernetes_credentials,
    kubernetes_problem,
    log_tool_worker_readiness,
    redis_client,
    run_startup_checks,
    tool_worker_forbidden_targets,
    tool_worker_redis_breaches,
    tool_worker_redis_probes,
)
from smarter.common.conf import smarter_settings
from smarter.common.conf.settings import Settings
from smarter.common.conf.settings.cache import (
    EXTENSION_WORKER_REDIS_USERNAME,
    LOCAL_EXTENSION_WORKER_REDIS_PASSWORD,
    LOCAL_TOOL_WORKER_REDIS_PASSWORD,
    TOOL_WORKER_REDIS_USERNAME,
)
from smarter.common.utils.redis_url import redis_server_url
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.apps.infrastructure.startup"

KUBERNETES_API = ("10.100.0.1", 443)
"""The Kubernetes api's address in a fake pod's environment."""

POD_ENVIRONMENT = {
    "KUBERNETES_SERVICE_HOST": KUBERNETES_API[0],
    "KUBERNETES_SERVICE_PORT": str(KUBERNETES_API[1]),
    "DJANGO_CELERY_BROKER_URL": "redis://:not-a-credential-name@smarter-redis:6379/0",
}
"""The tool worker's environment in a pod, as the Helm chart gives it: no credential's name."""


def kubectl_service(ready: bool, configured: bool) -> Mock:
    """
    A stand-in for :class:`KubectlKubernetesService`, which isinstance() accepts, and which never runs kubectl.

    :param ready: What its ``ready`` says.
    :param configured: What its ``configured`` says.
    :returns: The stand-in.
    """
    service = Mock(spec=KubectlKubernetesService)
    service.ready = ready
    service.configured = configured
    service.provider_name = "aws"
    return service


def fake_can_connect(reachable: set[tuple[str, int]]):
    """
    A replacement for can_connect() that reaches only these addresses, without a connection.

    :param reachable: The host and port of each address that connects.
    :returns: The replacement.
    """

    def connect(host: str, port: int, timeout: float = 0.0) -> bool:
        return (host, port) in reachable

    return connect


class TestCheckKubernetes(SmarterTestBase):
    """Check_kubernetes() logs whether the cluster is ready, and what to check when it isn't."""

    def check(self, kubernetes, in_cluster: bool = False) -> bool:
        """
        Run check_kubernetes() with this Kubernetes service.

        :param kubernetes: The service that the facade returns.
        :param in_cluster: Whether the process runs in a pod with a ServiceAccount token.
        :returns: What check_kubernetes() returned.
        """
        facade = SimpleNamespace(kubernetes=kubernetes)
        server = None
        if in_cluster:
            server = "https://10.0.0.1:443"
        with (
            patch(f"{MODULE}.in_cluster_server", return_value=server),
            patch(f"{MODULE}.infrastructure", facade),
        ):
            result = check_kubernetes()
        return result

    def test_ready_in_a_pod(self):
        """A ready cluster is logged at INFO, with the ServiceAccount and the namespace."""
        with self.assertLogs(MODULE, level="INFO") as captured:
            self.assertTrue(self.check(kubectl_service(ready=True, configured=True), in_cluster=True))
        record = captured.records[0]
        self.assertEqual(record.levelname, "INFO")
        self.assertIn("the pod's ServiceAccount", record.getMessage())
        self.assertIn(smarter_settings.environment_namespace, record.getMessage())

    def test_not_configured(self):
        """A kubeconfig that the provider couldn't write is a WARNING that says what to check."""
        with self.assertLogs(MODULE, level="WARNING") as captured:
            self.assertFalse(self.check(kubectl_service(ready=False, configured=False)))
        message = captured.records[0].getMessage()
        self.assertIn("could not write the kubeconfig", message)
        self.assertIn("Check the cloud credentials", message)

    def test_namespace_missing(self):
        """A configured kubectl that can't read the namespace is a WARNING that names it, and RBAC."""
        with self.assertLogs(MODULE, level="WARNING") as captured:
            self.assertFalse(self.check(kubectl_service(ready=False, configured=True), in_cluster=True))
        message = captured.records[0].getMessage()
        self.assertIn(smarter_settings.environment_namespace, message)
        self.assertIn("the pod's ServiceAccount is not allowed to read it", message)
        self.assertIn("ClusterRole", message)

    def test_not_configured_is_read_once(self):
        """Kubectl that isn't configured tries to write the kubeconfig on each read, so it is read once, and ready isn't."""
        kubernetes = Mock(spec=KubectlKubernetesService)
        kubernetes.provider_name = "aws"
        configured = PropertyMock(return_value=False)
        ready = PropertyMock(return_value=False)
        type(kubernetes).configured = configured
        type(kubernetes).ready = ready
        with self.assertLogs(MODULE, level="WARNING"):
            self.assertFalse(self.check(kubernetes))
        configured.assert_called_once_with()
        ready.assert_not_called()

    def test_other_service_not_ready(self):
        """A service other than kubectl's, e.g. the in-memory one, is named by its provider."""
        with self.assertLogs(MODULE, level="WARNING") as captured:
            self.assertFalse(self.check(InMemoryKubernetesService(ready=False)))
        self.assertIn("memory Kubernetes service is not ready", captured.records[0].getMessage())

    def test_other_service_ready(self):
        """The in-memory service, when ready, is logged at INFO like any other."""
        with self.assertLogs(MODULE, level="INFO"):
            self.assertTrue(self.check(InMemoryKubernetesService(ready=True)))

    def test_kubernetes_credentials(self):
        """Kubectl authenticates with the pod's ServiceAccount in a pod, and with the kubeconfig elsewhere."""
        with patch(f"{MODULE}.in_cluster_server", return_value="https://10.0.0.1:443"):
            self.assertEqual(kubernetes_credentials(), "the pod's ServiceAccount")
        with patch(f"{MODULE}.in_cluster_server", return_value=None):
            self.assertEqual(kubernetes_credentials(), "the kubeconfig")

    def test_kubernetes_problem(self):
        """The problem is the kubeconfig when kubectl isn't configured, otherwise the namespace."""
        not_configured = kubernetes_problem(False, "the kubeconfig", "smarter-local")
        self.assertIn("could not write the kubeconfig", not_configured)
        no_namespace = kubernetes_problem(True, "the kubeconfig", "smarter-local")
        self.assertIn("the namespace smarter-local does not exist", no_namespace)


class TestDependencyChecks(SmarterTestBase):
    """The database, cache and broker checks: the real ones of the test stack, and faked failures."""

    def test_database(self):
        """The test stack's database answers, which is logged without credentials."""
        with self.assertLogs(MODULE, level="INFO") as captured:
            self.assertTrue(check_database())
        message = captured.records[0].getMessage()
        self.assertIn("is reachable", message)
        self.assertNotIn(str(smarter_settings.subsystem_sql_password), message)

    def test_database_unreachable(self):
        """An unreachable database is a WARNING with the error's code, not its message, which names hosts and users."""
        error = OperationalError(2003, "Can't connect to MySQL server on 'private-host'")
        with patch(f"{MODULE}.connection.cursor", side_effect=error):
            with self.assertLogs(MODULE, level="WARNING") as captured:
                self.assertFalse(check_database())
        message = captured.records[0].getMessage()
        self.assertIn("OperationalError 2003", message)
        self.assertNotIn("private-host", message)

    def test_cache(self):
        """The test stack's Redis stores and returns a value; its url is logged with the password masked."""
        with self.assertLogs(MODULE, level="INFO") as captured:
            self.assertTrue(check_cache())
        message = captured.records[0].getMessage()
        self.assertIn("is reachable", message)
        self.assertNotIn(":smarter@", message)

    def test_cache_unreachable(self):
        """A cache that raises is a WARNING."""
        with patch(f"{MODULE}.lazy_cache.set", side_effect=ConnectionError("refused")):
            with self.assertLogs(MODULE, level="WARNING") as captured:
                self.assertFalse(check_cache())
        self.assertIn("ConnectionError", captured.records[0].getMessage())

    def test_cache_loses_the_value(self):
        """A cache that stores nothing, e.g. a dummy backend, is a WARNING."""
        with (
            patch(f"{MODULE}.lazy_cache.set"),
            patch(f"{MODULE}.lazy_cache.get", return_value=None),
        ):
            with self.assertLogs(MODULE, level="WARNING") as captured:
                self.assertFalse(check_cache())
        self.assertIn("did not return the value", captured.records[0].getMessage())

    def test_broker(self):
        """A broker that connects is logged at INFO, with its password masked."""
        broker = MagicMock()
        with patch("smarter.lib.celery_conf.APP.connection_for_write", return_value=broker):
            with self.assertLogs(MODULE, level="INFO") as captured:
                self.assertTrue(check_broker())
        broker.__enter__.return_value.ensure_connection.assert_called_once()
        self.assertNotIn(":smarter@", captured.records[0].getMessage())

    def test_broker_unreachable(self):
        """A broker that doesn't connect is a WARNING: the web server can't send tasks."""
        with patch("smarter.lib.celery_conf.APP.connection_for_write", side_effect=ConnectionError("refused")):
            with self.assertLogs(MODULE, level="WARNING") as captured:
                self.assertFalse(check_broker())
        self.assertIn("Tasks can't be sent", captured.records[0].getMessage())


class TestToolWorkerIsolation(SmarterTestBase):
    """Check_tool_worker_isolation() reports, as an ERROR, each way the tool worker could reach what ADR-038 forbids."""

    def check(self, environment: dict[str, str], reachable: set[tuple[str, int]], token: bool = False) -> bool:
        """
        Run the check in this environment, reaching only these addresses.

        :param environment: The process's whole environment.
        :param reachable: The addresses that connect.
        :param token: Whether a ServiceAccount token is mounted.
        :returns: What check_tool_worker_isolation() returned.
        """
        server = None
        if token:
            server = "https://10.100.0.1:443"
        with (
            patch.dict(os.environ, environment, clear=True),
            patch(f"{MODULE}.can_connect", side_effect=fake_can_connect(reachable)),
            patch(f"{MODULE}.in_cluster_server", return_value=server),
        ):
            result = check_tool_worker_isolation()
        return result

    def test_not_in_a_pod(self):
        """Docker-compose has no network policies, so outside a pod nothing is checked, and nothing connects."""
        with patch(f"{MODULE}.can_connect") as connect:
            with self.assertLogs(MODULE, level="INFO") as captured:
                self.assertTrue(self.check({}, set()))
        connect.assert_not_called()
        self.assertIn("not checked outside Kubernetes", captured.records[0].getMessage())

    def test_isolated(self):
        """Only the internet reaches: each removed capability is confirmed absent on a line of its own, at INFO."""
        with self.assertLogs(MODULE, level="INFO") as captured:
            self.assertTrue(self.check(POD_ENVIRONMENT, {INTERNET_HOST}))
        levels = {record.levelname for record in captured.records}
        self.assertEqual(levels, {"INFO"})
        messages = [record.getMessage() for record in captured.records]
        expected = [
            "ADR-038 confirmed: the tool worker's environment has no credentials",
            "ADR-038 confirmed: the tool worker has no Kubernetes ServiceAccount token.",
            "ADR-038 confirmed: the tool worker can't reach the instance metadata service (169.254.169.254:80).",
            "ADR-038 confirmed: the tool worker can't reach the Kubernetes api (10.100.0.1:443).",
            "The tool worker reaches the internet (example.com:443)",
            "The tool worker is isolated: every capability that ADR-038 removes is confirmed absent.",
        ]
        self.assertEqual(len(messages), len(expected))
        for message, start in zip(messages, expected):
            self.assertIn(start, message)

    def test_a_breach_is_summed_up(self):
        """After a breach, the last line says that the tool worker is not isolated."""
        with self.assertLogs(MODULE, level="ERROR") as captured:
            self.assertFalse(self.check(POD_ENVIRONMENT, {INTERNET_HOST, INSTANCE_METADATA_SERVICE}))
        self.assertIn("is NOT isolated", captured.records[-1].getMessage())

    def test_reaches_the_metadata_service(self):
        """Reaching the instance metadata service, which hands out the node's role, is an ERROR."""
        reachable = {INTERNET_HOST, INSTANCE_METADATA_SERVICE}
        with self.assertLogs(MODULE, level="ERROR") as captured:
            self.assertFalse(self.check(POD_ENVIRONMENT, reachable))
        message = captured.records[0].getMessage()
        self.assertIn("the instance metadata service", message)
        self.assertIn("smarter-tools-egress", message)

    def test_reaches_the_kubernetes_api(self):
        """Reaching the Kubernetes api is an ERROR."""
        reachable = {INTERNET_HOST, KUBERNETES_API}
        with self.assertLogs(MODULE, level="ERROR") as captured:
            self.assertFalse(self.check(POD_ENVIRONMENT, reachable))
        self.assertIn("the Kubernetes api", captured.records[0].getMessage())

    def test_has_credentials(self):
        """A credential in the environment is an ERROR that names the variable, never its value."""
        environment = {**POD_ENVIRONMENT, "SMARTER_SUBSYSTEM_SQL_PASSWORD": "value-that-must-not-be-logged"}
        with self.assertLogs(MODULE, level="ERROR") as captured:
            self.assertFalse(self.check(environment, {INTERNET_HOST}))
        message = captured.records[0].getMessage()
        self.assertIn("SMARTER_SUBSYSTEM_SQL_PASSWORD", message)
        self.assertNotIn("value-that-must-not-be-logged", message)

    def test_has_a_service_account_token(self):
        """A mounted ServiceAccount token is an ERROR."""
        with self.assertLogs(MODULE, level="ERROR") as captured:
            self.assertFalse(self.check(POD_ENVIRONMENT, {INTERNET_HOST}, token=True))
        self.assertIn("automountServiceAccountToken", captured.records[0].getMessage())

    def test_no_internet(self):
        """No internet is a WARNING, not a breach: the tool worker is still isolated."""
        with self.assertLogs(MODULE, level="WARNING") as captured:
            self.assertTrue(self.check(POD_ENVIRONMENT, set()))
        self.assertIn("can't reach the internet", captured.records[0].getMessage())

    def test_forbidden_targets(self):
        """The Kubernetes api is a target only in a pod, which has its address in the environment."""
        with patch.dict(os.environ, POD_ENVIRONMENT, clear=True):
            targets = tool_worker_forbidden_targets()
        addresses = [(host, port) for _, host, port in targets]
        self.assertEqual(addresses, [INSTANCE_METADATA_SERVICE, KUBERNETES_API])
        with patch.dict(os.environ, {}, clear=True):
            targets = tool_worker_forbidden_targets()
        self.assertEqual(len(targets), 1)

    def test_credential_variables(self):
        """Credentials are found by name, empty ones are ignored, and Redis's urls are allowed."""
        environment = {
            **POD_ENVIRONMENT,
            "AWS_ACCESS_KEY_ID": "x",
            "AWS_WEB_IDENTITY_TOKEN_FILE": "/var/run/token",
            "SMARTER_APP_PROVIDER_OPENAI_API_KEY": "x",
            "DJANGO_SECRET_KEY": "",
            "SMARTER_DEBUG_MODE": "false",
            # its own Redis user's password, which it needs.
            "SMARTER_SUBSYSTEM_REDIS_PASSWORD": "x",
        }
        with patch.dict(os.environ, environment, clear=True):
            names = credential_variables()
        expected = ["AWS_ACCESS_KEY_ID", "AWS_WEB_IDENTITY_TOKEN_FILE", "SMARTER_APP_PROVIDER_OPENAI_API_KEY"]
        self.assertEqual(names, expected)


class TestRunStartupChecks(SmarterTestBase):
    """Run_startup_checks() runs each check once per server, and never raises."""

    def run_checks(self, checks, first: bool = True) -> dict[str, bool]:
        """
        Run checks as a server's worker would, outside the unit tests.

        :param checks: The checks.
        :param first: Whether this process is its server's first worker.
        :returns: What run_startup_checks() returned.
        """
        with (
            patch(f"{MODULE}.running_unit_tests", return_value=False),
            patch(f"{MODULE}.is_first_worker", return_value=first),
        ):
            results = run_startup_checks(checks)
        return results

    def test_results_by_name(self):
        """Each check's result is returned by its name."""

        def passes() -> bool:
            return True

        def fails() -> bool:
            return False

        self.assertEqual(self.run_checks([passes, fails]), {"passes": True, "fails": False})

    def test_an_error_is_a_failure_logged_by_type(self):
        """An error in a check never keeps the server from starting, and its message, which can hold an arn, isn't logged."""

        def raises() -> bool:
            raise RuntimeError("arn:aws:eks:ca-central-1:000000000000:cluster/x")

        with self.assertLogs(MODULE, level="WARNING") as captured:
            results = self.run_checks([raises])
        self.assertEqual(results, {"raises": False})
        message = captured.records[0].getMessage()
        self.assertIn("RuntimeError", message)
        self.assertNotIn("arn:aws", message)

    def test_once_per_server(self):
        """Only the first of a server's workers checks."""
        check = Mock(return_value=True, __name__="check")
        self.assertEqual(self.run_checks([check], first=False), {})
        check.assert_not_called()

    def test_not_in_the_unit_tests(self):
        """The unit tests never check, so that nothing reaches the cluster."""
        check = Mock(return_value=True, __name__="check")
        self.assertEqual(run_startup_checks([check]), {})
        check.assert_not_called()

    def test_the_lists(self):
        """Every server but the tool worker checks the database, cache and Kubernetes; only the web server the broker."""
        for checks in (WEB_SERVER_CHECKS, WORKER_CHECKS):
            for check in (check_database, check_cache, check_kubernetes):
                self.assertIn(check, checks)
        self.assertIn(check_broker, WEB_SERVER_CHECKS)
        self.assertNotIn(check_broker, WORKER_CHECKS)
        self.assertEqual(TOOL_WORKER_CHECKS, (check_tool_worker_isolation, check_tool_worker_redis))


class TestHelpers(SmarterTestBase):
    """Error_description() and can_connect()."""

    def test_error_description(self):
        """An error is described by its type, and its numeric code if it has one, never its message."""
        self.assertEqual(
            error_description(OperationalError(1045, "Access denied for user 'someone'")), "OperationalError 1045"
        )
        self.assertEqual(error_description(RuntimeError("private")), "RuntimeError")

    def test_can_connect(self):
        """A connection that opens is True, and is closed; one that fails is False."""
        with patch(f"{MODULE}.socket.create_connection") as create:
            self.assertTrue(can_connect("example.com", 443, timeout=1.0))
        create.assert_called_once_with(("example.com", 443), timeout=1.0)
        create.return_value.__exit__.assert_called_once()
        with patch(f"{MODULE}.socket.create_connection", side_effect=TimeoutError()):
            self.assertFalse(can_connect("example.com", 443))


def with_redis_username(username):
    """
    Patch the settings' Redis username.

    The settings are frozen, so their class is patched.

    :param username: The username, or None for the default user.
    :returns: The patch, as a context manager.
    """
    patch_ = patch.object(
        Settings, "subsystem_redis_username", new_callable=PropertyMock, return_value=username, create=True
    )
    return patch_


def in_the_extension_worker():
    """
    Patch the settings so that this process looks like the Extension worker: no database, the Extensions queue.

    The settings are frozen, so their class is patched.

    :returns: The patches, as one context manager.
    """
    stack = ExitStack()
    stack.enter_context(
        patch.object(Settings, "database_unavailable", new_callable=PropertyMock, return_value=True, create=True)
    )
    stack.enter_context(
        patch.object(
            Settings,
            "app_tools_worker_queue",
            new_callable=PropertyMock,
            return_value="extensions_celery_task_queue",
            create=True,
        )
    )
    return stack


def refusing_client(allowed_queue: str) -> MagicMock:
    """
    A stand-in Redis client that refuses every probe, as the tools user's ACL does, and reads one queue.

    :param allowed_queue: The queue whose length it returns.
    :returns: The stand-in.
    """
    client = MagicMock()

    def llen(key):
        if key == allowed_queue:
            return 0
        raise NoPermissionError("NOPERM")

    client.llen.side_effect = llen
    for method in ("smembers", "hlen", "exists", "scan", "pubsub_channels"):
        getattr(client, method).side_effect = NoPermissionError("NOPERM")
    return client


class TestToolWorkerRedis(SmarterTestBase):
    """Check_tool_worker_redis() confirms that the tool worker's Redis user reaches only its own keys."""

    def test_breaches(self):
        """A refused probe is no breach; one that is allowed, or that can't be checked, is."""

        def refused():
            raise NoPermissionError("NOPERM")

        def lost():
            raise RedisConnectionError("gone")

        probes = [("refused", refused), ("allowed", lambda: 1), ("lost", lost)]
        with self.assertLogs(MODULE, level="WARNING"):
            breaches = tool_worker_redis_breaches(probes)
        self.assertEqual(breaches, ["allowed", "lost"])

    def test_default_user_is_a_breach(self):
        """Without a username, the tool worker would be Redis's default user."""
        with with_redis_username(None), self.assertLogs(MODULE, level="ERROR") as captured:
            self.assertFalse(check_tool_worker_redis())
        self.assertIn("default user", "\n".join(captured.output))

    def test_every_probe_refused(self):
        """The tools user reads its own queue, and is refused every probe."""
        tools_queue = smarter_settings.app_tools_tasks_celery_task_queue
        client = refusing_client(tools_queue)
        with (
            with_redis_username(TOOL_WORKER_REDIS_USERNAME),
            patch(f"{MODULE}.redis_client", return_value=client),
            self.assertLogs(MODULE, level="INFO") as captured,
        ):
            self.assertTrue(check_tool_worker_redis())
        output = "\n".join(captured.output)
        self.assertIn("reaches only its own keys", output)
        self.assertNotIn("breach", output)
        # each line is a sentence: "can't" and the probe's action.
        self.assertIn("Redis user tools can't read the sessions.", output)
        self.assertIn("Redis user tools can't list the keys.", output)

    def test_an_allowed_probe_is_logged(self):
        """A probe that Redis allows is an ERROR, named."""
        tools_queue = smarter_settings.app_tools_tasks_celery_task_queue
        client = refusing_client(tools_queue)
        client.exists.side_effect = None
        client.exists.return_value = 0
        with (
            with_redis_username(TOOL_WORKER_REDIS_USERNAME),
            patch(f"{MODULE}.redis_client", return_value=client),
            self.assertLogs(MODULE, level="ERROR") as captured,
        ):
            self.assertFalse(check_tool_worker_redis())
        output = "\n".join(captured.output)
        self.assertIn("the sessions", output)
        self.assertIn("RedBeat's schedule", output)

    def test_own_queue_unreadable(self):
        """A user that can't read its own queue runs no tool call."""
        client = refusing_client("another queue")
        with (
            with_redis_username(TOOL_WORKER_REDIS_USERNAME),
            patch(f"{MODULE}.redis_client", return_value=client),
            self.assertLogs(MODULE, level="WARNING") as captured,
        ):
            self.assertFalse(check_tool_worker_redis())
        self.assertIn("can't read its own queue", "\n".join(captured.output))

    def test_redis_client(self):
        """The client has the startup checks' timeout, and the url's database."""
        client = redis_client("redis://:pw@smarter-redis:6379/2")
        kwargs = client.connection_pool.connection_kwargs
        self.assertEqual(kwargs["db"], 2)
        self.assertEqual(kwargs["socket_timeout"], 2)


class TestToolWorkerReadiness(SmarterTestBase):
    """The line that ends the tool worker's startup checks, from log_tool_worker_readiness(), sums them up."""

    TASKS = ["smarter.apps.llmtool.tasks.run_tool_call"]
    QUEUE = "tools_celery_task_queue"

    def test_every_check_passed(self):
        """One INFO line: correctly configured, with what it runs and where it takes it from."""
        results = {"check_tool_worker_isolation": True, "check_tool_worker_redis": True}
        with (
            patch.dict(os.environ, POD_ENVIRONMENT, clear=True),
            self.assertLogs(MODULE, level="INFO") as captured,
        ):
            self.assertTrue(log_tool_worker_readiness(results, self.TASKS, self.QUEUE))
        self.assertEqual(len(captured.records), 1)
        record = captured.records[0]
        self.assertEqual(record.levelname, "INFO")
        message = record.getMessage()
        self.assertIn("Startup checks passed", message)
        self.assertIn("the tool worker is correctly configured to run tool calls.", message)
        self.assertIn("runs only smarter.apps.llmtool.tasks.run_tool_call, from tools_celery_task_queue", message)
        self.assertIn("It is isolated (ADR-038)", message)

    def test_the_extension_worker(self):
        """The Extension worker names itself, and what it runs: Extensions' code, a process per call (issue #1077)."""
        results = {"check_tool_worker_isolation": True, "check_tool_worker_redis": True}
        with (
            in_the_extension_worker(),
            patch.dict(os.environ, POD_ENVIRONMENT, clear=True),
            self.assertLogs(MODULE, level="INFO") as captured,
        ):
            log_tool_worker_readiness(results, self.TASKS, "extensions_celery_task_queue")
        message = captured.records[0].getMessage()
        self.assertIn(
            "the Extension worker is correctly configured to run Extensions' code, each call in a process of its own.",
            message,
        )
        self.assertIn("from extensions_celery_task_queue", message)

    def test_outside_kubernetes_isolation_is_not_claimed(self):
        """In docker-compose the isolation check checks nothing, so the line says so."""
        results = {"check_tool_worker_isolation": True, "check_tool_worker_redis": True}
        with patch.dict(os.environ, {}, clear=True), self.assertLogs(MODULE, level="INFO") as captured:
            log_tool_worker_readiness(results, self.TASKS, self.QUEUE)
        message = captured.records[0].getMessage()
        self.assertNotIn("It is isolated", message)
        self.assertIn("Its isolation (ADR-038) is checked only in Kubernetes", message)

    def test_a_check_failed(self):
        """An ERROR naming each failed check, and never a claim that it is correctly configured."""
        results = {"check_tool_worker_isolation": True, "check_tool_worker_redis": False}
        with self.assertLogs(MODULE, level="INFO") as captured:
            self.assertFalse(log_tool_worker_readiness(results, self.TASKS, self.QUEUE))
        self.assertEqual(len(captured.records), 1)
        record = captured.records[0]
        self.assertEqual(record.levelname, "ERROR")
        self.assertIn("NOT correctly configured", record.getMessage())
        self.assertIn("check_tool_worker_redis", record.getMessage())

    def test_nothing_when_the_checks_did_not_run(self):
        """The unit tests, and every worker but the first, run no checks, and so claim nothing."""
        with patch(f"{MODULE}.logger") as logger:
            self.assertFalse(log_tool_worker_readiness({}, self.TASKS, self.QUEUE))
        logger.info.assert_not_called()
        logger.error.assert_not_called()


class TestToolWorkerRedisAcl(SmarterTestBase):
    """
    The test stack's Redis defines the tool worker's user with the Helm chart's rules: check them, for real.

    docker-compose.yml and docker-compose.shard.yml give smarter-redis the user ``tools``, with the rules of
    the Helm chart's ``redis.master.preExecCmds``; a chart test keeps the three the same. These tests connect as
    that user, and as the default user, so a rule that is too narrow, which would break tool calls, or too
    wide, which would let code in the tool worker reach another worker's queue or the sessions, fails here.
    Every key they write is their own, and deleted.
    """

    tools: Redis
    tools_cache: Redis
    tools_sessions: Redis
    admin: Redis
    admin_cache: Redis
    admin_sessions: Redis
    suffix: str

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        server = redis_server_url("smarter-redis:6379", TOOL_WORKER_REDIS_USERNAME, LOCAL_TOOL_WORKER_REDIS_PASSWORD)
        cls.tools = Redis.from_url(f"{server}/0")
        cls.tools_cache = Redis.from_url(f"{server}/1")
        cls.tools_sessions = Redis.from_url(f"{server}/2")
        cls.admin = Redis.from_url(settings.CELERY_BROKER_URL)
        cls.admin_cache = Redis.from_url(str(settings.CACHES["default"]["LOCATION"]))
        cls.admin_sessions = Redis.from_url(str(settings.CACHES["sessions"]["LOCATION"]))
        cls.suffix = uuid.uuid4().hex

    @classmethod
    def tearDownClass(cls):
        for client in (cls.tools, cls.tools_cache, cls.tools_sessions, cls.admin, cls.admin_cache, cls.admin_sessions):
            client.close()
        super().tearDownClass()

    def test_every_probe_refused_to_the_tools_user(self):
        """The startup check's probes, which are refused to the tools user."""
        probes = tool_worker_redis_probes(self.tools, self.tools_cache, self.tools_sessions)
        self.assertEqual(tool_worker_redis_breaches(probes), [])

    def test_every_probe_allowed_to_the_default_user(self):
        """The same probes, allowed to the default user: they would find a missing ACL."""
        probes = tool_worker_redis_probes(self.admin, self.admin_cache, self.admin_sessions)
        breaches = tool_worker_redis_breaches(probes)
        self.assertEqual(len(breaches), len(probes))

    def test_its_queue_and_kombus_keys_under_it(self):
        """It pushes and pops its queue's keys, where kombu keeps its messages in flight in the tool worker."""
        key = f"{smarter_settings.app_tools_tasks_celery_task_queue}.test-{self.suffix}"
        self.addCleanup(self.admin.delete, key)
        self.tools.rpush(key, "message")
        self.assertEqual(self.tools.lpop(key), b"message")
        unacked = f"{smarter_settings.app_tools_tasks_celery_task_queue}.unacked"
        self.tools.hlen(unacked)

    def test_cannot_push_to_another_queue(self):
        """Not the infrastructure queue, whose worker holds the Kubernetes Role and the IAM role."""
        queue = smarter_settings.app_infrastructure_tasks_celery_task_queue
        with self.assertRaises(NoPermissionError):
            self.tools.rpush(queue, "forged")

    def test_cannot_rebind_its_queue(self):
        """Kombu's routing set, which the app reads, is the app's to write."""
        binding = f"_kombu.binding.{smarter_settings.app_tools_tasks_celery_task_queue}"
        with self.assertRaises(NoPermissionError):
            self.tools.sadd(binding, "forged")

    def test_results(self):
        """It reads and writes the tool calls' results, and publishes them."""
        key = f"celery-task-meta-test-{self.suffix}"
        self.addCleanup(self.admin.delete, key)
        self.tools.set(key, "result", ex=60)
        self.assertEqual(self.tools.get(key), b"result")
        self.tools.publish(key, "result")

    def test_extension_archives_are_read_only(self):
        """It reads an Extension's archive from the cache, and can't replace one."""
        key = f"{settings.CACHE_KEY_PREFIX}:1:smarter:extension:archive:test-{self.suffix}"
        self.addCleanup(self.admin_cache.delete, key)
        self.admin_cache.set(key, "archive", ex=60)
        self.assertEqual(self.tools_cache.get(key), b"archive")
        with self.assertRaises(NoPermissionError):
            self.tools_cache.set(key, "replaced")

    def test_robots_txt_cache(self):
        """It caches a website's robots.txt, which a page fetch checks on each redirect, in the tool worker."""
        key = (
            f"{settings.CACHE_KEY_PREFIX}:1:smarter.apps.llmtool.plugin.websearch_fetch.robots_rules."
            f"<locals>.get_cached_robots_txt()_test-{self.suffix}"
        )
        self.addCleanup(self.admin_cache.delete, key)
        self.tools_cache.set(key, "rules", ex=60)
        self.assertEqual(self.tools_cache.get(key), b"rules")

    def test_log_streams_are_write_only(self):
        """It adds its log records to the console's streams, and can't read anyone's."""
        key = f"stream:logs:test-{self.suffix}"
        self.addCleanup(self.admin_cache.delete, key)
        self.tools_cache.xadd(key, {"data": "record"})
        self.tools_cache.publish(f"logs:test-{self.suffix}", "record")
        with self.assertRaises(NoPermissionError):
            self.tools_cache.xrange(key)

    def test_cannot_list_or_subscribe(self):
        """Key and channel names include sessions' keys and users' log channels."""
        with self.assertRaises(NoPermissionError):
            self.tools.keys("*")
        with self.assertRaises(NoPermissionError):
            self.tools.scan(0)
        with self.assertRaises(NoPermissionError):
            self.tools.pubsub_channels()
        pubsub = self.tools.pubsub()
        self.addCleanup(pubsub.close)
        with self.assertRaises(NoPermissionError):
            pubsub.subscribe("logs:global")
            pubsub.get_message(timeout=1)

    def test_cannot_read_a_session(self):
        """A session in database 2, written by the default user, is out of the tools user's reach."""
        key = f":1:django.contrib.sessions.cachetest{self.suffix}"
        self.addCleanup(self.admin_sessions.delete, key)
        self.admin_sessions.set(key, "session", ex=60)
        with self.assertRaises(NoPermissionError):
            self.tools_sessions.get(key)


class TestExtensionWorkerRedisAcl(SmarterTestBase):
    """
    The test stack's Redis defines the Extension worker's user, extensions, with the Helm chart's rules: check them.

    It may use its own queue, never the tools queue, where the tool worker's calls wait with their credentials
    (issue #1077). Every key the tests write is their own, and deleted.
    """

    extensions: Redis
    extensions_cache: Redis
    extensions_sessions: Redis
    admin: Redis
    suffix: str

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        server = redis_server_url(
            "smarter-redis:6379", EXTENSION_WORKER_REDIS_USERNAME, LOCAL_EXTENSION_WORKER_REDIS_PASSWORD
        )
        cls.extensions = Redis.from_url(f"{server}/0")
        cls.extensions_cache = Redis.from_url(f"{server}/1")
        cls.extensions_sessions = Redis.from_url(f"{server}/2")
        cls.admin = Redis.from_url(settings.CELERY_BROKER_URL)
        cls.suffix = uuid.uuid4().hex

    @classmethod
    def tearDownClass(cls):
        for client in (cls.extensions, cls.extensions_cache, cls.extensions_sessions, cls.admin):
            client.close()
        super().tearDownClass()

    def test_every_probe_refused(self):
        """The startup check's probes, as the Extension worker runs them, are all refused to its user."""
        with in_the_extension_worker():
            probes = tool_worker_redis_probes(self.extensions, self.extensions_cache, self.extensions_sessions)
        descriptions = [description for description, _probe in probes]
        self.assertIn("read the tool worker's queue", descriptions)
        self.assertEqual(tool_worker_redis_breaches(probes), [])

    def test_its_own_queue(self):
        """It pushes and pops its queue's keys, where kombu keeps its messages in flight in the Extension worker."""
        key = f"{smarter_settings.app_extensions_tasks_celery_task_queue}.test-{self.suffix}"
        self.addCleanup(self.admin.delete, key)
        self.extensions.rpush(key, "message")
        self.assertEqual(self.extensions.lpop(key), b"message")

    def test_cannot_read_the_tools_queue(self):
        """The tool worker's queue, where API, SQL and MCP calls wait with their credentials, is out of reach."""
        with self.assertRaises(NoPermissionError):
            self.extensions.llen(smarter_settings.app_tools_tasks_celery_task_queue)
        with self.assertRaises(NoPermissionError):
            self.extensions.hlen(f"{smarter_settings.app_tools_tasks_celery_task_queue}.unacked")

    def test_no_robots_txt_cache(self):
        """Only the tool worker's page fetches use it."""
        key = (
            f"{settings.CACHE_KEY_PREFIX}:1:smarter.apps.llmtool.plugin.websearch_fetch.robots_rules."
            f"<locals>.get_cached_robots_txt()_test-{self.suffix}"
        )
        with self.assertRaises(NoPermissionError):
            self.extensions_cache.set(key, "rules", ex=60)

    def test_results_and_archives(self):
        """It writes its calls' results, and reads Extensions' archives."""
        key = f"celery-task-meta-test-{self.suffix}"
        self.addCleanup(self.admin.delete, key)
        self.extensions.set(key, "result", ex=60)
        self.assertEqual(self.extensions.get(key), b"result")
        archive = f"{settings.CACHE_KEY_PREFIX}:1:smarter:extension:archive:test-{self.suffix}"
        self.assertIsNone(self.extensions_cache.get(archive))
