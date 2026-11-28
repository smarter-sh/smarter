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
    should and shouldn't hold (ADR-038), and :mod:`smarter.common.conf.credentials` says which kinds hold each
    credential.
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

    platform = [API, WORKER, WORKER_INFRASTRUCTURE, JOB_INIT]
    """
    The kinds that do the platform's work: serve requests, run its tasks, and initialize it.

    The app, ``smarter-worker``, ``smarter-worker-infrastructure`` and the init Job. They decrypt Smarter Secrets
    (the Fernet key), send email (SMTP), and sign what the app verifies (the Django secret key): e.g. an account
    contact's email, which the workers send, carries an unsubscribe token signed with ``SECRET_KEY``. It is narrower
    than :attr:`with_database`: Celery Beat, the migrate Job, the backup Job and the bastion have a database, but do
    none of that. The backup Job sends one email, its own result, which is why it holds SMTP's credentials too.
    """


class SmarterHttpMethods:
    """A class representing the fixed set of HTTP methods used in the Smarter API."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    all = [GET, POST, PUT, PATCH, DELETE]
