Docker for Software Development
===============================

**Why Smarter.** Students run a realistic multi-container application on day one: a Django web
server, Celery workers and a scheduler, MariaDB and Redis, all defined in one Compose file and
built from one Dockerfile.

**Look at.** ``Dockerfile``, ``docker-compose.yml`` and the ``docker-*`` targets in the ``Makefile``.

**Read.** :doc:`/smarter-framework/technologies/docker`, :doc:`ADR 002 on Docker </adr/002-docker>`,
:doc:`ADR 004 on the twelve-factor app </adr/004-12-factor>`.

**Exercises.**

- Annotate the Dockerfile: what each stage does, why the application runs as a non-root user, and
  how the image size could be reduced.
- Use ``docker exec``, ``docker logs`` and ``docker stats`` to follow a chat request from the web
  server to a Celery worker.
- Explain why the same image runs as the web server, the worker and the scheduler.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <docker/bootcamp>
   Two-week online course: 6 hours <docker/two-week>
   Four-week online course: 12 hours <docker/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
