..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMSecret
=========

``smarter.models.sam.secret``
-----------------------------

.. py:module:: smarter.models.sam.secret

SAM model of the ``Secret`` kind, generated from the Smarter platform's JSON Schema.

Do not edit: run ``scripts/generate_sam_models.py``. See :mod:`smarter.models.sam`.

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



.. py:class:: SAMSecretMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Secret Manifest - Metadata class.

   .. py:attribute:: annotations
      :type: None | list[dict[str, Union[str, int, float, bool, datetime.date, datetime.datetime, Annotated[str, StringConstraints(strip_whitespace=None, to_upper=None, to_lower=None, strict=None, min_length=None, max_length=None, pattern='^(?!^[-+.]*$)[+-]?0*\\d*\\.?\\d*$', ascii_only=None)], uuid.UUID, bytes, list, dict[str, Any]]]]

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

      Secret.metadata.name[str].

      Required. The name of the secret. camelCase, no spaces, no special characters.


   .. py:attribute:: tags
      :type: list[str] | None

      The tags of the manifest.

      Used for generic resource categorization and search. Example: ['tag1', 'tag2']


   .. py:attribute:: version
      :type: str | None

      The semantic version of the manifest.

      Example: 0.1.0



.. py:class:: SAMSecretSpecConfig

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Secret Manifest Secret.spec.config.

   .. py:attribute:: expiration_date
      :type: datetime.datetime | None

      Secret.spec.configuration.expiration_date[str].

      Optional. The expiration date of the Secret.


   .. py:attribute:: value
      :type: str

      Secret.spec.configuration.value[str].

      Required. The unencrypted value of the Secret.



.. py:class:: SAMSecretStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Secret Manifest - Status class (read-only, like Kubernetes status attributes).

   .. py:attribute:: accountNumber
      :type: str

      Secret.status.account_number: The account owner of this Secret.

      Read only.


   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.secret.SAMDependency] | None

      Dependencies[List]: The resources that depend on this resource, and that must be deleted, or stop referring to it, before it can be deleted.

      Lists only the resources that you can read. Read only.


   .. py:attribute:: last_accessed
      :type: datetime.datetime | None

      Secret.status.last_accessed: The date in which this Secret was most recently accessed.

      Read only.


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

      Secret.status.account_number: The Smarter user who created this Secret.

      Read only.



.. py:class:: SAMSecretSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Secret Manifest Secret.spec.

   .. py:attribute:: config
      :type: SAMSecretSpecConfig

      Secret.spec.config[object].

      The configuration for the Secret.



.. py:class:: SAMSecret

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - Secret.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMSecretMetadata

      Secret.metadata[obj]: Required, the Secret metadata.


   .. py:attribute:: spec
      :type: SAMSecretSpec

      Secret.spec[obj]: Required, the Secret specification.


   .. py:attribute:: status
      :type: smarter.models.sam.secret.SAMSecretStatus | None

      Secret.status[obj]: Optional, Read-only.

      Stateful status information about the Secret.
