"""Test :mod:`smarter.apps.connection.models.connection_base`, :mod:`smarter.apps.connection.models.utils`, and the parts of :mod:`smarter.apps.connection.models.sql_connection` that need no database server."""

from unittest.mock import MagicMock

from django.urls import reverse

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.connection.models import ApiConnection, ConnectionBase, SqlConnection
from smarter.apps.connection.models.utils import (
    get_cached_connection_detail_view_and_kind,
)
from smarter.apps.connection.urls import ConnectionReverseNames
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError

from .mixins import ApiConnectionTestMixin, SqlConnectionTestMixin


def detail_url(connection, reverse_name: str) -> str:
    return reverse(f"{ConnectionReverseNames.namespace}:{reverse_name}", kwargs={"hashed_id": connection.hashed_id})


class TestApiConnectionModels(ApiConnectionTestMixin):
    """Test ConnectionBase and the connection model utils with an ApiConnection."""

    def test_connection_base_manifest_url(self):
        """Test that ConnectionBase.manifest_url is the detail page of the connection's kind."""
        connection = ConnectionBase.objects.get(pk=self.connection_django_model.pk)  # type: ignore[union-attr]
        self.assertEqual(connection.manifest_url, detail_url(connection, ConnectionReverseNames.api_detailview))

    def test_manifest_url(self):
        """Test that ApiConnection.manifest_url is its detail page."""
        connection = self.connection_django_model
        self.assertEqual(connection.manifest_url, detail_url(connection, ConnectionReverseNames.api_detailview))  # type: ignore[union-attr]

    def test_manifest_url_unsupported_kind(self):
        connection = ConnectionBase(id=1, name="test_unsupported_kind", kind="Plugin")
        with self.assertRaises(SmarterConfigurationError):
            connection.manifest_url  # pylint: disable=W0104

    def test_get_cached_connections_for_user(self):
        self.assertEqual(ConnectionBase.get_cached_connections_for_user(None), [])  # type: ignore[arg-type]
        connections = ConnectionBase.get_cached_connections_for_user(self.admin_user, invalidate=True)
        self.assertIn(self.connection_django_model.pk, [c.pk for c in connections])  # type: ignore[union-attr]
        self.assertEqual(ConnectionBase.get_cached_connections_for_user(self.admin_user), connections)

    def test_get_cached_connection_detail_view_and_kind(self):
        name = self.connection_django_model.name  # type: ignore[union-attr]
        for invalidate in (True, False):
            connection = get_cached_connection_detail_view_and_kind(
                self.admin_user, SAMKinds.API_CONNECTION, name, invalidate=invalidate
            )
            self.assertEqual(connection.pk, self.connection_django_model.pk)  # type: ignore[union-attr]
        self.assertIsNone(
            get_cached_connection_detail_view_and_kind(self.admin_user, SAMKinds.API_CONNECTION, "no_such_connection")
        )
        self.assertIsNone(
            get_cached_connection_detail_view_and_kind(
                self.admin_user, SAMKinds.SQL_CONNECTION, "no_such_connection", invalidate=True
            )
        )
        for kind in (None, SAMKinds.STATIC_PLUGIN):
            with self.subTest(kind=kind), self.assertRaises(SmarterValueError):
                get_cached_connection_detail_view_and_kind(self.admin_user, kind, name)  # type: ignore[arg-type]


class TestSqlConnectionModels(SqlConnectionTestMixin):
    """Test ConnectionBase, the connection model utils and SqlConnection with an SqlConnection."""

    def test_connection_base_manifest_url(self):
        connection = ConnectionBase.objects.get(pk=self.connection_django_model.pk)  # type: ignore[union-attr]
        self.assertEqual(connection.manifest_url, detail_url(connection, ConnectionReverseNames.sql_detailview))

    def test_manifest_url(self):
        """Test that SqlConnection.manifest_url is its detail page."""
        connection = self.connection_django_model
        self.assertEqual(connection.manifest_url, detail_url(connection, ConnectionReverseNames.sql_detailview))  # type: ignore[union-attr]

    def test_get_cached_connection_detail_view_and_kind(self):
        name = self.connection_django_model.name  # type: ignore[union-attr]
        connection = get_cached_connection_detail_view_and_kind(self.admin_user, SAMKinds.SQL_CONNECTION, name)
        self.assertIsInstance(connection, SqlConnection)
        self.assertEqual(connection.pk, self.connection_django_model.pk)  # type: ignore[union-attr]

    def test_paramiko_update_known_hosts_policy(self):
        """Test that an unknown ssh host key is appended to the connection's known hosts."""
        connection = SqlConnection.objects.get(pk=self.connection_django_model.pk)  # type: ignore[union-attr]
        original = connection.ssh_known_hosts
        self.addCleanup(SqlConnection.objects.filter(pk=connection.pk).update, ssh_known_hosts=original)
        key = MagicMock()
        key.get_name.return_value = "ssh-ed25519"
        key.get_base64.return_value = "AAAA"
        policy = SqlConnection.ParamikoUpdateKnownHostsPolicy(connection)

        connection.ssh_known_hosts = None
        policy.missing_host_key(client=None, hostname="db1.example.com", key=key)
        policy.missing_host_key(client=None, hostname="db2.example.com", key=key)
        self.assertEqual(
            SqlConnection.objects.get(pk=connection.pk).ssh_known_hosts,
            "db1.example.com ssh-ed25519 AAAA\ndb2.example.com ssh-ed25519 AAAA\n",
        )
