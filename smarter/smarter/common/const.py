# pylint: disable=E1101
"""
Constants of the platform's code.

This is for constants that are highly unlikely to change.
Anything else belongs in ``smarter_settings`` and/or Django settings, who's values are
substantially derived from the Helm chart and environment variables.
"""

import importlib.util
import os
from pathlib import Path
from typing import Dict

SMARTER_LOCAL_PORT = 9357
SMARTER_ACCOUNT_NUMBER = "3141-5926-5359"
SMARTER_API_SUBDOMAIN = "api"


# This is a custom attribute that can be added to the request
# to indicate that the request is an internal API request. This
# is used to bypass DRF authentication and permission checks in the API views.
SMARTER_IS_INTERNAL_API_REQUEST = "smarter_is_internal_api_request"


HERE = os.path.abspath(os.path.dirname(__file__))  # smarter/smarter/common
PROJECT_ROOT = str(Path(HERE).parent)  # smarter/smarter
PYTHON_ROOT = str(Path(PROJECT_ROOT).parent)  # smarter
REPO_ROOT = str(Path(PYTHON_ROOT).parent)  # ./


def load_version() -> Dict[str, str]:
    """Stringify the __version__ module."""
    version_file_path = os.path.join(PROJECT_ROOT, "__version__.py")
    spec = importlib.util.spec_from_file_location("__version__", version_file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load version file: {version_file_path}")
    version_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(version_module)
    return version_module.__dict__


VERSION = load_version()
AUTHOR = "Lawrence P. McDaniel - https://lawrencemcdaniel.com"


# pylint: disable=too-few-public-methods
class SmarterEnvironments:
    """A class representing the fixed set environments for the Smarter API."""

    LOCAL = "local"
    ALPHA = "alpha"
    BETA = "beta"
    NEXT = "next"
    PROD = "prod"
    all = [LOCAL, ALPHA, BETA, NEXT, PROD]
    aws_environments = [ALPHA, BETA, NEXT, PROD]


class SmarterKubernetesPodKinds:
    """
    The fixed set of kinds of pod that the platform runs: the values of ``SERVICE_TYPE``.

    The Helm chart sets ``SERVICE_TYPE`` on each Deployment and Job, and docker-compose on each service, and
    ``smarter_settings.service_type`` validates it against :attr:`all`. The settings check each kind for what it
    should and shouldn't hold (ADR-038). This class says what each kind *is*; what each kind *does* with a
    credential is :class:`SmarterPodCapabilities`.
    """

    API = "api"
    WORKER = "worker"
    WORKER_INFRASTRUCTURE = "worker-infrastructure"
    BEAT = "beat"
    WORKER_TOOLS = "worker-tools"
    WORKER_EXTENSIONS = "worker-extensions"
    JOB_INIT = "job-init"
    JOB_MIGRATE = "job-migrate"
    JOB_BACKUP = "job-backup"
    BASTION = "bastion"

    labels: Dict[str, str] = {
        API: "the api server",
        WORKER: "the worker",
        WORKER_INFRASTRUCTURE: "the infrastructure worker",
        BEAT: "Celery Beat",
        WORKER_TOOLS: "the tool worker",
        WORKER_EXTENSIONS: "the Extension worker",
        JOB_INIT: "the init job",
        JOB_MIGRATE: "the migrate job",
        JOB_BACKUP: "the backup job",
        BASTION: "the bastion",
    }
    """How each kind's name reads in a sentence, e.g. in the settings' READY line: ``for the tool worker``."""

    all = list(labels)
    """Every kind of pod."""

    restricted = [WORKER_TOOLS, WORKER_EXTENSIONS]
    """The kinds without a database, which run code that the platform doesn't control (ADR-038, issue #1077)."""

    with_database = [API, WORKER, WORKER_INFRASTRUCTURE, BEAT, JOB_INIT, JOB_MIGRATE, JOB_BACKUP, BASTION]
    """The kinds with a database: every one but the :attr:`restricted` workers, which a test checks."""


class SmarterPodCapabilities:
    """
    What a kind of pod does that needs a credential: each capability lists the kinds of pod that have it (ADR-038).

    A credential setting names the capability that uses it, e.g. ``HeldBy(*SmarterPodCapabilities.email)`` on SMTP's
    password, so that only those kinds hold it (:mod:`smarter.common.conf.credentials`). They are lists of members,
    not the Kubernetes Roles or the IAM roles that the Helm chart and smarter-infrastructure create: those are one
    per kind of pod, for all of its capabilities at once. What a pod *is*, e.g. whether it has a database, is on
    :class:`SmarterKubernetesPodKinds`.
    """

    smarter_secrets = [
        SmarterKubernetesPodKinds.API,
        SmarterKubernetesPodKinds.WORKER,
        SmarterKubernetesPodKinds.WORKER_INFRASTRUCTURE,
        SmarterKubernetesPodKinds.JOB_INIT,
    ]
    """
    Decrypt and encrypt Smarter Secrets, with the Fernet key: the app, both workers and the init Job.

    The tasks that use a Secret's value, e.g. an LLMHost's api key or a plugin's connection, run in the workers, and
    the init Job creates the bootstrap Secrets.
    """

    signing = [
        SmarterKubernetesPodKinds.API,
        SmarterKubernetesPodKinds.WORKER,
        SmarterKubernetesPodKinds.WORKER_INFRASTRUCTURE,
        SmarterKubernetesPodKinds.JOB_INIT,
    ]
    """
    Sign what the app verifies, with the Django secret key: the app, both workers and the init Job.

    E.g. an account contact's email, which the workers send, carries an unsubscribe token signed with ``SECRET_KEY``.
    Celery Beat and the migrate Job sign nothing, and start with a random key of their own.
    """

    email = [
        SmarterKubernetesPodKinds.API,
        SmarterKubernetesPodKinds.WORKER,
        SmarterKubernetesPodKinds.WORKER_INFRASTRUCTURE,
        SmarterKubernetesPodKinds.JOB_INIT,
        SmarterKubernetesPodKinds.JOB_BACKUP,
    ]
    """
    Send email, with SMTP's credentials: the app, both workers, the init Job, and the backup Job.

    ``smarter-worker-infrastructure`` emails a custom domain's verification result, and the backup Job its own result.
    """

    aws = [
        SmarterKubernetesPodKinds.API,
        SmarterKubernetesPodKinds.WORKER,
        SmarterKubernetesPodKinds.WORKER_INFRASTRUCTURE,
        SmarterKubernetesPodKinds.JOB_INIT,
        SmarterKubernetesPodKinds.JOB_BACKUP,
        SmarterKubernetesPodKinds.BASTION,
    ]
    """
    Call AWS: S3, Route53, ACM and EKS.

    On Kubernetes, each kind with its own IAM role, and no key.

    The backup Job saves its dump to S3. Celery Beat and the migrate Job make no AWS call, and have no role
    (ADR-038, phase 3), so the settings don't ask STS for credentials there (``Settings.uses_aws``).
    """

    job_logs = [
        SmarterKubernetesPodKinds.JOB_INIT,
        SmarterKubernetesPodKinds.JOB_BACKUP,
    ]
    """Post a Job's log to Slack, with ``manage.py email_job_log``: the init Job and the backup Job."""

    database_admin = [
        SmarterKubernetesPodKinds.JOB_INIT,
        SmarterKubernetesPodKinds.JOB_BACKUP,
        SmarterKubernetesPodKinds.BASTION,
    ]
    """
    Administer the database server, as its administrator or the backup account.

    The init Job creates the database, its user and the backup account. The backup Job dumps the database as the
    backup account, or as the administrator until that account exists. The bastion is for a person who does either.
    """


class SmarterHttpMethods:
    """A class representing the fixed set of HTTP methods used in the Smarter API."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    all = [GET, POST, PUT, PATCH, DELETE]
