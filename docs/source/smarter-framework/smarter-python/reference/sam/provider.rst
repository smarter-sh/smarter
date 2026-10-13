..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMProvider
===========

``smarter.models.sam.provider``
-------------------------------

.. py:module:: smarter.models.sam.provider

SAM model of the ``Provider`` kind, generated from the Smarter platform's JSON Schema.

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



.. py:class:: SAMProviderMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Provider Manifest - Metadata class.

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



.. py:class:: SAMProviderSpecProvider

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API - generic API Connection class.

   .. py:attribute:: api_key
      :type: str | None

      The name of the Smarter Secret containing the API key to use for verification tests.


   .. py:attribute:: base_url
      :type: str | None

      The base URL for the Provider's API.


   .. py:attribute:: connectivity_test_path
      :type: str | None

      The URL path to test connectivity with the Provider's API.


   .. py:attribute:: contact_email
      :type: pydantic.networks.EmailStr | None

      The contact email of the Provider.


   .. py:attribute:: description
      :type: str | None

      A brief description of the Provider.


   .. py:attribute:: docs_url
      :type: str | None

      The documentation URL of the Provider.


   .. py:attribute:: logo
      :type: str | None

      The logo of the Provider.


   .. py:attribute:: name
      :type: str

      The name of the Provider.

      Case sensitive. Must be unique and not empty, with no leading or trailing whitespace and no special characters. examples: 'OpenAI', 'GoogleAI', 'MetaAI'.


   .. py:attribute:: privacy_policy_url
      :type: str | None

      The privacy policy URL of the Provider.


   .. py:attribute:: support_email
      :type: pydantic.networks.EmailStr | None

      The support email of the Provider.


   .. py:attribute:: terms_of_service_url
      :type: str | None

      The terms of service URL of the Provider.


   .. py:attribute:: website_url
      :type: str | None

      The website_url URL of the Provider.



.. py:class:: SAMProviderStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Provider Manifest - Status class.

   .. py:attribute:: can_activate
      :type: bool | None

      Provider.status.can_activate: Indicates whether this Provider can be activated.

      Read only.


   .. py:attribute:: contact_email_verified
      :type: datetime.datetime | None

      Provider.status.contact_email_verified: The date in which the contact email for this Provider was verified.

      Read only.


   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.provider.SAMDependency] | None

      Dependencies[List]: The resources that depend on this resource, and that must be deleted, or stop referring to it, before it can be deleted.

      Lists only the resources that you can read. Read only.


   .. py:attribute:: is_active
      :type: bool

      Provider.status.is_active: Indicates whether this Provider is currently active. Read only.


   .. py:attribute:: is_deprecated
      :type: bool

      Provider.status.is_deprecated: Indicates whether this Provider is deprecated.

      Read only.


   .. py:attribute:: is_flagged
      :type: bool

      Provider.status.is_flagged: Indicates whether this Provider has been flagged for review.

      Read only.


   .. py:attribute:: is_suspended
      :type: bool

      Provider.status.is_suspended: Indicates whether this Provider is currently suspended.

      Read only.


   .. py:attribute:: is_verified
      :type: bool

      Provider.status.is_verified: Indicates whether this Provider has been verified.

      Read only.


   .. py:attribute:: modified
      :type: datetime

      The date in which this resource was most recently changed.

      Read only.


   .. py:attribute:: ownership_requested
      :type: pydantic.networks.EmailStr | None

      Provider.status.ownership_requested: The Smarter user that has requested ownership of this Provider.

      Read only.


   .. py:attribute:: recordLocator
      :type: str

      RecordLocator[String]: An optional identifier used to locate the resource record associated with this manifest.

      Read only.


   .. py:attribute:: support_email_verified
      :type: datetime.datetime | None

      Provider.status.support_email_verified: The date in which the support email for this Provider was verified.

      Read only.


   .. py:attribute:: tos_accepted_at
      :type: datetime.datetime | None

      Provider.status.tos_accepted_at: The date in which the Terms of Service for this Provider were accepted.

      Read only.


   .. py:attribute:: tos_accepted_by
      :type: pydantic.networks.EmailStr | None

      Provider.status.tos_accepted_by: The Smarter user that accepted the Terms of Service for this Provider.

      Read only.



.. py:class:: SAMProviderSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Api Connection Manifest ApiConnection.spec.

   .. py:attribute:: provider
      :type: SAMProviderSpecProvider

      Provider.spec.selector[obj]: the spec for the Provider.



.. py:class:: SAMProvider

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - Account.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMProviderMetadata

      Provider.metadata[obj]: Required, the Provider metadata.


   .. py:attribute:: spec
      :type: SAMProviderSpec

      Provider.spec[obj]: Required, the Provider specification.


   .. py:attribute:: status
      :type: smarter.models.sam.provider.SAMProviderStatus | None

      Provider.status[obj]: Optional, Read-only.

      Stateful status information about the Provider.
