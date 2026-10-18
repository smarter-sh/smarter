API Connection
================

An API Connection represents a connection to an external API service within the Smarter platform.
It encapsulates the necessary configuration and credentials (``Smarter Secret``) required to interact with the API,

.. literalinclude:: ../../../../../smarter/smarter/apps/connection/data/stackademy/smarter-test-api.yaml.tpl
   :language: yaml
   :caption: Example API Connection Manifest

Technical References
--------------------

- Django ORM Model: :py:class:`smarter.apps.connection.models.ApiConnection`
- :doc:`SAM Broker <../manifest/brokers/api-connection>`
- :doc:`SAM Pydantic Class Reference <../manifest/models/api-connection>`
