"""
Test :mod:`smarter.apps.connection.ssh`, and SQL queries through an SSH tunnel, against a real SSH server.

The SSH server is paramiko's, in this process: it accepts one login, and forwards ``direct-tcpip``
channels to their destination, as OpenSSH's ``AllowTcpForwarding`` does. The tests tunnel to a TCP echo
server, and to the test stack's own database.
"""

import socket
import threading
from typing import Optional
from unittest import mock

import paramiko
from django.db import connection as django_connection
from paramiko.common import AUTH_FAILED, AUTH_SUCCESSFUL, OPEN_SUCCEEDED

from smarter.apps.connection.execution import (
    SqlToolCall,
    SshTunnelSettings,
    execute_sql_call,
)
from smarter.apps.connection.ssh import SshTunnel, SshTunnelError, host_keys_from_text
from smarter.lib import json
from smarter.lib.unittest.base_classes import SmarterTestBase

SSH_USERNAME = "tunnel"
SSH_PASSWORD = "test-ssh-password-value"


class ForwardingServer(paramiko.ServerInterface):
    """An SSH server's policy: one password login, and port forwarding to any destination."""

    def __init__(self):
        self.destinations: list[tuple[str, int]] = []

    def get_allowed_auths(self, username):
        return "password"

    def check_auth_password(self, username, password):
        if username == SSH_USERNAME and password == SSH_PASSWORD:
            return AUTH_SUCCESSFUL
        return AUTH_FAILED

    def check_channel_direct_tcpip_request(self, chanid, origin, destination):
        self.destinations.append(destination)
        return OPEN_SUCCEEDED


def pump(first, second, stop: threading.Event) -> None:
    """Copy bytes both ways between two socket-like objects until either closes."""
    import select  # pylint: disable=import-outside-toplevel

    while not stop.is_set():
        readable, _writable, _errored = select.select([first, second], [], [], 0.5)
        for source in readable:
            data = source.recv(32768)
            if not data:
                return
            target = second if source is first else first
            target.sendall(data)


class FakeSshServer:
    """A real SSH server, in a thread, on a loopback port, that forwards direct-tcpip channels."""

    def __init__(self, host_key: paramiko.PKey):
        self.host_key = host_key
        self.policy = ForwardingServer()
        self.stop = threading.Event()
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(4)
        self.listener.settimeout(0.5)
        self.port = self.listener.getsockname()[1]
        self.transports: list[paramiko.Transport] = []
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def known_hosts(self, key: Optional[paramiko.PKey] = None) -> str:
        """The server's line of known_hosts, with its key or another."""
        key = key or self.host_key
        return f"[127.0.0.1]:{self.port} {key.get_name()} {key.get_base64()}\n"

    def serve(self) -> None:
        while not self.stop.is_set():
            try:
                client, _address = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            transport = paramiko.Transport(client)
            transport.add_server_key(self.host_key)
            self.transports.append(transport)
            try:
                transport.start_server(server=self.policy)
            except (paramiko.SSHException, EOFError):
                continue
            threading.Thread(target=self.serve_channels, args=(transport,), daemon=True).start()

    def serve_channels(self, transport: paramiko.Transport) -> None:
        while not self.stop.is_set() and transport.is_active():
            channel = transport.accept(timeout=0.5)
            if channel is None:
                continue
            host, port = self.policy.destinations[-1]
            try:
                target = socket.create_connection((host, port), timeout=5)
            except OSError:
                channel.close()
                continue
            threading.Thread(target=self.forward, args=(channel, target), daemon=True).start()

    def forward(self, channel, target) -> None:
        try:
            pump(channel, target, self.stop)
        finally:
            channel.close()
            target.close()

    def close(self) -> None:
        self.stop.set()
        self.listener.close()
        for transport in self.transports:
            transport.close()
        self.thread.join(timeout=2)


class EchoServer:
    """A TCP server, in a thread, on a loopback port, that sends back what it receives."""

    def __init__(self):
        self.stop = threading.Event()
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(4)
        self.listener.settimeout(0.5)
        self.port = self.listener.getsockname()[1]
        threading.Thread(target=self.serve, daemon=True).start()

    def serve(self) -> None:
        while not self.stop.is_set():
            try:
                client, _address = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            with client:
                data = client.recv(1024)
                client.sendall(data)

    def close(self) -> None:
        self.stop.set()
        self.listener.close()


class TestSshTunnel(SmarterTestBase):
    """Test the SSH tunnel against a real SSH server."""

    host_key: paramiko.RSAKey
    other_key: paramiko.RSAKey

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.host_key = paramiko.RSAKey.generate(2048)
        cls.other_key = paramiko.RSAKey.generate(2048)

    def setUp(self):
        super().setUp()
        self.ssh_server = FakeSshServer(self.host_key)
        self.addCleanup(self.ssh_server.close)
        self.echo_server = EchoServer()
        self.addCleanup(self.echo_server.close)

    def tunnel(self, known_hosts: Optional[str] = None, password: str = SSH_PASSWORD, port: int = 0) -> SshTunnel:
        """Return a tunnel through the test SSH server to the echo server."""
        if known_hosts is None:
            known_hosts = self.ssh_server.known_hosts()
        tunnel = SshTunnel(
            ssh_host="127.0.0.1",
            ssh_port=port or self.ssh_server.port,
            username=SSH_USERNAME,
            password=password,
            known_hosts=known_hosts,
            remote_host="127.0.0.1",
            remote_port=self.echo_server.port,
            timeout=5,
        )
        return tunnel

    def test_host_keys_from_text(self):
        """Test that known_hosts text is parsed, and that blank lines, comments and junk are skipped."""
        text = "# a comment\n\nnot a key line\n" + self.ssh_server.known_hosts()
        host_keys = host_keys_from_text(text)
        self.assertEqual(list(host_keys.keys()), [f"[127.0.0.1]:{self.ssh_server.port}"])
        self.assertEqual(len(host_keys_from_text(None).keys()), 0)

    def test_tunnel_forwards_bytes(self):
        """Test that bytes sent to the tunnel's local port reach the remote host, through the SSH server, and come back."""
        with self.tunnel() as tunnel:
            with socket.create_connection(("127.0.0.1", tunnel.local_port), timeout=5) as local:
                local.sendall(b"hello through the tunnel")
                self.assertEqual(local.recv(1024), b"hello through the tunnel")
        self.assertEqual(self.ssh_server.policy.destinations[-1], ("127.0.0.1", self.echo_server.port))

    def test_no_known_hosts(self):
        """Test that a tunnel without sshKnownHosts is refused, before connecting, with how to fix it."""
        with self.assertRaises(SshTunnelError) as context:
            self.tunnel(known_hosts="").open()
        self.assertIn("ssh-keyscan", str(context.exception))
        self.assertEqual(self.ssh_server.transports, [])

    def test_unknown_host_key(self):
        """Test that a server whose host isn't in sshKnownHosts is refused, never learned."""
        known_hosts = f"other.example.com {self.host_key.get_name()} {self.host_key.get_base64()}\n"
        with self.assertRaises(SshTunnelError) as context:
            self.tunnel(known_hosts=known_hosts).open()
        self.assertIn("isn't in sshKnownHosts", str(context.exception))

    def test_changed_host_key(self):
        """Test that a server whose host key differs from sshKnownHosts' is refused."""
        with self.assertRaises(SshTunnelError) as context:
            self.tunnel(known_hosts=self.ssh_server.known_hosts(self.other_key)).open()
        self.assertIn("doesn't match", str(context.exception))

    def test_wrong_password(self):
        """Test that a refused login is reported as such."""
        with self.assertRaises(SshTunnelError) as context:
            self.tunnel(password="wrong").open()
        self.assertIn("refused the login", str(context.exception))

    def test_unreachable_server(self):
        """Test that an SSH server that can't be reached is reported as such."""
        unused = socket.socket()
        unused.bind(("127.0.0.1", 0))
        port = unused.getsockname()[1]
        unused.close()
        with self.assertRaises(SshTunnelError) as context:
            self.tunnel(known_hosts=f"[127.0.0.1]:{port} ssh-rsa {self.host_key.get_base64()}\n", port=port).open()
        self.assertIn("could not be reached", str(context.exception))

    def test_close_stops_forwarding(self):
        """Test that the local port stops accepting connections when the tunnel closes."""
        tunnel = self.tunnel().open()
        port = tunnel.local_port
        tunnel.close()
        with self.assertRaises(OSError):
            socket.create_connection(("127.0.0.1", port), timeout=1)

    # =========================================================================
    # a SQL query through the tunnel, to the test stack's database
    # =========================================================================
    def sql_call(self, sql: str, ssh: Optional[SshTunnelSettings]) -> SqlToolCall:
        """Return a query of the test database, through the test SSH server when ``ssh`` is given."""
        settings = django_connection.settings_dict
        call = SqlToolCall(
            engine=settings["ENGINE"],
            database=settings["NAME"],
            username=settings["USER"],
            password=settings["PASSWORD"],
            host=settings["HOST"] or "127.0.0.1",
            port=int(settings["PORT"] or 3306),
            ssh=ssh,
            sql=sql,
            timeout=10,
        )
        return call

    def ssh_settings(self, **fields) -> SshTunnelSettings:
        """Return the test SSH server's settings."""
        values = {
            "host": "127.0.0.1",
            "port": self.ssh_server.port,
            "username": SSH_USERNAME,
            "password": SSH_PASSWORD,
            "known_hosts": self.ssh_server.known_hosts(),
            **fields,
        }
        return SshTunnelSettings(**values)

    def test_sql_query_through_the_tunnel(self):
        """Test that a SqlPlugin's query reaches the database through the SSH tunnel, and returns its rows."""
        result = execute_sql_call(self.sql_call("SELECT 1 AS one;", self.ssh_settings()))
        self.assertIsNone(result.failure, result.failure)
        self.assertEqual(json.loads(str(result.value)), [{"one": 1}])
        settings = django_connection.settings_dict
        self.assertEqual(self.ssh_server.policy.destinations[-1][1], int(settings["PORT"] or 3306))

    def test_sql_query_through_a_refused_tunnel(self):
        """Test that a tunnel that can't be opened fails the call, and nothing reaches the database."""
        result = execute_sql_call(self.sql_call("SELECT 1;", self.ssh_settings(password="wrong")))
        self.assertIn("could not open the SSH tunnel", result.failure or "")
        self.assertEqual(self.ssh_server.policy.destinations, [])

    def test_sql_query_error(self):
        """Test that a query that the database rejects is a result with is_error, not a failure."""
        result = execute_sql_call(self.sql_call("SELECT * FROM no_such_table_anywhere;", None))
        self.assertTrue(result.is_error)
        self.assertIsNone(result.failure)

    def test_sql_call_keeps_its_passwords_out_of_repr(self):
        """Test that neither the database's password nor the SSH tunnel's is in repr()."""
        call = self.sql_call("SELECT 1;", self.ssh_settings())
        self.assertNotIn(SSH_PASSWORD, repr(call))
        # the test database's password is also its name and user, so its field is looked for instead.
        self.assertNotIn("password=", repr(call))
        self.assertEqual(SqlToolCall.model_validate_json(call.model_dump_json()), call)

    def test_sql_kind_is_registered(self):
        """Test that the tool runner finds the SQL executor."""
        from smarter.apps.llmtool.runner import (  # pylint: disable=import-outside-toplevel
            executor_for,
        )

        self.assertIs(executor_for("sql"), execute_sql_call)

    def test_unreachable_database(self):
        """Test that a database that can't be reached is a failure."""
        call = self.sql_call("SELECT 1;", None).model_copy(update={"host": "127.0.0.1", "port": 1})
        with mock.patch.dict(call.options, {"connect_timeout": 2}):
            result = execute_sql_call(call)
        self.assertIn("could not connect to the database", result.failure or "")
