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

Technical References
--------------------

- Django ORM Model: :py:class:`smarter.apps.connection.models.SqlConnection`
- :doc:`SAM Broker <../manifest/brokers/sql-connection>`
- :doc:`SAM Pydantic Class Reference <../manifest/models/sql-connection>`
