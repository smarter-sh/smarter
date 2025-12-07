API Connection
================

An API Connection represents a connection to an external API service within the Smarter platform.
It encapsulates the necessary configuration and credentials (``Smarter Secret``) required to interact with the API,

.. literalinclude:: ../../../../../smarter/smarter/apps/plugin/data/sample-connections/smarter-test-api.yaml
   :language: yaml
   :caption: Example API Connection Manifest

Technical References
--------------------

- Django ORM Model: :py:class:`smarter.apps.plugin.models.ApiConnection`
- :doc:`SAM Broker <../sam/brokers/api-connection>`
- :doc:`SAM Pydantic Class Reference <../sam/models/api-connection>`
