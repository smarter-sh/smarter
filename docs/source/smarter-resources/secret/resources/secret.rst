Secret Resource
================

A sensitive credential or piece of information that is referenced by other Smarter Resources.
Secrets are used to securely persist data such as API keys, passwords, and tokens.

.. literalinclude:: ../../../example-manifests/secret.yaml
  :language: yaml
  :caption: Sample Secret Manifest

Technical References
--------------------

- Django ORM Model: :py:class:`smarter.apps.secret.models.Secret`
- :doc:`SAM Broker <../sam/brokers/secret>`
- :doc:`SAM Pydantic Class Reference <../sam/models/secret>`
