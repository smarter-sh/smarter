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
import time
from contextlib import contextmanager
from typing import Any, Optional
from unittest import mock

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
from smarter.apps.plugin.manifest.models.sql_plugin.model import SAMSqlPlugin
from smarter.apps.plugin.manifest.models.static_plugin.model import SAMStaticPlugin
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.plugin.api import ApiPlugin
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


# pylint: disable=too-many-instance-attributes
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

    sql_plugin_yaml: dict
    api_plugin_yaml: dict
    static_plugin_yaml: dict
    static_edge_cases_yaml: dict
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
