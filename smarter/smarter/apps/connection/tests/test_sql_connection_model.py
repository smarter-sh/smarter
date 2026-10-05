"""Test the methods of :class:`smarter.apps.connection.models.SqlConnection` that connect to a database and query it, with an in-memory SQLite database, so that no database server is needed."""

from unittest.mock import MagicMock, patch

import requests

from smarter.apps.connection.manifest.models.sql_connection.enum import (
    DbEngines,
    DBMSAuthenticationMethods,
)
from smarter.apps.connection.models import SqlConnection
from smarter.apps.secret.models import Secret
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json
from smarter.lib.unittest.base_classes import SmarterTestBase


def sqlite_connection(**kwargs) -> SqlConnection:
    """An unsaved SqlConnection to an in-memory SQLite database."""
    fields = {
        "name": "test_sqlite_connection",
        "db_engine": DbEngines.SQLITE.value,
        "database": ":memory:",
        "hostname": "localhost",
        "port": 0,
        "username": "test_user",
        "authentication_method": DBMSAuthenticationMethods.NONE.value,
        "timeout": 5,
    }
    fields.update(kwargs)
    return SqlConnection(**fields)


class TestSqlConnectionModel(SmarterTestBase):
    """Test connecting, querying, and the connection's settings and strings."""

    def test_connect_and_query(self):
        """Test that the connection is established, queried, and closed, with and without a limit."""
        connection = sqlite_connection()
        self.assertTrue(connection.test_connection())
        self.assertTrue(connection.validate())
        rows = json.loads(connection.execute_query("SELECT 1 AS one UNION SELECT 2 AS one;"))
        self.assertEqual([row["one"] for row in rows], [1, 2])
        rows = json.loads(connection.execute_query("SELECT 1 AS one UNION SELECT 2 AS one;", limit=1))
        self.assertEqual(len(rows), 1)
        connection.close()
        connection.close()

    def test_tcpip(self):
        connection = sqlite_connection(authentication_method=DBMSAuthenticationMethods.TCPIP.value)
        self.assertTrue(connection.test_connection())

    def test_unknown_authentication_method(self):
        with self.assertRaises(SmarterValueError):
            sqlite_connection(authentication_method="kerberos").get_connection()

    def test_connection_and_query_failures(self):
        """Test that a connection that fails returns None, and a query that fails returns False, as documented."""
        self.assertIsNone(sqlite_connection(db_engine="django.db.backends.no_such_engine").get_connection())
        self.assertFalse(sqlite_connection().execute_query("SELECT * FROM no_such_table"))

    def test_failure_log_masks_password(self):
        """Test that a failed connection is logged with its password masked."""
        password = MagicMock(spec=Secret)
        password.get_secret.return_value = "s3cret"
        connection = sqlite_connection(db_engine="django.db.backends.no_such_engine")
        with (
            patch.object(SqlConnection, "password", password, create=True),
            patch("smarter.apps.connection.receivers.logger") as logger,
        ):
            self.assertIsNone(connection.get_connection())
        logged = str(logger.error.call_args_list)
        self.assertIn("******", logged)
        self.assertNotIn("s3cret", logged)

    def assert_default_database(self, authentication_method: str):
        """Assert that the connection's Django settings are given to ConnectionHandler as its default database."""
        connection = sqlite_connection(authentication_method=authentication_method)
        with (
            patch("smarter.apps.connection.models.sql_connection.ConnectionHandler") as handler,
            patch("smarter.apps.connection.models.sql_connection.paramiko.SSHClient"),
            patch("smarter.apps.connection.models.sql_connection.socket"),
        ):
            try:
                connection.get_connection()
            except Exception:  # pylint: disable=broad-except
                pass
        databases = handler.call_args.args[0]
        self.assertIn("default", databases)
        self.assertEqual(databases["default"]["ENGINE"], DbEngines.SQLITE.value)

    def test_tcpip_default_database(self):
        self.assert_default_database(DBMSAuthenticationMethods.TCPIP.value)

    def test_ldap_default_database(self):
        self.assert_default_database(DBMSAuthenticationMethods.LDAP_USER_PWD.value)

    def test_tcpip_ssh_default_database(self):
        self.assert_default_database(DBMSAuthenticationMethods.TCPIP_SSH.value)

    def test_ldap_options(self):
        connection = sqlite_connection(authentication_method=DBMSAuthenticationMethods.LDAP_USER_PWD.value)
        self.assertEqual(connection.db_options, {"authentication": "LDAP"})

    def test_settings_and_strings(self):
        connection = sqlite_connection(use_ssl=True, ssl_ca="ca", ssl_cert="cert", ssl_key="key")
        self.assertEqual(connection.db_options["ssl"], {"ca": "ca", "cert": "cert", "key": "key"})
        settings = connection.django_db_connection
        self.assertEqual(settings["ENGINE"], DbEngines.SQLITE.value)
        self.assertIsNone(settings["PASSWORD"])
        self.assertIn("test_user:******@localhost", connection.connection_string)
        self.assertNotIn("******", connection.get_connection_string(masked=False))
        self.assertIn("test_sqlite_connection", str(connection))

    def test_password(self):
        """Test that the password is masked, and given to Django unmasked."""
        password = MagicMock(spec=Secret)
        password.get_secret.return_value = "s3cret"
        connection = sqlite_connection()
        with patch.object(SqlConnection, "password", password, create=True):
            self.assertIn(":******@", connection.get_connection_string())
            self.assertIn(":s3cret@", connection.get_connection_string(masked=False))
            self.assertEqual(connection.django_db_connection["PASSWORD"], "s3cret")

    def test_proxy(self):
        connection = sqlite_connection(proxy_protocol="http", proxy_host="proxy.example.com", proxy_port=8080)
        with patch(
            "smarter.apps.connection.models.sql_connection.requests.get", return_value=MagicMock(status_code=200)
        ) as get:
            self.assertTrue(connection.test_proxy())
        self.assertIn("http", get.call_args.kwargs["proxies"])
        with patch(
            "smarter.apps.connection.models.sql_connection.requests.get", side_effect=requests.ConnectionError("down")
        ):
            self.assertFalse(connection.test_proxy())

    def test_proxy_password(self):
        """Test that the proxy url has the proxy password's value, rather than the Secret."""
        password = MagicMock(spec=Secret)
        password.get_secret.return_value = "proxy-s3cret"
        password.__str__.return_value = "<Secret proxy_password>"
        connection = sqlite_connection(proxy_protocol="http", proxy_host="proxy.example.com", proxy_username="u")
        with (
            patch.object(SqlConnection, "proxy_password", password, create=True),
            patch(
                "smarter.apps.connection.models.sql_connection.requests.get", return_value=MagicMock(status_code=200)
            ) as get,
        ):
            connection.test_proxy()
        self.assertIn("u:proxy-s3cret@", get.call_args.kwargs["proxies"]["http"])
