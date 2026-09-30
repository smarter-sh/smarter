"""
Shared fixtures and helpers for the unit tests of.

:py:class:`smarter.apps.plugin.plugin.base.PluginBase`,
:py:class:`smarter.apps.plugin.plugin.sql.SqlPlugin` and
:py:class:`smarter.apps.plugin.plugin.api.ApiPlugin`.

Test data lives in ``./data``:

- ``sql-connection.yaml``: the SqlConnection used by the SqlPlugin.
- ``api-connection.yaml``: the ApiConnection used by the ApiPlugin.
- ``sql-plugin.yaml``: the shared SqlPlugin.
- ``api-plugin.yaml``: the shared ApiPlugin.
- ``static-plugin.yaml``: the shared StaticPlugin, based on the Everlasting Gobstopper sample plugin.
- ``static-plugin-edge-cases.yaml``: a StaticPlugin whose staticData exercises the semantics of the static data structure.
- ``skill-plugin.yaml``: the shared SkillPlugin, whose SKILL.md and bundled files are contained verbatim.
- ``skill-plugin-remote.yaml``: the shared remotely sourced SkillPlugin, which refers to a skill on GitHub.
- ``skill-remote/``: the skill that :class:`FakeSkillHost` serves in lieu of GitHub.

.. note::

    Class-level fixtures are expensive, so each test module packs all of its
    tests into a single test class. Tests must not mutate the shared plugins in
    the database. Tests that create, update, clone or delete plugins create
    their own throwaway plugins, which are removed via ``addCleanup()``.
    In-memory mutations of ``plugin_data`` on a freshly loaded plugin instance
    are fine, since they are never saved.

.. warning::

    Do not call ``factory_account_teardown()`` from inside a test. In addition
    to the objects passed to it, it sweeps every test UserProfile and Account,
    including this class's own fixtures.
"""

import copy
import os
import socket
import time
from contextlib import contextmanager
from typing import Any, Optional
from unittest import mock
from urllib.parse import quote

import requests
from django.core.cache import cache

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.connection.manifest.models.api_connection.model import (
    SAMApiConnection,
)
from smarter.apps.connection.manifest.models.sql_connection.model import (
    SAMSqlConnection,
)
from smarter.apps.connection.models import ApiConnection, SqlConnection
from smarter.apps.connection.tests.factories import secret_factory
from smarter.apps.plugin.manifest.models.api_plugin.model import SAMApiPlugin
from smarter.apps.plugin.manifest.models.skill_plugin.model import SAMSkillPlugin
from smarter.apps.plugin.manifest.models.sql_plugin.model import SAMSqlPlugin
from smarter.apps.plugin.manifest.models.static_plugin.model import SAMStaticPlugin
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.plugin.api import ApiPlugin
from smarter.apps.plugin.plugin.skill import SkillPlugin
from smarter.apps.plugin.plugin.sql import SqlPlugin
from smarter.apps.plugin.plugin.static import StaticPlugin
from smarter.apps.secret.models import Secret
from smarter.common.utils import get_readonly_yaml_file, to_snake_case
from smarter.lib import json, logging
from smarter.lib.manifest.loader import SAMLoader

logger = logging.getLogger(__name__)

HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.join(HERE, "data")

SQL_CONNECTION_NAME = "test_sql_connection"
SQL_CONNECTION_NAME_2 = "test_sql_connection_2"
API_CONNECTION_NAME = "test_api_connection"
API_CONNECTION_NAME_2 = "test_api_connection_2"
SQL_PLUGIN_NAME = "test_sql_plugin"
API_PLUGIN_NAME = "test_api_plugin"
STATIC_PLUGIN_NAME = "test_static_plugin"
STATIC_EDGE_CASES_PLUGIN_NAME = "test_static_plugin_edge_cases"
SKILL_PLUGIN_NAME = "test_skill_plugin"
SKILL_REMOTE_PLUGIN_NAME = "test_skill_plugin_remote"

# the fictitious GitHub repository that FakeSkillHost serves from ./data/skill-remote.
# these must match ./data/skill-plugin-remote.yaml
SKILL_REMOTE_PATH = os.path.join(DATA_PATH, "skill-remote")
SKILL_REMOTE_OWNER = "example-org"
SKILL_REMOTE_REPO = "skills"
SKILL_REMOTE_REF = "main"
SKILL_REMOTE_DIRECTORY = "skills/test-skill"
SKILL_REMOTE_URL = (
    f"https://github.com/{SKILL_REMOTE_OWNER}/{SKILL_REMOTE_REPO}/tree/{SKILL_REMOTE_REF}/{SKILL_REMOTE_DIRECTORY}"
)
SKILL_REMOTE_TREE_URL = (
    f"https://api.github.com/repos/{SKILL_REMOTE_OWNER}/{SKILL_REMOTE_REPO}/git/trees/{SKILL_REMOTE_REF}?recursive=1"
)
SKILL_REMOTE_RAW_URL = f"https://raw.githubusercontent.com/{SKILL_REMOTE_OWNER}/{SKILL_REMOTE_REPO}/{SKILL_REMOTE_REF}/{SKILL_REMOTE_DIRECTORY}/"
SKILL_SOURCES_REQUESTS_PATCH = "smarter.apps.plugin.plugin.skill_sources.requests.get"
SKILL_SOURCES_DNS_PATCH = "smarter.apps.plugin.plugin.skill_sources.socket.getaddrinfo"
PUBLIC_ADDRESS = "140.82.112.3"

# these must match ./data/sql-plugin.yaml and ./data/api-plugin.yaml
SQL_QUERY = "SELECT {username} AS username, {unit} AS unit;"
API_ENDPOINT = "/api/v1/tests/unauthenticated/{kind}/"

API_REQUEST_PATCH = "smarter.apps.connection.models.api_connection.requests.request"
LIVE_API_PROBE_URL = "http://localhost:9357/api/v1/tests/unauthenticated/list/"


def get_test_data(filename: str) -> dict[str, Any]:
    """Return the contents of a yaml file in ./data."""
    data = get_readonly_yaml_file(os.path.join(DATA_PATH, filename))
    if not isinstance(data, dict):
        raise ValueError(f"Test data {filename} not found in {DATA_PATH}")
    return data


@contextmanager
def capture_signal(signal):
    """Collect the kwargs of every send of a Django signal for the duration of the context."""
    received: list[dict[str, Any]] = []

    def handler(sender, **kwargs):
        received.append({"sender": sender, **kwargs})

    signal.connect(handler, weak=False)
    try:
        yield received
    finally:
        signal.disconnect(handler)


def mock_response(json_data: Any = None, status_code: int = 200) -> mock.MagicMock:
    """Return a mock of a requests.Response."""
    response = mock.MagicMock(spec=requests.Response)
    response.status_code = status_code
    response.json.return_value = json_data
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(f"{status_code} error")
    else:
        response.raise_for_status.return_value = None
    return response


def read_skill_remote_files() -> dict[str, bytes]:
    """Return the files of ./data/skill-remote, keyed by path relative to the skill root."""
    files: dict[str, bytes] = {}
    for root, _, filenames in os.walk(SKILL_REMOTE_PATH):
        for filename in filenames:
            path = os.path.join(root, filename)
            with open(path, "rb") as file:
                files[os.path.relpath(path, SKILL_REMOTE_PATH).replace(os.sep, "/")] = file.read()
    return files


def fake_http_response(content: bytes = b"", status_code: int = 200, headers: Optional[dict] = None) -> mock.MagicMock:
    """Return a mock of a streamed requests.Response."""
    response = mock.MagicMock(spec=requests.Response)
    response.status_code = status_code
    response.headers = headers or {}
    response.iter_content.side_effect = lambda chunk_size=1: iter(
        [content[i : i + chunk_size] for i in range(0, len(content), chunk_size)]
    )
    return response


# pylint: disable=unused-argument
def public_getaddrinfo(host, port, *args, **kwargs):
    """A stand-in for socket.getaddrinfo that resolves every host to a public address."""
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (PUBLIC_ADDRESS, port))]


class FakeSkillHost:
    """
    Serves ./data/skill-remote as the skill at SKILL_REMOTE_URL, in lieu of GitHub.

    It answers the GitHub git trees api, and raw.githubusercontent.com. Other routes can be
    added with :meth:`add`. Every requested URL is recorded in :attr:`requested`.
    """

    def __init__(self):
        self.files = read_skill_remote_files()
        self.routes: dict[str, tuple[bytes, int, dict]] = {}
        self.requested: list[str] = []
        tree = [
            {"path": f"{SKILL_REMOTE_DIRECTORY}/{path}", "type": "blob", "size": len(content)}
            for path, content in self.files.items()
        ]
        tree += [
            {"path": SKILL_REMOTE_DIRECTORY, "type": "tree"},
            {"path": "skills/other-skill/SKILL.md", "type": "blob", "size": 10},
            {"path": "README.md", "type": "blob", "size": 10},
        ]
        self.add(SKILL_REMOTE_TREE_URL, json.dumps({"tree": tree, "truncated": False}).encode("utf-8"))
        for path, content in self.files.items():
            self.add(SKILL_REMOTE_RAW_URL + quote(path), content)

    def add(self, url: str, content: bytes = b"", status_code: int = 200, headers: Optional[dict] = None) -> None:
        """Serve a response for a URL."""
        self.routes[url] = (content, status_code, headers or {})

    def remove(self, url: str) -> None:
        """Stop serving a URL, so that it returns 404."""
        self.routes.pop(url, None)

    # pylint: disable=unused-argument
    def get(self, url, **kwargs) -> mock.MagicMock:
        """A stand-in for requests.get."""
        self.requested.append(url)
        content, status_code, headers = self.routes.get(url, (b"Not Found", 404, {}))
        return fake_http_response(content, status_code, headers)


@contextmanager
def mock_skill_host(host: Optional[FakeSkillHost] = None):
    """Serve remote skills from a FakeSkillHost, and resolve every host to a public address."""
    host = host or FakeSkillHost()
    with (
        mock.patch(SKILL_SOURCES_REQUESTS_PATCH, side_effect=host.get),
        mock.patch(SKILL_SOURCES_DNS_PATCH, side_effect=public_getaddrinfo),
    ):
        yield host


def live_api_is_available(attempts: int = 5) -> bool:
    """Return True if the local Smarter api is reachable from this process."""
    for attempt in range(attempts):
        try:
            return requests.get(LIVE_API_PROBE_URL, timeout=3).status_code == 200
        except requests.exceptions.RequestException:
            # the dev server may be mid-restart. give it a moment.
            if attempt < attempts - 1:
                time.sleep(2)
    return False


# pylint: disable=too-many-instance-attributes,too-many-public-methods
class PluginTestBase(TestAccountMixin):
    """
    Base class for plugin tests.

    Subclasses choose which class-level fixtures they need via
    ``sql_fixtures``, ``api_fixtures`` and ``static_fixtures``:

    - ``sql_connection``, ``sql_connection_2``: SqlConnection Django models.
    - ``sql_plugin``: a SqlPlugin created from ``./data/sql-plugin.yaml``, using ``sql_connection``.
    - ``api_connection``, ``api_connection_2``: ApiConnection Django models.
    - ``api_plugin``: an ApiPlugin created from ``./data/api-plugin.yaml``, using ``api_connection``.
    - ``static_plugin``: a StaticPlugin created from ``./data/static-plugin.yaml``.
    - ``static_edge_cases_plugin``: a StaticPlugin created from ``./data/static-plugin-edge-cases.yaml``.

    The second connection of each kind is used to verify that tool call results
    are cached per connection.
    """

    sql_fixtures: bool = True
    api_fixtures: bool = True
    static_fixtures: bool = False
    skill_fixtures: bool = False

    sql_plugin_yaml: dict
    api_plugin_yaml: dict
    static_plugin_yaml: dict
    static_edge_cases_yaml: dict
    skill_plugin_yaml: dict
    skill_remote_yaml: dict
    api_key: str

    sql_secret: Optional[Secret] = None
    api_secret: Optional[Secret] = None
    api_proxy_secret: Optional[Secret] = None
    sql_connection: SqlConnection
    sql_connection_2: SqlConnection
    api_connection: ApiConnection
    api_connection_2: ApiConnection
    sql_plugin: SqlPlugin
    api_plugin: ApiPlugin
    static_plugin: StaticPlugin
    static_edge_cases_plugin: StaticPlugin
    skill_plugin: SkillPlugin
    skill_remote_plugin: SkillPlugin

    # -------------------------------------------------------------------------
    # class fixtures
    # -------------------------------------------------------------------------
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sql_plugin_yaml = get_test_data("sql-plugin.yaml")
        cls.api_plugin_yaml = get_test_data("api-plugin.yaml")
        cls.static_plugin_yaml = get_test_data("static-plugin.yaml")
        cls.static_edge_cases_yaml = get_test_data("static-plugin-edge-cases.yaml")
        cls.skill_plugin_yaml = get_test_data("skill-plugin.yaml")
        cls.skill_remote_yaml = get_test_data("skill-plugin-remote.yaml")
        if cls.sql_fixtures:
            cls._create_sql_connections()
            cls.sql_plugin = SqlPlugin(manifest=cls.sql_manifest(SQL_PLUGIN_NAME), user_profile=cls.user_profile)
        if cls.api_fixtures:
            cls._create_api_connections()
            cls.api_plugin = ApiPlugin(manifest=cls.api_manifest(API_PLUGIN_NAME), user_profile=cls.user_profile)
        if cls.static_fixtures:
            cls.static_plugin = StaticPlugin(
                manifest=cls.static_manifest(STATIC_PLUGIN_NAME), user_profile=cls.user_profile
            )
            cls.static_edge_cases_plugin = StaticPlugin(
                manifest=cls.static_manifest(STATIC_EDGE_CASES_PLUGIN_NAME, edge_cases=True),
                user_profile=cls.user_profile,
            )
        if cls.skill_fixtures:
            cls.skill_plugin = SkillPlugin(
                manifest=cls.skill_manifest(SKILL_PLUGIN_NAME), user_profile=cls.user_profile
            )
            with mock_skill_host():
                cls.skill_remote_plugin = SkillPlugin(
                    manifest=cls.skill_manifest(SKILL_REMOTE_PLUGIN_NAME, remote=True), user_profile=cls.user_profile
                )

    @classmethod
    def tearDownClass(cls):
        try:
            PluginMeta.objects.filter(user_profile__account=cls.account).delete()
            for name in ("api_connection", "api_connection_2", "sql_connection", "sql_connection_2"):
                connection = cls.__dict__.get(name)
                if connection is not None:
                    connection.delete()
            for secret in (cls.api_secret, cls.api_proxy_secret, cls.sql_secret):
                if secret is not None:
                    secret.delete()
        # pylint: disable=W0718
        except Exception as e:
            logger.warning("%s.tearDownClass() cleanup failed: %s", cls.__name__, e)
        finally:
            super().tearDownClass()

    @classmethod
    def _create_api_connections(cls):
        """
        Create two ApiConnections from ./data/api-connection.yaml. Adapted from.

        ApiConnectionTestMixin, but with secret names that do not collide with
        those of the SqlConnection.
        """
        loader = SAMLoader(manifest=json.dumps(get_test_data("api-connection.yaml")))
        model = SAMApiConnection(**loader.pydantic_model_dump())
        dump = model.spec.connection.model_dump()
        dump["user_profile"] = cls.user_profile
        dump["description"] = model.metadata.description
        dump["kind"] = model.kind

        cls.api_key = dump.pop("apiKey")
        cls.api_secret = secret_factory(
            user_profile=cls.user_profile, name=f"test_api_key_{cls.hash_suffix}", value=cls.api_key
        )
        dump["apiKey"] = cls.api_secret
        cls.api_proxy_secret = secret_factory(
            user_profile=cls.user_profile,
            name=f"test_api_proxy_password_{cls.hash_suffix}",
            value=dump.pop("proxyPassword"),
        )
        dump["proxyPassword"] = cls.api_proxy_secret
        dump = to_snake_case(dump)

        cls.api_connection = ApiConnection(**{**dump, "name": API_CONNECTION_NAME})
        cls.api_connection.save()
        cls.api_connection_2 = ApiConnection(**{**dump, "name": API_CONNECTION_NAME_2})
        cls.api_connection_2.save()

    @classmethod
    def _create_sql_connections(cls):
        """
        Create two SqlConnections from ./data/sql-connection.yaml. Adapted from.

        SqlConnectionTestMixin, but with a secret name that does not collide
        with those of the ApiConnection.
        """
        loader = SAMLoader(manifest=json.dumps(get_test_data("sql-connection.yaml")))
        model = SAMSqlConnection(**loader.pydantic_model_dump())
        dump = model.spec.connection.model_dump()
        dump["user_profile"] = cls.user_profile
        dump["description"] = model.metadata.description

        cls.sql_secret = secret_factory(
            user_profile=cls.user_profile, name=f"test_sql_password_{cls.hash_suffix}", value=dump.pop("password")
        )
        dump["password"] = cls.sql_secret
        dump = to_snake_case(dump)
        dump["kind"] = model.kind

        cls.sql_connection = SqlConnection(**{**dump, "name": SQL_CONNECTION_NAME})
        cls.sql_connection.save()
        cls.sql_connection_2 = SqlConnection(**{**dump, "name": SQL_CONNECTION_NAME_2})
        cls.sql_connection_2.save()

    @classmethod
    def sql_manifest_dict(
        cls, name: str, connection: str = SQL_CONNECTION_NAME, sql_query: str = SQL_QUERY
    ) -> dict[str, Any]:
        """Return a SqlPlugin manifest dict based on ./data/sql-plugin.yaml."""
        data = copy.deepcopy(cls.sql_plugin_yaml)
        data["metadata"]["name"] = name
        data["spec"]["connection"] = connection
        data["spec"]["sqlData"]["sqlQuery"] = sql_query
        return data

    @classmethod
    def sql_manifest(cls, name: str, **kwargs) -> SAMSqlPlugin:
        """Return a SqlPlugin Pydantic manifest based on ./data/sql-plugin.yaml."""
        return SAMSqlPlugin(**cls.sql_manifest_dict(name, **kwargs))

    @classmethod
    def api_manifest_dict(cls, name: str, connection: str = API_CONNECTION_NAME) -> dict[str, Any]:
        """Return an ApiPlugin manifest dict based on ./data/api-plugin.yaml."""
        data = copy.deepcopy(cls.api_plugin_yaml)
        data["metadata"]["name"] = name
        data["spec"]["connection"] = connection
        return data

    @classmethod
    def api_manifest(cls, name: str, **kwargs) -> SAMApiPlugin:
        """Return an ApiPlugin Pydantic manifest based on ./data/api-plugin.yaml."""
        return SAMApiPlugin(**cls.api_manifest_dict(name, **kwargs))

    @classmethod
    def static_manifest_dict(
        cls, name: str, static_data: Optional[dict] = None, edge_cases: bool = False
    ) -> dict[str, Any]:
        """
        Return a StaticPlugin manifest dict based on ./data/static-plugin.yaml, or on.

        ./data/static-plugin-edge-cases.yaml if ``edge_cases``, optionally replacing its staticData.
        """
        data = copy.deepcopy(cls.static_edge_cases_yaml if edge_cases else cls.static_plugin_yaml)
        data["metadata"]["name"] = name
        if static_data is not None:
            data["spec"]["data"]["staticData"] = static_data
        return data

    @classmethod
    def static_manifest(cls, name: str, **kwargs) -> SAMStaticPlugin:
        """Return a StaticPlugin Pydantic manifest.

        See static_manifest_dict().
        """
        return SAMStaticPlugin(**cls.static_manifest_dict(name, **kwargs))

    @classmethod
    def skill_manifest_dict(cls, name: str, remote: bool = False, **skill_data) -> dict[str, Any]:
        """
        Return a SkillPlugin manifest dict based on ./data/skill-plugin.yaml, or on.

        ./data/skill-plugin-remote.yaml if ``remote``, optionally replacing its skillData fields.
        """
        data = copy.deepcopy(cls.skill_remote_yaml if remote else cls.skill_plugin_yaml)
        data["metadata"]["name"] = name
        for key, value in skill_data.items():
            if value is None:
                data["spec"]["skillData"].pop(key, None)
            else:
                data["spec"]["skillData"][key] = value
        return data

    @classmethod
    def skill_manifest(cls, name: str, **kwargs) -> SAMSkillPlugin:
        """Return a SkillPlugin Pydantic manifest.

        See skill_manifest_dict().
        """
        return SAMSkillPlugin(**cls.skill_manifest_dict(name, **kwargs))

    # -------------------------------------------------------------------------
    # test fixtures
    # -------------------------------------------------------------------------
    def setUp(self):
        super().setUp()
        # tool call results are cached. start every test with a clean slate.
        cache.clear()

    def delete_plugin_by_name(self, name: str) -> None:
        """Remove a throwaway plugin, and everything that cascades from it."""
        PluginMeta.objects.filter(user_profile__account=self.account, name=name).delete()

    def delete_plugin_by_id(self, plugin_id: Optional[int]) -> None:
        """Remove a throwaway plugin by id, and everything that cascades from it."""
        PluginMeta.objects.filter(id=plugin_id).delete()

    def new_sql_plugin(self, name: str, **kwargs) -> SqlPlugin:
        """Create a throwaway SqlPlugin that is deleted when the test ends."""
        self.addCleanup(self.delete_plugin_by_name, name)
        return SqlPlugin(manifest=self.sql_manifest(name, **kwargs), user_profile=self.user_profile)

    def new_api_plugin(self, name: str, **kwargs) -> ApiPlugin:
        """Create a throwaway ApiPlugin that is deleted when the test ends."""
        self.addCleanup(self.delete_plugin_by_name, name)
        return ApiPlugin(manifest=self.api_manifest(name, **kwargs), user_profile=self.user_profile)

    def new_static_plugin(self, name: str, **kwargs) -> StaticPlugin:
        """Create a throwaway StaticPlugin that is deleted when the test ends."""
        self.addCleanup(self.delete_plugin_by_name, name)
        return StaticPlugin(manifest=self.static_manifest(name, **kwargs), user_profile=self.user_profile)

    def load_static_plugin(self, edge_cases: bool = False) -> StaticPlugin:
        """Return a fresh instance of a shared StaticPlugin, loaded from the database."""
        plugin = self.static_edge_cases_plugin if edge_cases else self.static_plugin
        return StaticPlugin(plugin_id=plugin.id, user_profile=self.user_profile)

    def new_skill_plugin(self, name: str, host: Optional[FakeSkillHost] = None, **kwargs) -> SkillPlugin:
        """Create a throwaway SkillPlugin that is deleted when the test ends.

        Remote skills are served by ``host``.
        """
        self.addCleanup(self.delete_plugin_by_name, name)
        manifest = self.skill_manifest(name, **kwargs)
        with mock_skill_host(host):
            return SkillPlugin(manifest=manifest, user_profile=self.user_profile)

    def load_skill_plugin(self, remote: bool = False) -> SkillPlugin:
        """Return a fresh instance of a shared SkillPlugin, loaded from the database."""
        plugin = self.skill_remote_plugin if remote else self.skill_plugin
        return SkillPlugin(plugin_id=plugin.id, user_profile=self.user_profile)

    def load_sql_plugin(self) -> SqlPlugin:
        """Return a fresh instance of the shared SqlPlugin, loaded from the database."""
        return SqlPlugin(plugin_id=self.sql_plugin.id, user_profile=self.user_profile)

    def load_api_plugin(self) -> ApiPlugin:
        """Return a fresh instance of the shared ApiPlugin, loaded from the database."""
        return ApiPlugin(plugin_id=self.api_plugin.id, user_profile=self.user_profile)

    def sql_rows(self, plugin: SqlPlugin, function_args: Any) -> list[dict]:
        """Run a SqlPlugin tool call and decode its JSON string result."""
        retval = plugin.tool_call_fetch_plugin_response(function_args)
        self.assertIsInstance(retval, str)
        return json.loads(retval)  # type: ignore[arg-type]

    def api_call(
        self, plugin: ApiPlugin, function_args: Any, json_data: Any = None, status_code: int = 200
    ) -> tuple[Any, mock.MagicMock]:
        """Run an ApiPlugin tool call against a mocked HTTP request."""
        json_data = [{"id": 1}] if json_data is None else json_data
        with mock.patch(API_REQUEST_PATCH, return_value=mock_response(json_data, status_code)) as request:
            retval = plugin.tool_call_fetch_plugin_response(function_args)
        return retval, request
