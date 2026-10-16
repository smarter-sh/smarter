Smarter Vectorsearch
=====================

Smarter Vectorsearch is a Django application that provides a framework for executing
semantic search queries against locally-hosted vector databases managed by
:doc:`Smarter Vectorstore <smarter-vectorstore>`. It is fully integrated into the Smarter
Framework, namely the
:doc:`Smarter Application Manifest (SAM) <../smarter-framework/developer-reference/lib/drf/manifest>` yaml manifest-based API.

A Vectorsearch is a named, ownable configuration describing how to query a single
:doc:`Vectorstore <smarter-vectorstore/models>`: which retrieval strategy to use
(similarity, similarity with a score threshold, or maximal marginal relevance),
how many results to return, and any metadata filters to apply. It does not itself
hold embeddings or documents, and it does not generate text -- it is purely the
retrieval half of a retrieval-augmented generation pipeline. Combining a
Vectorsearch with a :doc:`Smarter LLMClient <smarter-llmclient>` yields a complete
RAG solution: the top-k results returned by the Vectorsearch are injected into the
LLMClient's system prompt at inference time, grounding the model's response in the
underlying Vectorstore's content.

The module follows the same operational conventions as the rest of the Smarter
Framework, using feature flags (:doc:`waffle switches <../smarter-framework/developer-reference/lib/django/waffle>`)
to control logging behavior, and exposing full manifest-driven lifecycle
management -- create, apply, describe, and delete -- through the
:doc:`SAMVectorsearchBroker <smarter-vectorsearch/manifest>`. Because a Vectorsearch's
:doc:`Vectorstore and auth Secret <smarter-vectorsearch/models>` are referenced by
name in the manifest spec but held as foreign keys on the underlying ORM model, the
broker is also responsible for resolving those references against the owning
account before every create, update, or read. Overall, the Smarter Vectorsearch
app is architected to be a thin, reusable retrieval layer that any LLMClient in the
Smarter Framework can compose into a RAG pipeline without re-implementing search
logic on a per-integration basis.

.. toctree::
   :maxdepth: 1
   :caption: Technical Reference

   smarter-vectorsearch/api
   smarter-vectorsearch/const
   smarter-vectorsearch/management
   smarter-vectorsearch/manifest
   smarter-vectorsearch/models
   smarter-vectorsearch/serializers
   smarter-vectorsearch/signals
   smarter-vectorsearch/tasks
   smarter-vectorsearch/views
