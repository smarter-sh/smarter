..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMCustomDomain
===============

``smarter.models.sam.customdomain``
-----------------------------------

.. py:module:: smarter.models.sam.customdomain

SAM model of the ``CustomDomain`` kind, generated from the Smarter platform's JSON Schema.

Do not edit: run ``scripts/generate_sam_models.py``. See :mod:`smarter.models.sam`.

.. py:class:: SAMCustomDomainMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API CustomDomain Manifest - Metadata class.

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



.. py:class:: SAMCustomDomainSpecConfig

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API CustomDomain Manifest - CustomDomain.spec.config.

   .. py:attribute:: domainName
      :type: str

      CustomDomain.spec.config.domainName[str].

      Required. The domain name, e.g. 'llmclients.example.com'. It cannot be changed once the domain has been registered.



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



.. py:class:: SAMCustomDomainSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API CustomDomain Manifest - CustomDomain.spec.

   .. py:attribute:: config
      :type: SAMCustomDomainSpecConfig

      CustomDomain.spec.config[object].

      Required. The configuration of the CustomDomain.



.. py:class:: SAMCustomDomainStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API CustomDomain Manifest - Status class.

   Read only. Besides ownership, it reports the domain's AWS Route53 hosted zone, whether
   the domain is verified, and its DNS records. The LLMClient that uses it is reported in
   ``dependencies``.

   .. py:attribute:: accountNumber
      :type: str

      CustomDomain.status.accountNumber: The account owner of this CustomDomain.

      Read only.


   .. py:attribute:: awsHostedZoneId
      :type: str | None

      CustomDomain.status.awsHostedZoneId: The AWS Route53 hosted zone of this CustomDomain, once it is registered with smarter deploy.

      Read only.


   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.customdomain.SAMDependency] | None

      Dependencies[List]: The resources that depend on this resource, and that must be deleted, or stop referring to it, before it can be deleted.

      Lists only the resources that you can read. Read only.


   .. py:attribute:: dnsRecords
      :type: list[str] | None

      CustomDomain.status.dnsRecords: The DNS records of this CustomDomain.

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

      CustomDomain.status.username: The Smarter user who created this CustomDomain.

      Read only.


   .. py:attribute:: verificationMessage
      :type: str | None

      CustomDomain.status.verificationMessage: Why the domain is not verified yet, or why its verification failed.

      Read only.


   .. py:attribute:: verificationStatus
      :type: str | None

      CustomDomain.status.verificationStatus: Not Verified, Verifying, Verified or Failed.

      The domain is Verified when its NS records are delegated to its hosted zone, and its TLS certificate is issued. Read only.


   .. py:attribute:: verifiedAt
      :type: datetime.datetime | None

      CustomDomain.status.verifiedAt: When the domain was verified.

      Read only.



.. py:class:: SAMCustomDomain

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - CustomDomain.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMCustomDomainMetadata

      CustomDomain.metadata[obj]: Required, the CustomDomain metadata.


   .. py:attribute:: spec
      :type: SAMCustomDomainSpec

      CustomDomain.spec[obj]: Required, the CustomDomain specification.


   .. py:attribute:: status
      :type: smarter.models.sam.customdomain.SAMCustomDomainStatus | None

      CustomDomain.status[obj]: Optional, Read-only.

      Stateful status information about the CustomDomain.
