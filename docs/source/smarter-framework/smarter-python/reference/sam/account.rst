..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMAccount
==========

``smarter.models.sam.account``
------------------------------

.. py:module:: smarter.models.sam.account

SAM model of the ``Account`` kind, generated from the Smarter platform's JSON Schema.

Do not edit: run ``scripts/generate_sam_models.py``. See :mod:`smarter.models.sam`.

.. py:class:: SAMAccountMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Account Manifest - Metadata class.

   .. py:attribute:: accountNumber
      :type: str | None

      Account.metadata.accountNumber[str].

      Your preassigned 12-digit account number for your Smarter Account in the format '####-####-####'. Read only.


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

      The camelCase name of the manifest resource.


   .. py:attribute:: tags
      :type: list[str] | None

      The tags of the manifest.

      Used for generic resource categorization and search. Example: ['tag1', 'tag2']


   .. py:attribute:: version
      :type: str | None

      The semantic version of the manifest.

      Example: 0.1.0



.. py:class:: SAMAccountSpecConfig

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Account Manifest Account.spec.config.

   .. py:attribute:: address1
      :type: str | None

      Account.spec.configuration.address1[str].

      The primary address for the Account.


   .. py:attribute:: address2
      :type: str | None

      Account.spec.configuration.address2[str].

      Optional. The secondary address for the Account.


   .. py:attribute:: city
      :type: str | None

      Account.spec.configuration.city[str].

      The city for the Account.


   .. py:attribute:: companyName
      :type: str

      Account.spec.configuration.companyName[str].

      The legal entity of your Smarter Account for invoicing and legal correspondence.


   .. py:attribute:: country
      :type: str | None

      Account.spec.configuration.country[str].

      The ISO 3166 country code for the Account. Default: USA.


   .. py:attribute:: currency
      :type: str | None

      Account.spec.configuration.currency[str].

      The primary ISO 4217 currency for the Account. Default: USD.


   .. py:attribute:: language
      :type: str | None

      Account.spec.configuration.language[str].

      The primary BCP 47 language tag for the Account. Default: en-US.


   .. py:attribute:: phoneNumber
      :type: str | None

      Account.spec.configuration.phoneNumber[str].

      The primary phone number for the Account.


   .. py:attribute:: postalCode
      :type: str | None

      Account.spec.configuration.postalCode[str].

      The postal code for the Account.


   .. py:attribute:: state
      :type: str | None

      Account.spec.configuration.state[str].

      The state for the Account.


   .. py:attribute:: timezone
      :type: str | None

      Account.spec.configuration.timezone[str].

      The primary IANA timezone for the Account. Default: America/New_York.



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



.. py:class:: SAMAccountSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Account Manifest Account.spec.

   .. py:attribute:: config
      :type: SAMAccountSpecConfig

      Account.spec.config[object].

      The configuration for the Account.



.. py:class:: SAMAccountStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Account Manifest - Status class.

   .. py:attribute:: adminAccount
      :type: str

      Account.status.adminAccount: The designated Smarter admin user for this Account.

      Read only.


   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.account.SAMDependency] | None

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



.. py:class:: SAMAccount

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
      :type: SAMAccountMetadata

      Account.metadata[obj]: Required, the Account metadata.


   .. py:attribute:: spec
      :type: SAMAccountSpec

      Account.spec[obj]: Required, the Account specification.


   .. py:attribute:: status
      :type: smarter.models.sam.account.SAMAccountStatus | None

      Account.status[obj]: Optional, Read-only.

      Stateful status information about the Account.
