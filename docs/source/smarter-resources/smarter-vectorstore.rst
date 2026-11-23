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
   ``SMARTER_APP_VECTORSTORE_ENABLE=false`` to disable it.

.. seealso::

   - :doc:`Smarter Provider <smarter-provider>`: the embeddings model is a Provider's.
   - :doc:`Smarter Connection <smarter-connection>`: a managed database is reached through an ApiConnection.
   - :doc:`Smarter Vectorsearch <smarter-vectorsearch>`: a search configuration of a Vectorstore, for RAG.
   - :doc:`Smarter LLMHost <smarter-llmhost>`: self-host an embeddings model, e.g. BGE-M3, and register it as a Provider.

Example Manifests
-----------------

A self-hosted Qdrant database. The embeddings ``model`` must produce vectors of ``index.dimension``:

.. literalinclude:: /_example-manifests/smarter/vectorstores/qdrant-self-hosted.yaml
   :language: yaml
   :caption: qdrant-self-hosted.yaml

From `vectorstores/qdrant-self-hosted.yaml <https://github.com/smarter-sh/example-manifests/blob/main/smarter/vectorstores/qdrant-self-hosted.yaml>`__ in the :doc:`example manifests repository </smarter-framework/smarter-manifests/example-manifests>`.

A Pinecone database. Its API key is in the ApiConnection named by ``connection``:

.. literalinclude:: /_example-manifests/smarter/vectorstores/pinecone.yaml
   :language: yaml
   :caption: pinecone.yaml

From `vectorstores/pinecone.yaml <https://github.com/smarter-sh/example-manifests/blob/main/smarter/vectorstores/pinecone.yaml>`__ in the :doc:`example manifests repository </smarter-framework/smarter-manifests/example-manifests>`.

More examples, of a larger self-hosted database with deletion protection, and of Qdrant Cloud,
are in the ``smarter/vectorstores/`` folder of the :doc:`example manifests repository </smarter-framework/smarter-manifests/example-manifests>`. ``manage.py initialize_platform``
applies them for the Smarter admin, so that every account may use them. They are applied, not deployed,
so that no database is created, nor paid for, until someone deploys one.

Lifecycle
---------

.. code-block:: console

   smarter apply -f qdrant-self-hosted.yaml           # create or update the Vectorstore
   smarter deploy vectorstore example_knowledge_base   # create its database, in the background
   smarter describe vectorstore example_knowledge_base # its status, conditions, vector count and snapshots
   smarter documents vectorstore example_knowledge_base --add manual.pdf  # add a document
   smarter documents vectorstore example_knowledge_base                   # its documents, and their status
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
     - Deployed. Waiting for the database: a new Pinecone index takes a minute or two to initialize, and a self-hosted Qdrant server several minutes to start. See its conditions.
   * - ready
     - Serving. Documents can be loaded and searched.
   * - stopped
     - Undeployed. A self-hosted server's volume, and so its data, is kept, and a managed index is left as it is. Deploy it again to resume.
   * - failed
     - The deploy gave up, or a check of a ready database failed. See its status message and ``lastError``. Celery Beat keeps checking a deployed database, so a transient error clears itself.
   * - deleting
     - Its database is being destroyed.

Once a Vectorstore is deployed, its ``backend``, ``hosting``, index name, dimension and metric,
and a self-hosted server's storage, cannot change, because the database would no longer match.
Delete it, and apply it again, to change them. Its embeddings model can change: its documents are
then loaded again.

A database with ``index.deletionProtection: true`` cannot be destroyed until it is disabled.

Deploying
~~~~~~~~~

Creating a vector database takes minutes, and has several independent points of failure: the
managed service must accept the api key, a self-hosted server needs a volume, an image and a pod
that starts, and the index must be created and initialized. So ``smarter deploy`` returns at
once, ``provisioning``, and a Celery task creates the database in the background:

- **What can be checked at once is checked by deploy itself**: a Vectorstore that isn't active,
  or an api key that Pinecone or Qdrant Cloud refuses, is an error now, not a deploy that fails
  minutes later.
- **The task checks the database every 15 seconds** while it waits, e.g. for a volume to be
  provisioned, without holding a worker between checks.
- **An error is retried**, after a wait that doubles with each error in a row, up to 5 minutes,
  e.g. a timeout, or a cluster that is briefly unavailable. An error that retrying can't fix, e.g.
  a refused api key, or a request that the service rejects, fails the deploy at once.
- **The deploy fails after 80 checks**, about 20 minutes, with what it was still waiting for.

Follow a deploy with ``smarter describe``. Its ``status`` shows the deploy's progress:

.. code-block:: yaml

   status:
     vectorstoreStatus: provisioning
     message: "ImagePullBackOff: Back-off pulling image qdrant/qdrant:v1.99.0-unprivileged"
     conditions:
       - type: Credentials
         status: "True"
         reason: Accepted
         message: Smarter generated the server's api key.
       - type: Volume
         status: "True"
         reason: Bound
         message: The volume is bound.
       - type: Server
         status: "False"
         reason: ImagePullBackOff
         message: "ImagePullBackOff: Back-off pulling image qdrant/qdrant:v1.99.0-unprivileged"
       - type: Index
         status: Unknown
         reason: Pending
         message: The index is created once the database is ready.
     attempt: 6
     maxAttempts: 80
     nextRetryAt: "2026-11-23T16:05:15Z"
     lastError: null

Each condition is one thing that the database needs, as in Kubernetes: ``True`` when it is met,
``False`` when it isn't, with a one-word ``reason``, and ``Unknown`` before it is checked. Its
``lastTransitionTime`` says how long it has been so. A Pinecone or Qdrant Cloud Vectorstore has the
conditions ``Credentials`` and ``Index``, and a self-hosted one also ``Volume`` and ``Server``.
``lastError`` is the deploy's last error, which may have been retried since. The REST api's
vectorstore, which the web console shows, has the same fields.

A new deploy replaces one in progress, and ``undeploy`` ends it.

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
     - ``APP_VECTORSTORE_PINECONE_API_KEY``
     - ``pinecone``
   * - Qdrant Cloud
     - ``APP_VECTORSTORE_QDRANT_CLOUD_URL``, ``APP_VECTORSTORE_QDRANT_CLOUD_API_KEY``
     - ``qdrant_cloud``

A managed database's index name includes the account number, so that accounts that share a
Pinecone project, or Qdrant Cloud cluster, never collide.

Documents
---------

Documents are added in the web console, in the Documents section of a Vectorstore's details,
where files can be dropped or chosen and a public url added, each document's status followed as
it loads, and a document removed, or with the ``smarter`` cli's ``documents`` command:

.. code-block:: console

   smarter documents vectorstore example_knowledge_base --add manual.pdf --add faq.md
   smarter documents vectorstore example_knowledge_base --url https://example.com/faq.html
   smarter documents vectorstore example_knowledge_base --remove faq.md

They can also be added through the REST API,
``/api/v1/vectorstores/<hashed id>/documents/``, or, in bulk, with
``manage.py load_vectorstore_documents --name <vectorstore> --path <file or folder>``. Only a
Vectorstore's owner may add or remove its documents. Anyone it is shared with may see them.

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
A document whose text is already in the Vectorstore is not added again. Documents may be added
before the Vectorstore is deployed: they wait, and are loaded as soon as its deploy is ready. The
documents are loaded by Celery: split into chunks of ``embeddings.chunkSize`` characters, embedded, and loaded
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

- ``reconcile_vectorstores``, every 5 minutes: it checks each deployed database, records its
  status, conditions and vector count, and creates an index that has gone missing. It leaves a
  deploy in progress to its own task, unless that task was lost, e.g. in a worker's restart, and
  then it finishes the deploy itself.
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
   smarter-vectorstore/caching
   smarter-vectorstore/commands
   smarter-vectorstore/deployment
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
