Docker for Software Development
===============================

**Why Smarter.** Docker is usually taught with a single container that prints "hello world", or a
two-service example that bears little resemblance to production. Smarter gives students a
realistic multi-container application on day one, the same one that runs in production:

- **One Dockerfile with twelve stages.** The `Dockerfile <https://github.com/smarter-sh/smarter/blob/main/Dockerfile>`__
  builds on a slim Python 3.14 base, adds system packages, ``kubectl``, the MariaDB connector and
  the AWS CLI, creates a non-root ``smarter_user`` with its own virtual environment, and, outside
  local development, makes the application's files read-only, so that a compromised process
  cannot rewrite its own code.
- **Six services in one Compose file.** `docker-compose.yml <https://github.com/smarter-sh/smarter/blob/main/docker-compose.yml>`__
  runs a Django web server under uvicorn, two Celery workers on separate queues, a Celery
  scheduler, MariaDB and Redis, with health checks and start-up dependencies.
- **One image, four roles.** The web server, both workers and the scheduler run the same image
  with different commands, configured entirely through the environment, as
  :doc:`ADR 004 on the twelve-factor app </adr/004-12-factor>` requires.
- **A real developer workflow.** The ``docker-*`` targets in the
  `Makefile <https://github.com/smarter-sh/smarter/blob/main/Makefile>`__ wrap every step, from
  ``make docker-init``, which creates the database and loads the platform's built-in resources, to
  a rebuild that takes seconds because it skips collecting static assets.
- **From laptop to production.** GitHub Actions builds the image for ``linux/amd64`` and
  ``linux/arm64`` and pushes it to Amazon ECR, the
  `Quick Start <https://github.com/smarter-sh/smarter-deploy>`__ runs a prebuilt image with its own
  Compose file, and the :doc:`Helm chart <kubernetes>` runs the same image on Kubernetes.

The files also have real flaws for students to find and fix: unpinned ``mariadb:latest`` and
``redis:latest`` images, an ``EXPOSE`` that names the wrong port, and two Compose files that use
different databases. Students learn as much from questioning a working setup as from building one.

**What the course covers.** Why containers, and what virtual machines and containers each isolate;
namespaces, control groups and union file systems; inspecting images and containers; the
Dockerfile, the build cache and layer ordering; multi-stage builds; users, permissions and file
ownership; Compose services, networks, volumes, health checks and dependencies; configuration
through the environment; one image in many roles, and logs as event streams; smaller, faster and
safer images, with scanning and signing; building and publishing images in CI; and what changes
on the way to production and Kubernetes.

**Look at.**

- `Dockerfile <https://github.com/smarter-sh/smarter/blob/main/Dockerfile>`__ and
  `.dockerignore <https://github.com/smarter-sh/smarter/blob/main/.dockerignore>`__.
- `docker-compose.yml <https://github.com/smarter-sh/smarter/blob/main/docker-compose.yml>`__, and
  the Quick Start's `docker-compose.yml
  <https://github.com/smarter-sh/smarter-deploy/blob/main/docker-compose.yml>`__ for comparison.
- The ``docker-*`` targets in the `Makefile <https://github.com/smarter-sh/smarter/blob/main/Makefile>`__,
  and the `build workflow <https://github.com/smarter-sh/smarter/blob/main/.github/workflows/build.yml>`__.

Each course plan lists every file that it uses under *Smarter in the Source Code*.

**Read.** :doc:`/smarter-framework/technologies/docker`, :doc:`ADR 002 on Docker </adr/002-docker>`,
:doc:`ADR 004 on the twelve-factor app </adr/004-12-factor>`,
:doc:`/smarter-framework/developer-reference/devops/build`,
:doc:`/smarter-platform/installation/quick-start`, `One Image, Laptop to Production: The Case for
Smarter on Docker and Kubernetes <https://blog.smarter.sh/2026/04/11/smarter-docker-kubernetes/>`__.

**Exercises.**

- Annotate the Dockerfile: what each stage does, why the application runs as a non-root user, and
  how the image size could be reduced.
- Use ``docker exec``, ``docker logs`` and ``docker stats`` to follow a chat request from the web
  server to a Celery worker, which writes its charge and history.
- Explain why the same image runs as the web server, the workers and the scheduler.
- Compare the development Compose file with the Quick Start's, and decide which differences are
  deliberate and which are drift.

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
