SQL Connection
=================

An SQL Connection represents a connection to a remote SQL database from the Smarter platform.
It encapsulates the necessary configuration and credentials (``Smarter Secret``)
required to interact with the SQL Database,

.. code-block:: yaml
   :caption: Example SQL Connection Manifest

   apiVersion: smarter.sh/v1
   kind: SqlConnection
   metadata:
     description: Read-only connection to Stackademy's course catalogue, the courses table of the stackademy database at smarter-mariadb:3306
     name: stackademy_catalog_db
     tags:
       - stackademy
       - sql
     annotations:
       smarter.sh/stackademy/owner: Stackademy IT
       smarter.sh/stackademy/purpose: the course catalogue, for the Stackademy SQL advisor
     version: 1.0.0
   spec:
     connection:
       authenticationMethod: tcpip
       database: stackademy
       dbEngine: django.db.backends.mysql
       username: stackademy_catalog
       hostname: smarter-mariadb
       maxOverflow: 10
       password: stackademy_catalog_db_password # the name of a Secret, not the password itself
       poolSize: 5
       port: 3306
       timeout: 30
       useSsl: false

From `connections/sql/stackademy-catalog-db.yaml <https://github.com/smarter-sh/stackademy/blob/main/connections/sql/stackademy-catalog-db.yaml>`__ in the :doc:`Stackademy example project </smarter-framework/smarter-manifests/stackademy>`.

Through an SSH tunnel
---------------------

A database that isn't reachable from the internet is often reachable through an SSH server, a
"bastion", that is. With ``authenticationMethod: tcpip_ssh``, Smarter connects to the SSH server,
forwards a local port to the database through it, and connects the database driver to that port, as
MySQL Workbench and DBeaver do for "Standard TCP/IP over SSH". The tunnel is opened for each query,
and closed after it.

.. code-block:: yaml
   :caption: An SQL Connection through an SSH tunnel

   spec:
     connection:
       authenticationMethod: tcpip_ssh
       dbEngine: django.db.backends.mysql
       hostname: 127.0.0.1          # the database, as the SSH server reaches it
       port: 3306
       database: sales
       username: reporting
       password: sales_db_password  # the name of a Secret
       proxyHost: bastion.example.com
       proxyPort: 22
       proxyUsername: tunnel
       proxyPassword: bastion_password  # the name of a Secret
       sshKnownHosts: |
         bastion.example.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA...

- ``proxyHost`` and ``proxyPort`` (22 when unset) are the SSH server, and ``proxyUsername`` and
  ``proxyPassword`` its login. Only password logins are supported.
- ``hostname`` and ``port`` are the database as the SSH server reaches it: ``127.0.0.1`` for a database
  on the SSH server itself, or a host on its private network.
- ``sshKnownHosts`` must hold the SSH server's host key, in ``known_hosts`` format, e.g. the output of
  ``ssh-keyscan -p 22 bastion.example.com``, checked against a fingerprint you trust. A server whose key
  isn't there, or doesn't match, is refused, and the query fails with a message that says which. A key
  is never learned on first use, so that a server in the middle can't read the database's traffic or
  its password.
- The SSH server must allow TCP forwarding (OpenSSH's ``AllowTcpForwarding``).

The tunnel runs wherever the query runs, with the passwords that the app reads from their Secrets, so
it needs nothing of the platform's own. See :mod:`smarter.apps.connection.ssh`.

Technical References
--------------------

- Django ORM Model: :py:class:`smarter.apps.connection.models.SqlConnection`
- :doc:`SAM Broker <../manifest/brokers/sql-connection>`
- :doc:`SAM Pydantic Class Reference <../manifest/models/sql-connection>`
