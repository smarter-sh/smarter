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
     description: Sql database connection pwd for smarter_test_db at smarter-mariadb:3306
     name: smarter_test_db
     tags:
       - test
       - sample
       - smarter
     annotations:
       - smarter.sh/smarter-test-db/owner: smarter-test-user
       - smarter.sh/smarter-test-db/creator: QA Team
       - smarter.sh/smarter-test-db/purpose: unit testing
       - smarter.sh/smarter-test-db/release-date: 2024-06-15
       - smarter.sh/smarter-test-db/backward-compatibility: true
     version: 0.1.0
   spec:
     connection:
       authenticationMethod: tcpip
       database: smarter_test_db
       dbEngine: django.db.backends.mysql
       username: smarter_test_user
       hostname: smarter-mariadb
       maxOverflow: 10
       password: smarter_test_user
       poolSize: 5
       port: 3306
       timeout: 30
       useSsl: false

From `connections/sql/smarter-test-db.yaml <https://github.com/smarter-sh/stackademy/blob/main/connections/sql/smarter-test-db.yaml>`__ in the :doc:`Stackademy example project </smarter-framework/smarter-manifests/stackademy>`.

Technical References
--------------------

- Django ORM Model: :py:class:`smarter.apps.connection.models.SqlConnection`
- :doc:`SAM Broker <../manifest/brokers/sql-connection>`
- :doc:`SAM Pydantic Class Reference <../manifest/models/sql-connection>`
