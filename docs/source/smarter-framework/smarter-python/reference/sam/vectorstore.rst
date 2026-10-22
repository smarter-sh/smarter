..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMVectorstore
==============

``smarter.models.sam.vectorstore``
----------------------------------

.. py:module:: smarter.models.sam.vectorstore

SAM model of the ``Vectorstore`` kind, generated from the Smarter platform's JSON Schema.

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



.. py:class:: SAMVectorstoreEmbeddings

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Vectorstore.spec.embeddings: how documents and queries are turned into vectors.

   .. py:attribute:: batchSize
      :type: Optional

      Vectorstore.__init_\_.embeddings.batchSize: chunks per embeddings request and upsert.


   .. py:attribute:: chunkOverlap
      :type: Optional

      Vectorstore.__init_\_.embeddings.chunkOverlap: characters shared by consecutive chunks.


   .. py:attribute:: chunkSize
      :type: Optional

      Vectorstore.__init_\_.embeddings.chunkSize: characters per chunk.


   .. py:attribute:: dimensions
      :type: Optional

      Vectorstore.__init_\_.embeddings.dimensions: ask the model for vectors of this size, if it supports it, e.g. text-embedding-3.

      It must equal index.dimension.


   .. py:attribute:: model
      :type: str

      Vectorstore.__init_\_.embeddings.model: the embeddings model, e.g. text-embedding-3-small.


   .. py:attribute:: provider
      :type: str

      Vectorstore.__init_\_.embeddings.provider: a Provider with an OpenAI-compatible embeddings API, e.g. openai.



.. py:class:: Metric

   Bases: :class:`enum.Enum`

   Vectorstore.__init__.index.metric: the distance metric.


.. py:class:: SAMVectorstoreIndex

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Vectorstore.spec.index: the index (Pinecone), or collection (Qdrant), of the database.

   .. py:attribute:: deletionProtection
      :type: bool | None

      Vectorstore.__init_\_.index.deletionProtection: refuse to destroy the database.


   .. py:attribute:: dimension
      :type: int

      Vectorstore.__init_\_.index.dimension: of the embeddings model's vectors.


   .. py:attribute:: metric
      :type: smarter.models.sam.vectorstore.Metric | None

      Vectorstore.__init_\_.index.metric: the distance metric.


   .. py:attribute:: name
      :type: Optional

      Vectorstore.__init_\_.index.name: the index or collection's name, in lowercase letters, digits and hyphens.

      Defaults to the manifest's name, with the account number for a managed service.



.. py:class:: SAMVectorstoreMaintenance

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Vectorstore.spec.maintenance: what Celery Beat does, besides checking its status.

   .. py:attribute:: snapshotIntervalHours
      :type: Optional

      Vectorstore.__init_\_.maintenance.snapshotIntervalHours: how often.


   .. py:attribute:: snapshotRetention
      :type: Optional

      Vectorstore.__init_\_.maintenance.snapshotRetention: how many are kept.

      Older ones are deleted.


   .. py:attribute:: snapshots
      :type: bool | None

      Vectorstore.__init_\_.maintenance.snapshots: take Qdrant snapshots, or Pinecone backups.



.. py:class:: SAMVectorstoreMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Vectorstore Manifest - Metadata class.

   .. py:attribute:: annotations
      :type: None | list[dict[str, str | int | float | bool | datetime.date | datetime.datetime | uuid.UUID | bytes | list | dict[str, Any]]]

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



.. py:class:: Cloud

   Bases: :class:`enum.Enum`

   Vectorstore.__init__.pinecone.cloud.


.. py:class:: SAMVectorstorePinecone

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Vectorstore.spec.pinecone: where Pinecone runs a serverless index.

   .. py:attribute:: cloud
      :type: smarter.models.sam.vectorstore.Cloud | None

      Vectorstore.__init_\_.pinecone.cloud.


   .. py:attribute:: region
      :type: Optional

      Vectorstore.__init_\_.pinecone.region.



.. py:class:: SAMVectorstoreSelfHosted

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Vectorstore.spec.selfHosted: the Qdrant server that Smarter runs on Kubernetes.

   .. py:attribute:: cpu
      :type: str | None

      Vectorstore.__init_\_.selfHosted.cpu: requested, e.g. 500m.


   .. py:attribute:: image
      :type: str | None

      Vectorstore.__init_\_.selfHosted.image: the Qdrant image.


   .. py:attribute:: memory
      :type: str | None

      Vectorstore.__init_\_.selfHosted.memory: requested, e.g. 1Gi.


   .. py:attribute:: storage
      :type: str | None

      Vectorstore.__init_\_.selfHosted.storage: the size of its volume, e.g. 10Gi.


   .. py:attribute:: storageClass
      :type: str | None

      Vectorstore.__init_\_.selfHosted.storageClass: of its volume.

      Defaults to the cluster's.



.. py:class:: Backend

   Bases: :class:`enum.Enum`

   Vectorstore.__init__.backend: qdrant or pinecone.


.. py:class:: Hosting

   Bases: :class:`enum.Enum`

   Vectorstore.__init__.hosting: self_hosted, run by Smarter on Kubernetes (qdrant only), or managed, a service reached through the ApiConnection in connection.


.. py:class:: SAMVectorstoreSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Vectorstore Manifest Vectorstore.spec.

   .. py:attribute:: backend
      :type: Backend

      Vectorstore.__init_\_.backend: qdrant or pinecone.


   .. py:attribute:: connection
      :type: str | None

      Vectorstore.__init_\_.connection: managed only.

      The name of an ApiConnection with the service's URL and API key Secret, e.g. https://api.pinecone.io, or a Qdrant Cloud cluster's URL.


   .. py:attribute:: embeddings
      :type: SAMVectorstoreEmbeddings

      Vectorstore.__init_\_.embeddings.


   .. py:attribute:: hosting
      :type: smarter.models.sam.vectorstore.Hosting | None

      Vectorstore.__init_\_.hosting: self_hosted, run by Smarter on Kubernetes (qdrant only), or managed, a service reached through the ApiConnection in connection.


   .. py:attribute:: index
      :type: SAMVectorstoreIndex

      Vectorstore.__init_\_.index.


   .. py:attribute:: isActive
      :type: bool | None

      Vectorstore.__init_\_.isActive: whether it may be used.


   .. py:attribute:: maintenance
      :type: smarter.models.sam.vectorstore.SAMVectorstoreMaintenance | None

      Vectorstore.__init_\_.maintenance.


   .. py:attribute:: pinecone
      :type: smarter.models.sam.vectorstore.SAMVectorstorePinecone | None

      Vectorstore.__init_\_.pinecone: pinecone only.


   .. py:attribute:: selfHosted
      :type: smarter.models.sam.vectorstore.SAMVectorstoreSelfHosted | None

      Vectorstore.__init_\_.selfHosted: self_hosted only.



.. py:class:: SAMVectorstoreStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Vectorstore Manifest - Status class.

   Read only.

   .. py:attribute:: accountNumber
      :type: str

      Vectorstore.status.accountNumber: the owner's account.

      Read only.


   .. py:attribute:: apiKeySecret
      :type: str | None

      Vectorstore.status.apiKeySecret: the Secret with a self-hosted database's API key.


   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.vectorstore.SAMDependency] | None

      Dependencies[List]: The resources that depend on this resource, and that must be deleted, or stop referring to it, before it can be deleted.

      Lists only the resources that you can read. Read only.


   .. py:attribute:: deployedAt
      :type: datetime.datetime | None


   .. py:attribute:: documentCount
      :type: int | None

      Vectorstore.status.documentCount: its documents.


   .. py:attribute:: endpoint
      :type: str | None

      Vectorstore.status.endpoint: where it is reached.


   .. py:attribute:: indexName
      :type: str | None

      Vectorstore.status.indexName: the Pinecone index, or Qdrant collection.


   .. py:attribute:: lastCheckedAt
      :type: datetime.datetime | None


   .. py:attribute:: lastMaintenanceAt
      :type: datetime.datetime | None


   .. py:attribute:: lastSnapshotAt
      :type: datetime.datetime | None


   .. py:attribute:: message
      :type: str | None

      Vectorstore.status.message: why, if it failed.


   .. py:attribute:: modified
      :type: datetime

      The date in which this resource was most recently changed.

      Read only.


   .. py:attribute:: recordLocator
      :type: str

      RecordLocator[String]: An optional identifier used to locate the resource record associated with this manifest.

      Read only.


   .. py:attribute:: snapshotCount
      :type: int | None

      Vectorstore.status.snapshotCount: its snapshots, or backups.


   .. py:attribute:: username
      :type: str

      Vectorstore.status.username: the owner.

      Read only.


   .. py:attribute:: vectorCount
      :type: int | None

      Vectorstore.status.vectorCount: as of lastCheckedAt.


   .. py:attribute:: vectorstoreStatus
      :type: str

      Vectorstore.status.vectorstoreStatus: pending, provisioning, ready, stopped, failed or deleting.



.. py:class:: SAMVectorstore

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - Vectorstore.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMVectorstoreMetadata

      Vectorstore.metadata[obj]: Required, the Vectorstore metadata.


   .. py:attribute:: spec
      :type: SAMVectorstoreSpec

      Vectorstore.spec[obj]: Required, the Vectorstore specification.


   .. py:attribute:: status
      :type: smarter.models.sam.vectorstore.SAMVectorstoreStatus | None

      Vectorstore.status[obj]: Optional, Read-only.

      Stateful status information about the Vectorstore.
