Smarter Journal
================

Smarter Journal is a core component of the Smarter Framework, responsible for creating
WORM (Write Once Read Many) structured and auditable
long-term storage of Smarter AI operations, including prompts, completions, metadata, and
resource management operations, among other features.

The journal is written on nearly every api request, and read only to investigate a rare incident,
so it is designed for writing. A journaled response doesn't save its entry: it chooses the entry's
key, returns it in the response's metadata, and queues the entry for a Celery worker, so the request
never waits on the database. Data that Smarter has already saved, such as the chat thread that an
LLMClient's configuration returns, isn't queued with the entry: the entry names its row, and the
worker reads it back, waiting for as long as it takes when another task hasn't written it yet, and
checks it against the SHA-256 of what the client received. The worker stores the entry's request and response documents as
compressed skeletons whose large and repeated parts, such as an LLMClient's tool definitions or the
earlier messages of a conversation, are content-addressed blobs that every entry shares. Each turn
of a conversation stores only its new messages, so a conversation's journal grows linearly with its
length rather than quadratically.

Journal Technical References
-----------------------------

.. toctree::
   :maxdepth: 1

   smarter-journal/enumerations
   smarter-journal/model
   smarter-journal/response
   smarter-journal/response-error
   smarter-journal/contract
   smarter-journal/serializers
   smarter-journal/api
   smarter-journal/signals
