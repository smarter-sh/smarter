Backend Development with Python, Django, Django REST Framework and Pydantic
===========================================================================

**Why Smarter.** Smarter is a large Django project that follows the community's conventions
closely, and its Django apps follow a deliberately rigid structure, so that once students
understand one app they can read them all. It shows patterns that small tutorial projects never
reach: custom management commands, Celery background tasks, caching, Pydantic models for every
API contract, and a broker layer that turns YAML manifests into database rows.

**Look at.** ``smarter/smarter/apps/`` (start with ``guardrail`` and ``secret``, the newest and
cleanest), ``smarter/smarter/lib/``, and the
:doc:`Architecture Decision Records </adr>`, especially those on Django, the broker model, caching,
task queues and Pydantic.

**Read.** :doc:`/smarter-framework/smarter-broker-model`, :doc:`/smarter-framework/smarter-api`,
:doc:`/smarter-framework/technologies/pydantic`, :doc:`/smarter-framework/getting-started` (a
reading list for these technologies).

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
