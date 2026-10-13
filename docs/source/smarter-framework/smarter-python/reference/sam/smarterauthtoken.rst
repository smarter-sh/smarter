..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMSmarterAuthToken
===================

``smarter.models.sam.smarterauthtoken``
---------------------------------------

.. py:module:: smarter.models.sam.smarterauthtoken

SAM model of the ``SmarterAuthToken`` kind, generated from the Smarter platform's JSON Schema.

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



.. py:class:: SAMSmarterAuthTokenMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API SmarterAuthToken Manifest - Metadata class.

   .. py:attribute:: annotations
      :type: None | list[dict[str, Union[str, int, float, bool, datetime.date, datetime.datetime, Annotated[str, StringConstraints(strip_whitespace=None, to_upper=None, to_lower=None, strict=None, min_length=None, max_length=None, pattern='^(?!^[-+.]*$)[+-]?0*\\d*\\.?\\d*$')], uuid.UUID, bytes, list, dict[str, Any]]]]

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



.. py:class:: SAMSmarterAuthTokenSpecConfig

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API SmarterAuthToken Manifest SmarterAuthToken.spec.config.

   .. py:attribute:: isActive
      :type: bool | None

      SmarterAuthToken.spec.configuration.isActive[bool].

      Required. Whether the SmarterAuthToken is activated.


   .. py:attribute:: username
      :type: str

      SmarterAuthToken.spec.configuration.username[str].

      The Smarter username to which this SmarterAuthToken is attached.



.. py:class:: SAMSmarterAuthTokenStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API SmarterAuthToken Manifest - Status class.

   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.smarterauthtoken.SAMDependency] | None

      Dependencies[List]: The resources that depend on this resource, and that must be deleted, or stop referring to it, before it can be deleted.

      Lists only the resources that you can read. Read only.


   .. py:attribute:: lastUsedAt
      :type: datetime.datetime | None

      SmarterAuthToken.status.modified: The date in which this SmarterAuthToken was most recently used for authentication.

      Read only.


   .. py:attribute:: modified
      :type: datetime

      The date in which this resource was most recently changed.

      Read only.


   .. py:attribute:: recordLocator
      :type: str

      RecordLocator[String]: An optional identifier used to locate the resource record associated with this manifest.

      Read only.



.. py:class:: SAMSmarterAuthTokenSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API SmarterAuthToken Manifest SmarterAuthToken.spec.

   .. py:attribute:: config
      :type: SAMSmarterAuthTokenSpecConfig

      SmarterAuthToken.spec.config[object].

      The configuration for the SmarterAuthToken.



.. py:class:: SAMSmarterAuthToken

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - SmarterAuthToken.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMSmarterAuthTokenMetadata

      SmarterAuthToken.metadata[obj]: Required, the SmarterAuthToken metadata.


   .. py:attribute:: spec
      :type: SAMSmarterAuthTokenSpec

      SmarterAuthToken.spec[obj]: Required, the SmarterAuthToken specification.


   .. py:attribute:: status
      :type: smarter.models.sam.smarterauthtoken.SAMSmarterAuthTokenStatus | None

      SmarterAuthToken.status[obj]: Optional, Read-only.

      Stateful status information about the SmarterAuthToken.
