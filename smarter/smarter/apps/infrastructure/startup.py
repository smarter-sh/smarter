"""
The self-checks that a Smarter server runs when it starts.

The settings check the AWS credentials when every process starts
(:func:`~smarter.common.conf.settings.aws.aws_credentials_work`), and warn at once if they don't
work. The checks here do the same for the rest of what a server depends on: the Kubernetes
cluster, the database, the Redis cache and the Celery broker, and, in the tool worker, the
isolation that ADR-038 promises. A broken dependency is then in a pod's first log lines, rather
than found at the first request, the first deploy or the next run of a periodic task. A check
that passes logs one INFO line, one that fails a WARNING that says what to check, or an ERROR
when the tool worker can reach what it must not.

:func:`run_startup_checks` runs one of the lists below, once per server, and never raises, so
that no check can keep a server from starting. It is called from :mod:`smarter.asgi`, in the
first of uvicorn's workers, with :data:`WEB_SERVER_CHECKS`, and from each Celery worker's main
process, through Celery's ``worker_init`` signal (:mod:`smarter.lib.celery_conf`), with
:data:`WORKER_CHECKS`, or :data:`TOOL_WORKER_CHECKS` in the tool worker. Celery Beat,
``manage.py`` commands, the Docker build and the unit tests don't check: an ``AppConfig.ready()``
would run the checks in all of them.
"""

import os
import socket
from collections.abc import Callable, Sequence

from cache_results import lazy_cache
from django.conf import settings
from django.db import connection
from redis import Redis
from redis.exceptions import NoPermissionError, RedisError

from smarter.apps.infrastructure.services import infrastructure
from smarter.apps.infrastructure.services.kubernetes import (
    KubectlKubernetesService,
    in_cluster_server,
)
from smarter.common.conf import smarter_settings
from smarter.common.helpers.processes import is_first_worker
from smarter.common.helpers.startup_banner import mask_url
from smarter.lib import logging
from smarter.lib.unittest import running_unit_tests

logger = logging.getSmarterLogger(__name__)

StartupCheck = Callable[[], bool]
"""A self-check: it logs its result, and returns whether it passed."""

STARTUP_CHECK_TIMEOUT = 2
"""Seconds that a check waits for a connection, or for the Celery broker.

The database has its own connect timeout.
"""

CACHE_CHECK_KEY = "smarter.apps.infrastructure.startup.check_cache"
"""The key that :func:`check_cache` writes and reads back."""

INSTANCE_METADATA_SERVICE = ("169.254.169.254", 80)
"""The address of the cloud's instance metadata service, which hands out the node's IAM role."""

INTERNET_HOST = ("example.com", 443)
"""A public host, reserved for examples (RFC 2606), that the tool worker must reach: tool calls need the internet."""

TOOL_WORKER_FORBIDDEN_VARIABLES = (
    "AWS_ACCESS_KEY_ID",
    "AWS_ROLE_ARN",
    "AWS_CONTAINER_CREDENTIALS_FULL_URI",
    "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
)
"""Environment variables that give boto3 credentials, which the tool worker must never have."""

TOOL_WORKER_FORBIDDEN_NAME_PARTS = ("PASSWORD", "SECRET", "API_KEY", "TOKEN", "FERNET")
"""
Parts of an environment variable's name that mark it as a credential.

For example ``SMARTER_SUBSYSTEM_SQL_PASSWORD``, ``DJANGO_SECRET_KEY``, ``AWS_WEB_IDENTITY_TOKEN_FILE`` or
``SMARTER_APP_PROVIDER_OPENAI_API_KEY``. The tool worker's environment is an allowlist (``smarter.toolsEnv`` in the Helm chart), so a name like these in it is
a credential that was added by mistake. The broker's and the cache's urls carry Redis's password, which
the tool worker needs, under names that don't match.
"""

TOOL_WORKER_ALLOWED_CREDENTIALS = ("SMARTER_SUBSYSTEM_REDIS_PASSWORD",)
"""
The one credential that the tool worker holds: the password of its own Redis ACL user, ``tools``.

With it, the tool worker takes its tasks from the broker and reads Extensions' archives from the cache.
The user's ACL limits it to those keys (ADR-030, rule 8), which :func:`check_tool_worker_redis` confirms.
"""

SESSION_KEY_PROBE = ":1:django.contrib.sessions.cache" + "0" * 32
"""
A session's key in Redis's database 2, which the tool worker must not read.

Django's cache session backend keys each session by its cookie's value, so a session's key name is a
sign-in. No session has this one: the probe only asks whether the tool worker may look.
"""


# ------------------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------------------
def error_description(error: Exception) -> str:
    """
    Describe an error by its type, and its numeric code if it has one, never its message.

    A message can hold a cluster's arn, a host name or a user name. A code is enough to tell
    "access denied" (MySQL's 1045) from "can't connect" (2003).

    :param error: The error.
    :returns: e.g. ``OperationalError 2003``, or ``RuntimeError``.
    """
    name = type(error).__name__
    if error.args and isinstance(error.args[0], int):
        description = f"{name} {error.args[0]}"
        return description
    return name


def credential_variables() -> list[str]:
    """
    Name the environment variables that hold credentials which the tool worker must never have.

    :returns: Their names, sorted, never their values: those in :data:`TOOL_WORKER_FORBIDDEN_VARIABLES`,
        and those whose name has a part of :data:`TOOL_WORKER_FORBIDDEN_NAME_PARTS`.
    """
    names = []
    for name, value in os.environ.items():
        if not value:
            continue
        if name in TOOL_WORKER_ALLOWED_CREDENTIALS:
            continue
        if name in TOOL_WORKER_FORBIDDEN_VARIABLES:
            names.append(name)
            continue
        for part in TOOL_WORKER_FORBIDDEN_NAME_PARTS:
            if part in name:
                names.append(name)
                break
    names.sort()
    return names


def can_connect(host: str, port: int, timeout: float = STARTUP_CHECK_TIMEOUT) -> bool:
    """
    Whether a TCP connection to a host's port succeeds.

    :param host: The host name or address.
    :param port: The port.
    :param timeout: Seconds to wait.
    :returns: True if it connected. A network policy that drops the connection makes this wait
        the whole timeout, then return False.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# ------------------------------------------------------------------------------
# Kubernetes
# ------------------------------------------------------------------------------
def kubernetes_credentials() -> str:
    """
    Describe what kubectl authenticates with.

    :returns: ``the pod's ServiceAccount`` in a pod that has a ServiceAccount token (see
        :func:`~smarter.apps.infrastructure.services.kubernetes.in_cluster_server`), otherwise
        ``the kubeconfig``.
    """
    if in_cluster_server():
        return "the pod's ServiceAccount"
    return "the kubeconfig"


def kubernetes_problem(configured: bool, credentials: str, namespace: str) -> str:
    """
    Explain why kubectl's Kubernetes service isn't ready, and what to check.

    :param configured: Whether kubectl is configured for the cluster
        (:attr:`~smarter.apps.infrastructure.services.kubernetes.KubectlKubernetesService.configured`).
    :param credentials: What kubectl authenticates with, from :func:`kubernetes_credentials`.
    :param namespace: The environment's namespace.
    :returns: The explanation.
    """
    if not configured:
        problem = (
            "kubectl is not configured for the cluster: the cloud provider could not write the kubeconfig. "
            "Check the cloud credentials, and the cluster's name and region."
        )
        return problem
    problem = (
        f"the namespace {namespace} does not exist, or {credentials} is not allowed to read it. "
        "Check the namespace, and the Role and ClusterRole of the Helm chart."
    )
    return problem


def check_kubernetes() -> bool:
    """
    Check that kubectl reaches the cluster, and that the environment's namespace exists.

    :returns: True if the cluster is ready.
    """
    namespace = smarter_settings.environment_namespace
    credentials = kubernetes_credentials()
    kubernetes = infrastructure.kubernetes
    is_kubectl = False
    configured = True
    if isinstance(kubernetes, KubectlKubernetesService):
        is_kubectl = True
        # kubectl that isn't configured tries to write the kubeconfig again, and warns again,
        # each time configured is read, so it is read once, here.
        configured = kubernetes.configured
    ready = False
    if configured:
        ready = kubernetes.ready
    if ready:
        logger.info(
            "Kubernetes is configured: kubectl authenticates with %s, and the namespace %s exists.",
            credentials,
            namespace,
        )
        return True
    if is_kubectl:
        problem = kubernetes_problem(configured, credentials, namespace)
    else:
        problem = f"the {kubernetes.provider_name} Kubernetes service is not ready."
    logger.warning("Kubernetes is not configured properly. Some features may not work as expected: %s", problem)
    return False


# ------------------------------------------------------------------------------
# the database, Redis and the broker
# ------------------------------------------------------------------------------
def database_description() -> str:
    """
    Describe the platform's database, without its credentials.

    :returns: e.g. ``smarter@smarter-mariadb:3306``.
    """
    database = settings.DATABASES["default"]
    description = f"{database.get('NAME')}@{database.get('HOST')}:{database.get('PORT')}"
    return description


def check_database() -> bool:
    """
    Check that the platform's database answers a query.

    The connection is closed afterwards, so that a Celery worker's pool processes, which fork
    after this, don't share it.

    :returns: True if it answered.
    """
    description = database_description()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning(
            "The database %s is not reachable: %s. Check its host, port and credentials.",
            description,
            error_description(e),
        )
        return False
    finally:
        connection.close()
    logger.info("The database %s is reachable.", description)
    return True


def check_cache() -> bool:
    """
    Check that the Redis cache stores a value and returns it.

    :returns: True if it returned the value.
    """
    location = mask_url(str(settings.CACHES["default"].get("LOCATION")))
    try:
        lazy_cache.set(CACHE_CHECK_KEY, True, timeout=10)
        stored = lazy_cache.get(CACHE_CHECK_KEY)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("The cache %s is not reachable: %s.", location, error_description(e))
        return False
    if stored is not True:
        logger.warning("The cache %s did not return the value that was stored.", location)
        return False
    logger.info("The cache %s is reachable.", location)
    return True


def check_broker() -> bool:
    """
    Check that the Celery broker accepts a connection, so that the web server can send tasks.

    The workers don't run this check: Celery connects to the broker as a worker starts, and logs it.

    :returns: True if it connected.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.lib.celery_conf import APP

    url = mask_url(APP.conf.broker_url)
    try:
        with APP.connection_for_write() as broker:
            broker.ensure_connection(max_retries=1, timeout=STARTUP_CHECK_TIMEOUT)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("The Celery broker %s is not reachable: %s. Tasks can't be sent.", url, error_description(e))
        return False
    logger.info("The Celery broker %s is reachable.", url)
    return True


# ------------------------------------------------------------------------------
# the tool worker's isolation (ADR-038)
# ------------------------------------------------------------------------------
def tool_worker_forbidden_targets() -> list[tuple[str, str, int]]:
    """
    Name what the tool worker must not reach: the instance metadata service, and the Kubernetes api.

    Both are in the private ranges that smarter-infrastructure's ``smarter-tools-egress`` network
    policy denies. MariaDB's port is not among them: SQL plugins may use it.

    :returns: Each target's description, host and port.
    """
    metadata_host, metadata_port = INSTANCE_METADATA_SERVICE
    targets = [("the instance metadata service", metadata_host, metadata_port)]
    kubernetes_host = os.environ.get("KUBERNETES_SERVICE_HOST")
    if kubernetes_host:
        kubernetes_port = int(os.environ.get("KUBERNETES_SERVICE_PORT", "443"))
        targets.append(("the Kubernetes api", kubernetes_host, kubernetes_port))
    return targets


def check_tool_worker_isolation() -> bool:
    """
    Confirm, one by one, that the tool worker has none of the platform's credentials, and can't reach the cluster's private addresses.

    ADR-038 promises that the tool calls, whose code and requests manifest authors, extension
    authors and the LLM choose, run where there is nothing to steal. Nothing else verifies it: a
    network policy that is weakened, or a credential that is added to the tool worker's Secret,
    leaves every tool call working. So each capability that was removed is tested, and its result
    logged on a line of its own: INFO that confirms it is absent, or an ERROR when it is present.
    A last line sums them up.

    It runs only in a pod. In docker-compose the tool worker shares ``.env``, and its credentials,
    with the other services, and there are no network policies, so nothing there could pass.

    :returns: True if every removed capability is confirmed absent, or the tool worker isn't in a pod.
    """
    if not os.environ.get("KUBERNETES_SERVICE_HOST"):
        logger.info(
            "The tool worker's isolation (ADR-038) is not checked outside Kubernetes: in docker-compose it shares "
            ".env with the other services, and no network policy applies."
        )
        return True
    isolated = True

    present = credential_variables()
    if present:
        logger.error(
            "ADR-038 breach: the tool worker has credentials in its environment: %s. "
            "Check the Helm chart's secret-env-tools.yaml.",
            ", ".join(present),
        )
        isolated = False
    else:
        logger.info(
            "ADR-038 confirmed: the tool worker's environment has no credentials (AWS, database, keys, tokens)."
        )

    if in_cluster_server():
        logger.error(
            "ADR-038 breach: the tool worker has a Kubernetes ServiceAccount token. "
            "Check automountServiceAccountToken in the Helm chart's deployment-worker-tools.yaml."
        )
        isolated = False
    else:
        logger.info("ADR-038 confirmed: the tool worker has no Kubernetes ServiceAccount token.")

    for description, host, port in tool_worker_forbidden_targets():
        if can_connect(host, port):
            logger.error(
                "ADR-038 breach: the tool worker can reach %s (%s:%s). Check that smarter-infrastructure's "
                "smarter-tools-egress network policy exists (enable_enhanced_security), and denies it.",
                description,
                host,
                port,
            )
            isolated = False
        else:
            logger.info("ADR-038 confirmed: the tool worker can't reach %s (%s:%s).", description, host, port)

    internet_host, internet_port = INTERNET_HOST
    if can_connect(internet_host, internet_port):
        logger.info(
            "The tool worker reaches the internet (%s:%s), which tool calls need.", internet_host, internet_port
        )
    else:
        logger.warning(
            "The tool worker can't reach the internet (%s:%s): tool calls that need it will fail.",
            internet_host,
            internet_port,
        )

    if isolated:
        logger.info("The tool worker is isolated: every capability that ADR-038 removes is confirmed absent.")
    else:
        logger.error("The tool worker is NOT isolated: see the ADR-038 breaches above.")
    return isolated


RedisProbe = Callable[[], object]
"""A read of Redis that the tool worker's ACL user must be refused."""


def tool_worker_redis_probes(broker: Redis, cache: Redis, sessions: Redis) -> list[tuple[str, RedisProbe]]:
    """
    Name the reads of Redis that the tool worker's ACL user must be refused, each with its probe.

    Each probe only reads, so that a missing ACL changes nothing: a key that the user can't read, and
    that no pattern of its ACL names, can't be written either. They cover what code in the tool worker
    could otherwise do with Redis's url: push a task to another worker's queue, rebind its own queue,
    plant a message among the other workers' unacknowledged ones, edit RedBeat's schedule, read the cache
    and the sessions, and list the keys or the channels, whose names include sessions' keys.

    :param broker: A client of the broker's database, 0.
    :param cache: A client of the cache's database, 1.
    :param sessions: A client of the sessions' database, 2.
    :returns: Each probe's description, an action that completes "the user tools can't ...", e.g.
        ``read the sessions``, and the probe.
    """
    operational_queue = smarter_settings.app_llmclient_tasks_celery_task_queue
    infrastructure_queue = smarter_settings.app_infrastructure_tasks_celery_task_queue
    tools_queue = smarter_settings.app_tools_tasks_celery_task_queue
    cache_key = f"{settings.CACHE_KEY_PREFIX}:1:{CACHE_CHECK_KEY}"
    probes: list[tuple[str, RedisProbe]] = [
        ("read the operational queue", lambda: broker.llen(operational_queue)),
        ("read the infrastructure queue", lambda: broker.llen(infrastructure_queue)),
        ("read the routing of its own queue", lambda: broker.smembers(f"_kombu.binding.{tools_queue}")),
        ("read the other workers' unacknowledged messages", lambda: broker.hlen("unacked")),
        ("read RedBeat's schedule", lambda: broker.exists("redbeat::schedule")),
        ("read the cache", lambda: cache.exists(cache_key)),
        ("read the sessions", lambda: sessions.exists(SESSION_KEY_PROBE)),
        ("list the keys", lambda: broker.scan(0, count=1)),
        ("list the pub/sub channels", broker.pubsub_channels),
    ]
    return probes


def tool_worker_redis_breaches(probes: Sequence[tuple[str, RedisProbe]]) -> list[str]:
    """
    Run the probes, and name those that Redis allowed.

    :param probes: From :func:`tool_worker_redis_probes`.
    :returns: The description of each probe that wasn't refused with NOPERM. A probe that fails some
        other way, e.g. a lost connection, is logged and counts as allowed: the ACL wasn't confirmed.
    """
    breaches = []
    for description, probe in probes:
        try:
            probe()
        except NoPermissionError:
            continue
        except RedisError as e:
            logger.warning("Whether the tool worker can %s could not be checked: %s", description, error_description(e))
        breaches.append(description)
    return breaches


def redis_client(url: str) -> Redis:
    """
    Return a Redis client for a url, with the startup checks' timeout.

    :param url: A Redis url, with its credentials and database.
    :returns: The client.
    """
    client = Redis.from_url(url, socket_timeout=STARTUP_CHECK_TIMEOUT, socket_connect_timeout=STARTUP_CHECK_TIMEOUT)
    return client


def check_tool_worker_redis() -> bool:
    """
    Confirm that the tool worker's Redis ACL user can reach its own queue, and nothing else of the platform's.

    The tool worker holds Redis's url, which it needs to take its tasks and read Extensions' archives. As
    Redis's ``default`` user, that url would let code in the tool worker, an Extension's included, push a
    task to the infrastructure worker, which holds the Kubernetes Role and the IAM role, or read every user's
    session (ADR-030). Its own user, ``tools``, is refused all of that, and :func:`tool_worker_redis_probes`
    confirms it, one read at a time, each logged on a line of its own.

    It runs wherever the tool worker does, docker-compose included, whose Redis defines the same user.

    :returns: True if the tool worker reads its own queue, and every probe is refused.
    """
    username = smarter_settings.subsystem_redis_username
    if not username:
        logger.error(
            "ADR-030 breach: the tool worker authenticates to Redis as its default user, which may read every "
            "queue and session. Set SMARTER_SUBSYSTEM_REDIS_USERNAME and its password: see the Helm chart's "
            "smarter.toolsEnv."
        )
        return False
    broker = redis_client(settings.CELERY_BROKER_URL)
    cache = redis_client(str(settings.CACHES["default"]["LOCATION"]))
    sessions = redis_client(str(settings.CACHES["sessions"]["LOCATION"]))
    tools_queue = smarter_settings.app_tools_tasks_celery_task_queue
    try:
        broker.llen(tools_queue)
    except RedisError as e:
        logger.warning(
            "The tool worker's Redis user %s can't read its own queue, %s: %s. Tool calls will not run.",
            username,
            tools_queue,
            error_description(e),
        )
        return False
    logger.info("The tool worker's Redis user %s reads its own queue, %s.", username, tools_queue)
    probes = tool_worker_redis_probes(broker, cache, sessions)
    breaches = tool_worker_redis_breaches(probes)
    for description, _probe in probes:
        if description in breaches:
            logger.error(
                "ADR-030 breach: the tool worker's Redis user %s can %s. Check the Redis ACL in the Helm "
                "chart's redis.master.preExecCmds.",
                username,
                description,
            )
        else:
            logger.info("ADR-030 confirmed: the tool worker's Redis user %s can't %s.", username, description)
    if breaches:
        return False
    logger.info("The tool worker's Redis user %s reaches only its own keys.", username)
    return True


# ------------------------------------------------------------------------------
# the lists, and the runner
# ------------------------------------------------------------------------------
WEB_SERVER_CHECKS: tuple[StartupCheck, ...] = (check_database, check_cache, check_broker, check_kubernetes)
"""The web server's checks."""

WORKER_CHECKS: tuple[StartupCheck, ...] = (check_database, check_cache, check_kubernetes)
"""A Celery worker's checks.

Celery checks its own broker.
"""

TOOL_WORKER_CHECKS: tuple[StartupCheck, ...] = (check_tool_worker_isolation, check_tool_worker_redis)
"""The tool worker's checks.

It has no database, and its pods never reach Kubernetes.
"""


def run_startup_checks(checks: Sequence[StartupCheck]) -> dict[str, bool]:
    """
    Run self-checks once per server, each of which logs its own result.

    An error in a check is logged by its type, and counts as a failure, so that no check can keep
    the server from starting.

    :param checks: The checks, e.g. :data:`WEB_SERVER_CHECKS`.
    :returns: Whether each check passed, by its name; empty in the unit tests, and in every
        worker of a server but the first.
    """
    results: dict[str, bool] = {}
    if running_unit_tests():
        return results
    if not is_first_worker("startup-checks"):
        return results
    for check in checks:
        name = check.__name__
        try:
            passed = check()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("%s could not run: %s", name, error_description(e))
            passed = False
        results[name] = passed
    return results


__all__ = [
    "TOOL_WORKER_CHECKS",
    "WEB_SERVER_CHECKS",
    "WORKER_CHECKS",
    "can_connect",
    "check_broker",
    "check_cache",
    "check_database",
    "check_kubernetes",
    "check_tool_worker_isolation",
    "check_tool_worker_redis",
    "credential_variables",
    "error_description",
    "kubernetes_credentials",
    "kubernetes_problem",
    "run_startup_checks",
    "redis_client",
    "tool_worker_forbidden_targets",
    "tool_worker_redis_breaches",
    "tool_worker_redis_probes",
]
