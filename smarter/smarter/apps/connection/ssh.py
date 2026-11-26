"""
An SSH tunnel to a database, for a SqlConnection whose ``authenticationMethod`` is ``tcpip_ssh``.

A database that isn't reachable from the internet is often reachable through an SSH server, a
"bastion", that is. :class:`SshTunnel` connects to that server, and forwards a port on this machine's
loopback interface to the database's host and port, as the SSH server reaches them. The database
driver then connects to the loopback port, and every byte it sends travels through the SSH
connection. This is what MySQL Workbench and DBeaver call "Standard TCP/IP over SSH".

A SqlConnection describes it with fields it already had:

- ``proxyHost`` and ``proxyPort`` (22 when unset): the SSH server;
- ``proxyUsername`` and ``proxyPassword``: the SSH login;
- ``hostname`` and ``port``: the database, as the SSH server reaches it, e.g. ``127.0.0.1`` and ``3306``
  for a database on the SSH server itself;
- ``sshKnownHosts``: the SSH server's host keys, in ``known_hosts`` format, e.g. the output of
  ``ssh-keyscan -p 22 bastion.example.com``.

**Host keys.** The SSH server's host key must be one of ``sshKnownHosts``. An unknown or changed key is
refused, so that a server in the middle can't read the database's traffic or its password. A key is
never learned on first use: the connection's owner adds it, once, to the manifest.

The tunnel needs no database and no Smarter Secret of its own: the SSH password comes with its
settings, decrypted by the app, so it runs wherever the query runs (ADR-038).
"""

import select
import socket
import threading
from typing import Any, Optional

import paramiko
from paramiko.hostkeys import HostKeyEntry, InvalidHostKey

from smarter.common.exceptions import SmarterValueError

DEFAULT_SSH_PORT = 22
LOOPBACK = "127.0.0.1"
FORWARD_BUFFER_BYTES = 32768
SELECT_TIMEOUT_SECONDS = 1.0


class SshTunnelError(SmarterValueError):
    """The SSH tunnel couldn't be opened: the server can't be reached, its host key isn't known, or the login was refused."""


def host_keys_from_text(known_hosts: Optional[str]) -> paramiko.HostKeys:
    """
    Parse ``known_hosts`` text into paramiko's host keys.

    Blank lines, comments and lines that paramiko can't read are skipped.

    :param known_hosts: The text, e.g. the output of ``ssh-keyscan``.
    :returns: The host keys.
    """
    host_keys = paramiko.HostKeys()
    for line in (known_hosts or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            entry = HostKeyEntry.from_line(stripped)
        except (InvalidHostKey, paramiko.SSHException, ValueError):
            entry = None
        if entry is None or entry.key is None:
            continue
        for hostname in entry.hostnames:
            host_keys.add(hostname, entry.key.get_name(), entry.key)
    return host_keys


class SshTunnel:
    """
    An SSH tunnel from a port on this machine's loopback interface to a remote host and port.

    Use it as a context manager. Inside the ``with`` block, :attr:`local_port` forwards to the remote
    host and port, through the SSH server. On exit, the forwarded connections, the listening socket
    and the SSH connection are closed.

    .. code-block:: python

        with SshTunnel("bastion.example.com", 22, "deploy", password, known_hosts, "127.0.0.1", 3306) as tunnel:
            connect_to_database(host="127.0.0.1", port=tunnel.local_port)

    :param ssh_host: The SSH server.
    :param ssh_port: Its port.
    :param username: The SSH login.
    :param password: Its password.
    :param known_hosts: The SSH server's host keys, in ``known_hosts`` format.
    :param remote_host: The host to forward to, as the SSH server reaches it.
    :param remote_port: The port to forward to.
    :param timeout: Seconds to wait for the SSH server.
    """

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        ssh_host: str,
        ssh_port: int,
        username: Optional[str],
        password: Optional[str],
        known_hosts: Optional[str],
        remote_host: str,
        remote_port: int,
        timeout: float = 30,
    ):
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port or DEFAULT_SSH_PORT
        self.username = username
        self.password = password
        self.known_hosts = known_hosts
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.timeout = timeout
        self.client: Optional[paramiko.SSHClient] = None
        self.server_socket: Optional[socket.socket] = None
        self.local_port: int = 0
        self.closed = threading.Event()
        self.threads: list[threading.Thread] = []

    def __repr__(self) -> str:
        return f"<SshTunnel {self.ssh_host}:{self.ssh_port} -> {self.remote_host}:{self.remote_port}>"

    def open(self) -> "SshTunnel":
        """
        Connect to the SSH server, and start forwarding :attr:`local_port`.

        :returns: This tunnel.
        :raises SshTunnelError: If the SSH server's host key isn't in ``known_hosts``, the login is
            refused, or the server can't be reached.
        """
        host_keys = host_keys_from_text(self.known_hosts)
        if not host_keys.keys():
            raise SshTunnelError(
                f"sshKnownHosts has no host key for the SSH server {self.ssh_host}. Add its key, e.g. the output "
                f"of: ssh-keyscan -p {self.ssh_port} {self.ssh_host}"
            )
        client = paramiko.SSHClient()
        known = client.get_host_keys()
        for hostname, keys in host_keys.items():
            for key_type, key in keys.items():
                known.add(hostname, key_type, key)
        # an unknown or changed host key is refused: it is never learned on first use.
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        try:
            client.connect(
                hostname=self.ssh_host,
                port=self.ssh_port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                banner_timeout=self.timeout,
                auth_timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False,
            )
        except paramiko.BadHostKeyException as e:
            client.close()
            raise SshTunnelError(
                f"the SSH server {self.ssh_host}'s host key doesn't match sshKnownHosts. It may have changed, or "
                "the connection may have been intercepted."
            ) from e
        except paramiko.AuthenticationException as e:
            client.close()
            raise SshTunnelError(f"the SSH server {self.ssh_host} refused the login.") from e
        except (paramiko.SSHException, OSError) as e:
            client.close()
            if "not found in known_hosts" in str(e):
                raise SshTunnelError(
                    f"the SSH server {self.ssh_host}'s host key isn't in sshKnownHosts. Add it, e.g. the output of: "
                    f"ssh-keyscan -p {self.ssh_port} {self.ssh_host}"
                ) from e
            raise SshTunnelError(f"the SSH server {self.ssh_host}:{self.ssh_port} could not be reached: {e}") from e
        self.client = client

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((LOOPBACK, 0))
        server_socket.listen(8)
        server_socket.settimeout(SELECT_TIMEOUT_SECONDS)
        self.server_socket = server_socket
        self.local_port = server_socket.getsockname()[1]
        accept_thread = threading.Thread(target=self.accept_connections, name=f"{self!r} accept", daemon=True)
        accept_thread.start()
        self.threads.append(accept_thread)
        return self

    def accept_connections(self) -> None:
        """Accept connections to :attr:`local_port`, and forward each through its own SSH channel, until the tunnel closes."""
        server_socket = self.server_socket
        if server_socket is None:
            return
        while not self.closed.is_set():
            try:
                local, _address = server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                # the listening socket was closed.
                return
            forward_thread = threading.Thread(target=self.forward, args=(local,), name=f"{self!r} forward", daemon=True)
            forward_thread.start()
            self.threads.append(forward_thread)

    def forward(self, local: socket.socket) -> None:
        """
        Forward one local connection to the remote host and port, through an SSH ``direct-tcpip`` channel.

        :param local: The accepted local connection.
        """
        transport = self.client.get_transport() if self.client else None
        if transport is None or not transport.is_active():
            local.close()
            return
        try:
            channel = transport.open_channel(
                "direct-tcpip",
                (self.remote_host, self.remote_port),
                local.getpeername(),
                timeout=self.timeout,
            )
        except (paramiko.SSHException, OSError):
            local.close()
            return
        try:
            self.pump(local, channel)
        finally:
            channel.close()
            local.close()

    def pump(self, local: socket.socket, channel: paramiko.Channel) -> None:
        """
        Copy bytes both ways between a local connection and its SSH channel, until either end closes.

        :param local: The local connection.
        :param channel: Its SSH channel.
        """
        while not self.closed.is_set():
            # a paramiko Channel has a fileno(), so select() can wait on it beside the socket.
            readers: list[Any] = [local, channel]
            readable, _writable, _errored = select.select(readers, [], [], SELECT_TIMEOUT_SECONDS)
            if local in readable:
                data = local.recv(FORWARD_BUFFER_BYTES)
                if not data:
                    return
                channel.sendall(data)
            if channel in readable:
                data = channel.recv(FORWARD_BUFFER_BYTES)
                if not data:
                    return
                local.sendall(data)

    def close(self) -> None:
        """Stop forwarding, and close the listening socket and the SSH connection."""
        self.closed.set()
        if self.server_socket is not None:
            self.server_socket.close()
            self.server_socket = None
        if self.client is not None:
            self.client.close()
            self.client = None
        for thread in self.threads:
            thread.join(timeout=SELECT_TIMEOUT_SECONDS * 2)
        self.threads = []

    def __enter__(self) -> "SshTunnel":
        return self.open()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


__all__ = ["DEFAULT_SSH_PORT", "SshTunnel", "SshTunnelError", "host_keys_from_text"]
