..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMVectorsearch
===============

``smarter.models.sam.vectorsearch``
-----------------------------------

.. py:module:: smarter.models.sam.vectorsearch

SAM model of the ``Vectorsearch`` kind, generated from the Smarter platform's JSON Schema.

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



.. py:class:: SAMVectorsearchMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Vectorsearch Manifest - Metadata class.

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



.. py:class:: SAMVectorsearchStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Vectorsearch Manifest - Status class.

   .. py:attribute:: accountNumber
      :type: str

      Vectorsearch.status.account_number: The account owner of this Vectorsearch.

      Read only.


   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.vectorsearch.SAMDependency] | None

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

      Vectorsearch.status.username: The Smarter user who created this Vectorsearch.

      Read only.



.. py:class:: VectorsearchSearchType

   Bases: :class:`enum.Enum`

   Supported retrieval strategies for a Vectorsearch query.


.. py:class:: SAMVectorsearchSpecConfig

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Vectorsearch Manifest Vectorsearch.spec.config.

   .. py:attribute:: auth_secret_name
      :type: str | None

      Optional name of the Secret used to authenticate against the Vectorstore, if required.


   .. py:attribute:: fetch_k
      :type: Optional

      Number of candidate documents to fetch before MMR re-ranking.

      Only valid when search_type='mmr'.


   .. py:attribute:: is_enabled
      :type: bool | None

      Whether this Vectorsearch is active and eligible to be queried.


   .. py:attribute:: k
      :type: Optional

      Number of top results to return from the search.


   .. py:attribute:: lambda_mult
      :type: Optional

      Diversity vs.

      relevance trade-off for MMR (0.0=max diversity, 1.0=max relevance). Only valid when search_type='mmr'.


   .. py:attribute:: metadata_filter
      :type: dict[str, Any] | None

      Optional metadata filter applied to the Vectorstore query, e.g. {'source': 'faq'}.


   .. py:attribute:: score_threshold
      :type: Optional

      Minimum relevance score a result must meet to be included.

      Only valid when search_type='similarity_score_threshold'.


   .. py:attribute:: search_type
      :type: smarter.models.sam.vectorsearch.VectorsearchSearchType | None

      The retrieval strategy to use when querying the Vectorstore.


   .. py:attribute:: vectorstore_name
      :type: str

      The name of the locally-hosted Vectorstore this search queries against.



.. py:class:: SAMVectorsearchSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Vectorsearch Manifest Vectorsearch.spec.

   .. py:attribute:: config
      :type: SAMVectorsearchSpecConfig

      Vectorsearch.spec.config[object].

      The configuration for the Vectorsearch.



.. py:class:: SAMVectorsearch

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - Vectorsearch.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMVectorsearchMetadata

      Vectorsearch.metadata[obj]: Required, the Vectorsearch metadata.


   .. py:attribute:: spec
      :type: SAMVectorsearchSpec

      Vectorsearch.spec[obj]: Required, the Vectorsearch specification.


   .. py:attribute:: status
      :type: smarter.models.sam.vectorsearch.SAMVectorsearchStatus | None

      Vectorsearch.status[obj]: Optional, Read-only.

      Stateful status information about the Vectorsearch.
