..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMSqlConnection
================

``smarter.models.sam.sqlconnection``
------------------------------------

.. py:module:: smarter.models.sam.sqlconnection

SAM model of the ``SqlConnection`` kind, generated from the Smarter platform's JSON Schema.

Do not edit: run ``scripts/generate_sam_models.py``. See :mod:`smarter.models.sam`.

.. py:class:: Connection

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API - generic SQL Connection class.

   .. py:attribute:: authenticationMethod
      :type: str | None

      The authentication method to use for the connection.

      Example: 'Standard TCP/IP', 'Standard TCP/IP over SSH', 'LDAP User/Password'.


   .. py:attribute:: database
      :type: str

      The name of the database to connect to.

      Examples: 'sales' or 'mydb'.


   .. py:attribute:: dbEngine
      :type: str

      A valid SQL database engine. Common db_engines: ['django.db.backends.postgresql', 'django.db.backends.mysql', 'django.db.backends.oracle', 'django.db.backends.sqlite3', 'django.db.backends.mssql', 'django.db.backends.sybase'].


   .. py:attribute:: hostname
      :type: str

      The remote host of the SQL connection.

      Should be a valid internet domain name. Example: 'localhost' or 'mysql.mycompany.com'.


   .. py:attribute:: maxOverflow
      :type: int | None

      The maximum number of connections to allow beyond the pool size.


   .. py:attribute:: password
      :type: str | None

      The password.


   .. py:attribute:: poolSize
      :type: int | None

      The size of the connection pool.


   .. py:attribute:: port
      :type: int | None

      The port of the SQL connection.

      Default values are assigned based on the dbEngine.


   .. py:attribute:: proxyHost
      :type: str | None

      The remote host of the SQL proxy connection.

      Should be a valid internet domain name.


   .. py:attribute:: proxyPassword
      :type: str | None

      The password for the proxy connection.


   .. py:attribute:: proxyPort
      :type: int | None

      The port of the SQL proxy connection.


   .. py:attribute:: proxyUsername
      :type: str | None

      The username for the proxy connection.


   .. py:attribute:: sshKnownHosts
      :type: str | None

      The known_hosts file content for verifying SSH connections.


   .. py:attribute:: sslCa
      :type: str | None

      The Certificate Authority (CA) certificate for verifying the server.


   .. py:attribute:: sslCert
      :type: str | None

      The SSL certificate for the connection, if required.


   .. py:attribute:: sslKey
      :type: str | None

      The SSL key for the connection, if required.


   .. py:attribute:: timeout
      :type: int | None

      The timeout for the database connection in seconds.

      Default is 30 seconds.


   .. py:attribute:: useSsl
      :type: bool | None

      Whether to use SSL/TLS for the connection.


   .. py:attribute:: username
      :type: str | None

      The database username.



.. py:class:: SAMConnectionCommonMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Connection Manifest - common Metadata class.

   .. py:attribute:: annotations
      :type: None | list[dict[str, str | int | float | bool | datetime.date | datetime.datetime | uuid.UUID | bytes | list | dict[str, Any]]]

      The manifest annotations.

      Used for storing arbitrary metadata as
                  key-value pairs. Example: [{'smarter.sh/test-manifest/project-name': 'Scooby dooby do'}]. The
                  key should be a valid url-friendly string. The value accepts
                  multi-line string values (YAML block scalars) and various scalar types including
                  str, int, float, bool, datetime.date, datetime.datetime, decimal.Decimal, uuid.UUID, bytes, list, dict.


   .. py:attribute:: description
      :type: str | None

      The description for this resource.

      Be brief. Keep it under 255 characters.


   .. py:attribute:: name
      :type: str

      The camelCase name of the manifest resource.


   .. py:attribute:: tags
      :type: list[str] | None

      The tags of the manifest.

      Used for generic resource categorization and search. Example: ['tag1', 'tag2']


   .. py:attribute:: version
      :type: str | None

      The semantic version of the manifest.

      Example: 0.1.0



.. py:class:: SAMDependency

   Bases: :class:`smarter.models.sam.base.SAMModel`

   A resource that depends on the resource that a manifest describes.

   .. py:attribute:: kind
      :type: str

      Kind[String]: The SAM kind of the resource that depends on this resource, e.g. LLMClient.

      Read only.


   .. py:attribute:: name
      :type: str

      Name[String]: The name of the resource that depends on this resource.

      Read only.



.. py:class:: SAMSqlConnectionSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Sql Connection Manifest Connection.spec.

   .. py:attribute:: connection
      :type: Connection

      SqlConnection.spec.selector[obj]: the selector logic to use for the SqlConnection.



.. py:class:: SAMConnectionCommonStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Connection Manifest - Status class.

   .. py:attribute:: account_number
      :type: str

      Connection.status.account_number: The account owner of this Connection.

      Read only.


   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.sqlconnection.SAMDependency] | None

      Dependencies[List]: The resources that depend on this resource, and that must be deleted, or stop referring to it, before it can be deleted.

      Lists only the resources that you can read. Read only.


   .. py:attribute:: modified
      :type: datetime

      The date in which this resource was most recently changed.

      Read only.


   .. py:attribute:: recordLocator
      :type: str

      RecordLocator[String]: An optional identifier used to locate the resource record associated with this manifest.

      Read only.


   .. py:attribute:: username
      :type: str

      Connection.status.username: The Smarter user who created this Connection.

      Read only.



.. py:class:: SAMSqlConnection

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - SqlConnection Model.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMConnectionCommonMetadata

      SqlConnection.metadata[obj]: Required, the SqlConnection metadata.


   .. py:attribute:: spec
      :type: SAMSqlConnectionSpec

      SqlConnection.spec[obj]: Required, the SqlConnection specification.


   .. py:attribute:: status
      :type: smarter.models.sam.sqlconnection.SAMConnectionCommonStatus | None

      SqlConnection.status[obj]: Optional, Read-only.

      Stateful status information about the SqlConnection.
