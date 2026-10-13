..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMUser
=======

``smarter.models.sam.user``
---------------------------

.. py:module:: smarter.models.sam.user

SAM model of the ``User`` kind, generated from the Smarter platform's JSON Schema.

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



.. py:class:: SAMUserMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API User Manifest - Metadata class.

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


   .. py:attribute:: username
      :type: str

      User.metadata.username[str].

      Required. The Django username of the user.


   .. py:attribute:: version
      :type: str | None

      The semantic version of the manifest.

      Example: 0.1.0



.. py:class:: SAMUserSpecConfig

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API User Manifest User.spec.config.

   .. py:attribute:: email
      :type: str

      User.spec.configuration.email[str].

      The email address of the User.


   .. py:attribute:: firstName
      :type: str | None

      User.spec.configuration.firstName[str].

      Optional. The first name of the User.


   .. py:attribute:: isActive
      :type: bool

      User.spec.configuration.isActive[bool].

      Designates whether this User should be treated as active.


   .. py:attribute:: isStaff
      :type: bool | None

      User.spec.configuration.isStaff[bool].

      Optional. Designates whether the User has admin permissions.


   .. py:attribute:: lastName
      :type: str | None

      User.spec.configuration.lastName[str].

      Optional. The last name of the User.



.. py:class:: SAMUserStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API User Manifest - Status class.

   .. py:attribute:: account_number
      :type: str

      User.status.account_number: The account owner of this User.

      Read only.


   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.user.SAMDependency] | None

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


   .. py:attribute:: username
      :type: str

      User.status.account_number: The Smarter user who created this User.

      Read only.



.. py:class:: SAMUserSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API User Manifest User.spec.

   .. py:attribute:: config
      :type: SAMUserSpecConfig

      User.spec.config[object].

      The configuration for the User.



.. py:class:: SAMUser

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - User.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMUserMetadata

      User.metadata[obj]: Required, the User metadata.


   .. py:attribute:: spec
      :type: SAMUserSpec

      User.spec[obj]: Required, the User specification.


   .. py:attribute:: status
      :type: smarter.models.sam.user.SAMUserStatus | None

      User.status[obj]: Optional, Read-only.

      Stateful status information about the User.
