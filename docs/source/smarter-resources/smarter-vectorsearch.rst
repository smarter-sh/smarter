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
RAG solution: the LLMClient offers the Vectorsearch to its model as a search tool,
and the model answers from the passages that its searches return, grounded in the
underlying Vectorstore's content. See `Using a Vectorsearch in an LLMClient`_.

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

Using a Vectorsearch in an LLMClient
------------------------------------

An LLMClient lists the Vectorsearches that it may use in its manifest's ``spec.vectorsearches``,
by name. Each must be one that the LLMClient's owner owns, or that is shared with them.

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: LLMClient
   metadata:
     name: course_advisor
   spec:
     config:
       prompt:
         provider: openai
         defaultModel: gpt-6-luna
     vectorsearches:
       - stackademy_handbook

On every prompt, each of the LLMClient's enabled Vectorsearches is offered to the model as a
function tool. Its description is the Vectorsearch's own ``metadata.description``, which the model
reads to decide when to search, so write it for the model: say what the documents are, and what they
answer. Its one argument is a search query, which the model writes itself. A question that the
documents can't help with costs no search, and a question that needs two searches can make both.

When the model calls the tool, Smarter runs the Vectorsearch exactly as its REST api does, with
:func:`~smarter.apps.vectorsearch.run.run_vectorsearch`: it refuses a disabled Vectorsearch, checks
the Vectorsearch's budget, searches its Vectorstore with the Vectorsearch's search type, ``k``,
score threshold, MMR settings and metadata filter, and returns the passages that it found, most
similar first, each with its text, metadata and score. The model answers from them. An error, such
as a Vectorstore that isn't ready, is returned to the model, which can tell the user.

The workbench's Console shows each search like any other tool call, under the Vectorsearch's name. An
answer that searched a Vectorstore is never served from the cache of first answers, because the
documents can change. A Vectorsearch that an LLMClient uses can't be deleted until the LLMClient no
longer lists it.

.. toctree::
   :maxdepth: 1
   :caption: Technical Reference

   smarter-vectorsearch/api
   smarter-vectorsearch/const
   smarter-vectorsearch/management
   smarter-vectorsearch/manifest
   smarter-vectorsearch/models
   smarter-vectorsearch/run
   smarter-vectorsearch/serializers
   smarter-vectorsearch/signals
   smarter-vectorsearch/tasks
   smarter-vectorsearch/toolkit
   smarter-vectorsearch/views
