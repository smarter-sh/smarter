Smarter Vectorstore
=====================

Overview
--------

A Smarter Vectorstore is a vector database for retrieval-augmented generation (RAG). Your
documents, such as PDFs, product manuals, policies and support articles, are split into chunks,
turned into vectors by an embeddings model, and loaded into it. A question is then answered with
the chunks that are closest to it in meaning, rather than those that share its words, and an
LLM answers from them, citing your own material rather than its training data.

Smarter manages the whole life of the database:

- **Two kinds of database.** `Qdrant <https://qdrant.tech/>`__, either self-hosted, run by Smarter
  on its own Kubernetes cluster, or Qdrant Cloud; and `Pinecone <https://www.pinecone.io/>`__,
  a managed service. A self-hosted database keeps your documents inside your own network.
- **Its lifecycle.** Smarter creates the database, waits for it to become ready, stops it, and
  destroys it, from a manifest and the ``smarter`` CLI.
- **Its documents.** Add PDFs, text, Markdown, CSV, JSON, YAML and HTML, by upload, as text, or by
  URL. Smarter extracts their text, splits, embeds and loads them, and can remove or reload them.
- **Search.** Similarity search, with an optional score threshold, or maximal marginal relevance,
  which favours diverse results, and filters on the documents' metadata.
- **Maintenance.** Celery Beat checks every database's status every few minutes, takes snapshots
  on the manifest's schedule, prunes old ones, and retries documents whose loading was interrupted.

.. note::

   The Smarter Vectorstore is enabled by default. Set the environment variable
   ``SMARTER_ENABLE_VECTORSTORE=false`` to disable it.

.. seealso::

   - :doc:`Smarter Provider <smarter-provider>`: the embeddings model is a Provider's.
   - :doc:`Smarter Connection <smarter-connection>`: a managed database is reached through an ApiConnection.
   - :doc:`Smarter Vectorsearch <smarter-vectorsearch>`: a search configuration of a Vectorstore, for RAG.
   - :doc:`Smarter LLMHost <smarter-llmhost>`: self-host an embeddings model, e.g. BGE-M3, and register it as a Provider.

Example Manifests
-----------------

A self-hosted Qdrant database. The embeddings ``model`` must produce vectors of ``index.dimension``:

.. literalinclude:: ../../../smarter/smarter/apps/vectorstore/data/vectorstores/qdrant-self-hosted.yaml
   :language: yaml
   :caption: qdrant-self-hosted.yaml

A Pinecone database. Its API key is in the ApiConnection named by ``connection``:

.. literalinclude:: ../../../smarter/smarter/apps/vectorstore/data/vectorstores/pinecone.yaml
   :language: yaml
   :caption: pinecone.yaml

More examples, of a larger self-hosted database with deletion protection, and of Qdrant Cloud,
are in ``smarter/apps/vectorstore/data/vectorstores/``. ``manage.py initialize_platform`` applies
them for the Smarter admin, so that every account may use them. They are applied, not deployed,
so that no database is created, nor paid for, until someone deploys one.

Lifecycle
---------

.. code-block:: console

   smarter apply -f qdrant-self-hosted.yaml           # create or update the Vectorstore
   smarter deploy vectorstore example_knowledge_base   # create its database
   smarter describe vectorstore example_knowledge_base # its status, vector count and snapshots
   smarter logs vectorstore example_knowledge_base     # a self-hosted Qdrant server's logs
   smarter undeploy vectorstore example_knowledge_base # stop serving; its data is kept
   smarter delete vectorstore example_knowledge_base   # destroy its database and data

Only account admins may apply, deploy, undeploy and delete Vectorstores. Everyone in the account
may describe and search them.

.. list-table:: Status
   :header-rows: 1

   * - Status
     - Meaning
   * - pending
     - Applied, but not deployed.
   * - provisioning
     - Deployed. Waiting for the database: a new self-hosted Qdrant server takes a minute or two to start.
   * - ready
     - Serving. Documents can be loaded and searched.
   * - stopped
     - Undeployed. A self-hosted server's volume, and so its data, is kept, and a managed index is left as it is. Deploy it again to resume.
   * - failed
     - See its status message. Celery Beat keeps checking, so a transient error clears itself.
   * - deleting
     - Its database is being destroyed.

Once a Vectorstore is deployed, its ``backend``, ``hosting``, index name, dimension and metric,
and a self-hosted server's storage, cannot change, because the database would no longer match.
Delete it, and apply it again, to change them. Its embeddings model can change: its documents are
then loaded again.

A database with ``index.deletionProtection: true`` cannot be destroyed until it is disabled.

Self-Hosted Qdrant
~~~~~~~~~~~~~~~~~~

Each self-hosted Vectorstore gets its own Qdrant server: a Kubernetes StatefulSet with a
persistent volume for its data and snapshots, a ClusterIP Service, and a Secret with an API key
that Smarter generates and keeps in the Smarter Secret ``vectorstore_<name>_api_key``. It runs
the unprivileged Qdrant image, as a non-root user, and is reachable only inside the cluster. Its
size is set by ``spec.selfHosted``: ``storage``, ``storageClass``, ``cpu`` and ``memory``.

Managed Services
~~~~~~~~~~~~~~~~

``manage.py initialize_vectorstore_providers``, which ``initialize_platform`` runs, creates the
ApiConnections of the managed services from these environment variables:

.. list-table::
   :header-rows: 1

   * - Service
     - Environment variables
     - ApiConnection
   * - Pinecone
     - ``PINECONE_API_KEY``
     - ``pinecone``
   * - Qdrant Cloud
     - ``QDRANT_CLOUD_URL``, ``QDRANT_CLOUD_API_KEY``
     - ``qdrant_cloud``

A managed database's index name includes the account number, so that accounts that share a
Pinecone project, or Qdrant Cloud cluster, never collide.

Documents
---------

Documents are added through the REST API, ``/api/v1/vectorstores/<hashed id>/documents/``, or, in
bulk, with ``manage.py load_vectorstore_documents --name <vectorstore> --path <file or folder>``.

.. code-block:: console

   # a file; any number of them, as multipart/form-data
   curl -H "Authorization: Token $SMARTER_API_KEY" -F files=@manual.pdf \
     https://platform.smarter.sh/api/v1/vectorstores/<hashed id>/documents/

   # text, or a public https URL, with metadata that is stored with every chunk
   curl -H "Authorization: Token $SMARTER_API_KEY" -H "Content-Type: application/json" \
     -d '{"url": "https://example.com/faq.html", "metadata": {"source": "faq"}}' \
     https://platform.smarter.sh/api/v1/vectorstores/<hashed id>/documents/

A document's text is extracted when it is added, and kept in Smarter's database. The original
file is never written to file storage, so proprietary documents do not end up in a public bucket.
A document whose text is already in the Vectorstore is not added again. The documents are then
loaded by Celery: split into chunks of ``embeddings.chunkSize`` characters, embedded, and loaded
with deterministic ids, so that a document can be loaded again, or removed, cleanly. Every chunk's
metadata records its document, page and position, and the document's own metadata. PDFs must
have text: a scanned PDF needs OCR first. Documents may be up to 50 MiB.

Search
------

.. code-block:: console

   curl -H "Authorization: Token $SMARTER_API_KEY" -H "Content-Type: application/json" \
     -d '{"query": "How do I reset my password?", "k": 4, "filter": {"source": "faq"}}' \
     https://platform.smarter.sh/api/v1/vectorstores/<hashed id>/search/

``searchType`` is ``similarity`` (the default), ``similarity_score_threshold``, with
``scoreThreshold``, or ``mmr``, with optional ``fetchK`` and ``lambdaMult``. Each result has the
chunk's text, metadata and score.

Maintenance and Snapshots
-------------------------

Celery Beat runs two tasks:

- ``reconcile_vectorstores``, every 5 minutes: it brings deployed databases to ready, e.g. it
  creates a new self-hosted server's collection once the server has started, and records each
  database's status and vector count.
- ``maintain_vectorstores``, hourly: for each ready database, it takes a snapshot if one is due,
  every ``maintenance.snapshotIntervalHours``, deletes the oldest beyond
  ``maintenance.snapshotRetention``, and queues again the documents whose loading was interrupted.

A self-hosted Qdrant snapshot is kept on the server's own volume. A Pinecone snapshot is a
Pinecone backup, kept by Pinecone, which needs a paid Pinecone plan. Qdrant Cloud keeps its own.
Snapshots are listed, taken, and restored through the REST API:

- ``GET`` and ``POST /api/v1/vectorstores/<hashed id>/snapshots/``
- ``POST /api/v1/vectorstores/<hashed id>/snapshots/<id>/restore/``

Restoring replaces the database's data with the snapshot's. Documents loaded after the snapshot
are no longer in the database: load them again.

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   smarter-vectorstore/api
   smarter-vectorstore/backends
   smarter-vectorstore/builtins
   smarter-vectorstore/caching
   smarter-vectorstore/commands
   smarter-vectorstore/documents
   smarter-vectorstore/kubernetes
   smarter-vectorstore/manifest
   smarter-vectorstore/models
   smarter-vectorstore/receivers
   smarter-vectorstore/serializers
   smarter-vectorstore/services
   smarter-vectorstore/signals
   smarter-vectorstore/tasks
   smarter-vectorstore/views
