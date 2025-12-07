SQL Connection
=================

An SQL Connection represents a connection to a remote SQL database from the Smarter platform.
It encapsulates the necessary configuration and credentials (``Smarter Secret``)
required to interact with the SQL Database,

.. literalinclude:: ../../../../../smarter/smarter/apps/plugin/data/sample-connections/smarter-test-db.yaml
   :language: yaml
   :caption: Example SQL Connection Manifest

Technical References
--------------------

- Django ORM Model: :py:class:`smarter.apps.plugin.models.SqlConnection`
- :doc:`SAM Broker <../sam/brokers/sql-connection>`
- :doc:`SAM Pydantic Class Reference <../sam/models/sql-connection>`
