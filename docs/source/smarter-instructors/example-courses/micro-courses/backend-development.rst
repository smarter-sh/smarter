Backend Development with Python, Django, Django REST Framework and Pydantic
===========================================================================

**Why Smarter.** Tutorial projects teach Django one feature at a time, on a blog or a to-do list,
and stop before the problems that real backends face. Smarter is a large Django project in
production that follows the community's conventions closely, and its eighteen Django apps in
`smarter/smarter/apps/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps>`__
follow one deliberately rigid structure, so that once students understand one app they can read
them all. The `guardrail <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/guardrail>`__
app is the reference: a Django model, a Pydantic manifest, a broker, serializers, API views,
signals, receivers and one test module per source module, each in the same place in every app.

It shows the patterns that small projects never reach, each in code that students can open:

- **A broker layer** that turns a YAML manifest into database rows and back, behind one REST API
  for every kind of resource. See the
  `abstract broker <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/manifest/broker/abstract_broker_class.py>`__,
  the `registry of kinds <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/api/v1/cli/brokers.py>`__
  and :doc:`/smarter-framework/smarter-broker-model`.
- **Pydantic for every contract:** manifests, API responses and the
  `Settings class <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/common/conf/settings.py>`__
  that validates every environment variable (:doc:`ADR 031 </adr/031-pydantic-over-json>`).
- **Ownership and multi-tenancy:** an
  `abstract base model <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/account/models/metadata_with_ownership.py>`__
  that makes every resource belong to an account and a user, with permission-aware querysets.
- **Work outside the request:** Celery workers on named queues and a
  `beat schedule <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/workers/celerybeat.py>`__
  that aggregates charges and enforces budgets; caching with
  `@cache_results <https://github.com/smarter-sh/cache-results/blob/main/src/cache_results/decorators.py>`__;
  and `management commands <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/account/management/commands>`__
  built on a shared ``SmarterCommand`` base class.
- **Tests at scale:** more than five thousand unit tests, a
  `SmarterTestBase <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/unittest/base_classes.py>`__
  with no transaction rollback, and an in-memory provider that replaces every cloud call.

The reasons behind these choices are written down in the
:doc:`Architecture Decision Records </adr>`, so students learn why as well as how.

**What the course covers.** Installing Smarter from source and working with its containers; Django
in one picture: projects, apps, settings, URLs, middleware, views, models and the ORM; querysets,
relationships, aggregation and the N+1 problem; Django REST Framework, authentication and
permissions; errors, versioning and API documentation; Pydantic, manifests and brokers; models and
migrations, including when to add a migration rather than regenerate one; testing Django, with
fixtures, mocks and coverage; management commands; Celery tasks, queues and the beat scheduler;
and caching and performance. The longer plans end with a new resource kind, delivered as a pull
request.

**Look at.**

- `smarter/smarter/apps/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps>`__,
  starting with ``guardrail`` and ``secret``, the newest and cleanest apps.
- `smarter/smarter/lib/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/lib>`__,
  the framework code: brokers, manifests, the journal, caching and test helpers.
- The :doc:`Architecture Decision Records </adr>`, especially those on
  :doc:`Django </adr/001-django>`, the :doc:`broker model </adr/024-broker-model>`,
  :doc:`caching </adr/018-caching>`, :doc:`task queues </adr/030-task-queues>` and
  :doc:`Pydantic </adr/031-pydantic-over-json>`.

Each course plan lists every file that it uses, layer by layer, under *Smarter in the Source Code*.

**Read.** :doc:`/smarter-framework/smarter-broker-model`, :doc:`/smarter-framework/smarter-api`,
:doc:`/smarter-framework/technologies/pydantic`, :doc:`/smarter-framework/getting-started` (a
reading list for these technologies), :doc:`/smarter-framework/guides/developer-feature-checklist`,
`Pydantic Settings: How Smarter Validates and Manages Its Configuration
<https://blog.smarter.sh/2026/09/19/smarter-pydantic-settings/>`__, `Smarter's Ownership Model: One
Base Class for Owning, Sharing and Tracking AI Resources
<https://blog.smarter.sh/2026/07/18/smarter-metadata-with-ownership/>`__, `Smarter's
@cache_results() Decorator: Persistent Function Caching for Django
<https://blog.smarter.sh/2026/05/09/smarter-cache-results/>`__.

**Exercises.**

- Trace one ``smarter apply`` request from the URL route, through the DRF view and the broker, to
  the Django model, and draw a sequence diagram.
- Add a field to an existing resource's manifest: the Pydantic model, the Django model and its
  migration, the broker, and the tests.
- Write a ``manage.py`` command, following ``smarter/smarter/apps/account/management/commands/``.
- As a capstone, add a new resource kind end to end, following
  :doc:`/smarter-framework/guides/developer-feature-checklist`.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <backend-development/bootcamp>
   Two-week online course: 6 hours <backend-development/two-week>
   Four-week online course: 12 hours <backend-development/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
