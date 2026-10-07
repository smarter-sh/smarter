Smarter Journal
===============

The Smarter Journal is the Smarter API's permanent record of what was asked and
what was answered. When it is enabled, every journaled API response is also
written to the journal as one entry: the HTTP request as Django received it, the
JSON response that Smarter sent back, the user who made the request, the
resource kind and command involved, and the HTTP status code.

This page describes the journal from the API's point of view: what it records,
what it adds to responses, how to turn it on, and how to plan for its storage.
For the platform administrator's view, see
:doc:`../../smarter-platform/smarter-journal`. For the Python classes, see
:doc:`../developer-reference/smarter-journal`.

Why a Journal
-------------

Organizations that run LLM applications often have to keep a record of them for
legal and regulatory reasons: which prompts were sent, which completions came
back, and who changed which resources and when. That record has to be kept for
years, and it has to be complete.

That kind of data is large, it grows with every request, and it is almost never
read. Prompt completions, manifests and error reports are big, loosely
structured JSON documents. Keeping them inside the normalized tables that run
the platform day to day would be expensive, and it would slow those tables down
as they grew. Online transaction processing (OLTP) databases such as MariaDB
are built for many small, structured reads and writes. They are a costly place
to keep years of bulky records that nobody queries.

The journal is designed around that workload:

- **Write once.** An entry is created as the response is built and is never
  updated by Smarter afterwards.
- **Read rarely.** Entries are retrieved one at a time by key or by date, for
  an audit or an investigation, not by the running application.
- **Schema-light.** The request and response are stored as JSON documents, so
  the journal never needs a migration when a resource's manifest or a
  response's shape changes.
- **Separate from operational data.** Nothing in the platform reads the journal
  to do its job, so it can be moved, archived or tiered to low-cost storage on
  its own schedule without affecting the running platform.

The journal is not Smarter's application log. Application logs and the Django
admin log are short-lived diagnostic tools that are routinely purged; see
:doc:`logging`. The journal is the auditable record.

What Is Journaled
-----------------

An API view takes part in the journal by returning a
:class:`~smarter.lib.journal.http.SmarterJournaledJsonResponse`, or its error
counterpart :class:`~smarter.lib.journal.http.SmarterJournaledJsonErrorResponse`,
instead of a plain Django ``JsonResponse``. All of the following do:

- **Every CLI command** under ``/api/v1/cli/``: ``apply``, ``delete``,
  ``deploy``, ``undeploy``, ``describe``, ``get``, ``logs``, ``validate``,
  ``example_manifest``, ``json_schema``, ``chat_config``, ``prompt``,
  ``status``, ``version``, ``whoami`` and ``resources``. Each resource kind's
  broker builds its responses with these classes, so every resource you manage
  through the :doc:`CLI <cli>` is covered.
- **Prompts** sent to an LLMClient, and prompts sent through the provider
  passthrough endpoint. See :doc:`chat`.
- **Errors**, including failed authentication. When the token authentication
  middleware rejects a request, its ``401`` response is journaled too, so the
  journal also records attempts that never reached a view. See
  :doc:`authentication` and :doc:`error-handling`.

Successful and failed requests are journaled the same way. An error entry holds
the error response, including the exception class, description and stack trace,
along with its status code.

Enabling the Journal
--------------------

The journal is off by default. It is controlled by the ``enable_journal``
switch, a `django-waffle <https://waffle.readthedocs.io/>`_ feature switch that
a superuser turns on or off in the Django admin console under **Waffle >
Switches**.

The switch is checked on every response, so the change takes effect
immediately, with no restart. While it is off, journaled responses still have
the standard response envelope described below, but nothing is written and no
journal key is returned.

The Journal Entry
-----------------

Each entry is one row of the
:class:`~smarter.lib.journal.models.SAMJournal` model:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Field
     - Contents
   * - ``key``
     - The entry's primary key: a random 64-character string, generated when
       the entry is created. It is also returned to the client in the
       response (see below).
   * - ``created_at``
     - When the entry was written. Indexed.
   * - ``user``
     - The authenticated user who made the request, or empty for an anonymous
       request. Indexed.
   * - ``thing``
     - The kind of resource the request acted on, such as ``LLMClient``,
       ``Guardrail`` or ``Secret``. The full list is
       :class:`~smarter.lib.journal.enum.SmarterJournalThings`.
   * - ``command``
     - What was done to it, such as ``apply``, ``delete`` or ``prompt``. The
       full list is :class:`~smarter.lib.journal.enum.SmarterJournalCliCommands`.
   * - ``request``
     - The HTTP request as a JSON document: the URL, method, path, query
       parameters (``GET``), form data (``POST``), cookies, request headers and
       server metadata (``META``), encoding and content type. Authenticated
       requests also record the username.
   * - ``response``
     - The complete JSON body that was sent to the client.
   * - ``status_code``
     - The HTTP status code of the response.

The ``request`` document holds what Django parsed from the request. A request
body that Django does not parse into ``POST``, such as the YAML manifest that
``apply`` sends or a JSON prompt, is not copied into it. What the request asked
for is recorded through ``thing``, ``command`` and the response, which echoes
the resource or the completion.

Responses
---------

Every journaled response is a JSON object with the same envelope. Smarter adds
two keys to whatever data the view returns: ``api``, the API version, and
``metadata``, which names the command and the resource kind. When the journal
is enabled, ``metadata`` also carries the entry's ``key``:

.. code-block:: json

   {
     "data": {
       "...": "the view's own response data"
     },
     "api": "smarter.sh/v1",
     "metadata": {
       "command": "apply",
       "thing": "Guardrail",
       "key": "0d4c2f1e...  (64 characters)"
     }
   }

The key ties a client's response to its permanent record. A client can keep it,
or quote it in a support request, and an administrator can look up exactly that
entry later. If a view returns something other than an object,
the envelope wraps it: a string becomes ``{"response": "..."}``. A list is
journaled but returned as is, without the envelope or a key.

Error responses use the same envelope, with an ``error`` object in place of the
view's data:

.. code-block:: json

   {
     "error": {
       "errorClass": "SAMBrokerErrorNotFound",
       "stacktrace": "Traceback (most recent call last): ...",
       "description": "Guardrail my-guardrail not found",
       "status": 404,
       "args": "url=https://api.example.com/api/v1/cli/describe/Guardrail/",
       "cause": "Python Exception",
       "context": "thing=Guardrail, command=describe",
       "thing": "Guardrail",
       "command": "describe"
     },
     "api": "smarter.sh/v1",
     "metadata": {
       "command": "describe",
       "thing": "Guardrail",
       "key": "..."
     }
   }

The keys of the ``error`` object are defined by
:class:`~smarter.lib.journal.enum.SmarterJournalApiResponseErrorKeys`. How
exceptions map to status codes is described in :doc:`error-handling`.

Journaling Never Breaks a Request
---------------------------------

Writing the entry is part of building the response, but it cannot make the
response fail. If the entry can't be saved, for example because a value can't
be serialized or the database is unavailable, Smarter logs the error, with the
user, resource kind, command, status and response, and returns the response to
the client without a ``key``. A response with the journal enabled but no
``key`` in its metadata is the sign that an entry is missing. Monitor the
application logs for ``could not create journal entry`` if your compliance
requirements need every request to be recorded.

Reading the Journal
-------------------

Smarter has no API endpoint for reading the journal, by design: it is an audit
record for administrators, not data for applications. Staff users read it in
the Django admin console under **Smarter Journal**, where entries are listed
newest first with their date, user, resource kind, command and status code, and
can be sorted by those columns. Each entry opens to show its full request and
response documents.

Because entries are ordinary database rows, they can also be queried directly
for an audit, by ``key``, by ``user`` or by a ``created_at`` range, which are
the fields the table indexes.

Storage and Retention
---------------------

Journal entries are written to the ``SAMJournal`` table of the platform
database. Each entry holds two JSON documents, and an entry for a prompt or a
large manifest can be many kilobytes, so with the journal enabled this is
usually the fastest-growing table in a Smarter installation. Plan for its
growth before you enable it in production:

- **Estimate the volume.** Multiply the number of API calls per day,
  especially prompts, by the size of a typical entry, then by your retention
  period.
- **Archive by date.** Entries are never updated, and nothing in the platform
  reads them, so entries older than a cut-off date can be exported, for
  example to compressed JSON files in object storage with a retention lock,
  and then removed from the table. Smarter does not ship a retention or
  archival job, so schedule one to suit your policy.
- **Turn it off where it isn't needed.** Development and test installations
  rarely need a journal. Leave ``enable_journal`` off there.

Security Considerations
-----------------------

The journal is a complete record, and it should be protected like one.

- **It contains credentials.** The ``request`` document copies the request's
  headers and cookies as Django received them. That includes the
  ``Authorization`` header, which carries the caller's API key, and the web
  console's session and CSRF cookies. Restrict who can read the journal and
  its archives, encrypt them at rest, and treat a leak of the journal as a
  leak of every API key in it.
- **It contains user content.** Prompt responses and completions can hold
  personal or confidential information. Your privacy obligations, such as
  data-subject access and deletion requests, apply to the journal and its
  archives too.
- **Smarter does not enforce immutability.** Smarter never changes an entry,
  but the database does not stop others from doing so. Staff users can change
  and delete entries in the Django admin console, and deleting a user also
  deletes that user's journal entries. If your rules require a tamper-proof
  record, archive entries promptly to storage that enforces write-once
  retention.

Technical Reference
-------------------

- :doc:`../developer-reference/smarter-journal`: the journal's enumerations,
  model, and response classes.
- :doc:`../../smarter-platform/smarter-journal`: enabling the journal, and how
  it differs from Django and application logs.
- :doc:`error-handling`: how CLI views turn exceptions into journaled error
  responses.
