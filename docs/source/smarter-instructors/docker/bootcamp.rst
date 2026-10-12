Docker for Software Development: Classroom Bootcamp
===================================================

An eight-hour classroom bootcamp on Docker, taught on a realistic multi-container application:
Smarter's Django web server, Celery workers and scheduler, MariaDB and Redis, built from one
Dockerfile and run with one Compose file. Students read, run, debug and improve it. See
:doc:`../course-formats` for the standard bootcamp day, the grading scale and the course policies,
and :doc:`../docker` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers and operations engineers who are new to containers, or who use them without
       understanding them.
   * - **Deployment**
     - Each student clones the repository and runs it with Docker Desktop (or Docker Engine on
       Linux). The first ``make init`` downloads and builds several gigabytes, so it must be done
       **before** the bootcamp.
   * - **Cost**
     - Free. Labs need no model provider calls beyond a single test chat.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Explain images, layers, containers, volumes, networks and registries.
2. Read a multi-stage Dockerfile, and explain what each instruction does and why.
3. Run and debug a multi-container application with Docker Compose, using ``exec``, ``logs``,
   ``stats`` and ``inspect``.
4. Explain why one image can run as a web server, a worker and a scheduler, and how configuration
   reaches it.
5. Improve an image's size, build time or security, and measure the result.

Technical Prerequisites
-----------------------

- **Required:** the Linux or macOS command line: navigating directories, files and permissions,
  environment variables, processes, and a text editor.
- **Required:** Git: clone and pull.
- **Required:** Docker Desktop installed, with at least 8 GB of memory allotted to it, and
  ``make init`` and ``make run`` completed from the repository before the bootcamp (see
  :doc:`/smarter-framework/guides/developer-setup`).
- **Required:** reading YAML.
- **Helpful:** reading Python or another scripting language, and basic networking (ports, DNS,
  localhost).

Schedule
--------

.. list-table::
   :header-rows: 1
   :widths: 8 8 84

   * - Block
     - Min
     - Content
   * - 1
     - 45
     - **Lecture 1: Why containers.** "It works on my machine", virtual machines versus containers,
       images, layers, containers and registries. Smarter's containers, and
       :doc:`ADR 002 on Docker </adr/002-docker>`.
   * - 2
     - 45
     - **Lab 1: Look inside.** With ``docker ps``, ``docker images``, ``docker history``,
       ``docker inspect`` and ``docker exec``, explore the running Smarter containers: their
       processes, users, environment and networks. Produces Assignment 1.
   * - 3
     - 45
     - **Lecture 2: The Dockerfile.** Instructions, the build cache, multi-stage builds, and a walk
       through Smarter's ``Dockerfile`` stage by stage: base image, system packages, tools, a
       non-root user, a virtual environment, the application and its static assets.
   * - 4
     - 45
     - **Lab 2: Annotate the Dockerfile.** Annotate every stage and instruction: what it does,
       why it is there, and what would break without it. Produces Assignment 2.
   * - 5
     - 45
     - **Lecture 3: Compose.** Services, networks, volumes, environment files, health checks and
       dependencies, through Smarter's ``docker-compose.yml``. How the ``docker-*`` targets in the
       ``Makefile`` wrap it.
   * - 6
     - 45
     - **Lecture 4: One image, many roles.** Why the web server, the workers and the scheduler run
       from the same image with different commands. Configuration through the environment, and
       :doc:`ADR 004 on the twelve-factor app </adr/004-12-factor>`.
   * - 7
     - 45
     - **Lab 3: Follow a request.** Send a chat message, and follow it from the web server to a
       Celery worker and back with ``docker logs``, ``docker stats`` and Redis's ``MONITOR``
       command. Produces Assignment 3.
   * - 8
     - 45
     - **Lecture 5: Images that are small, fast and safe.** Layer ordering for caching, slim base
       images, ``.dockerignore``, running as non-root, secrets at build time versus run time, and
       scanning with Trivy.
   * - 9
     - 45
     - **Lab 4: Measure an image.** Explore Smarter's image layers with ``dive``, find the three
       largest, and propose one way to shrink each. Ungraded.
   * - 10
     - 45
     - **Lecture 6: From Compose to production.** Development versus production images, the lack
       of a bind mount in Smarter's setup and its trade-offs, registries, and why Kubernetes comes
       next.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone and plan it.

Graded Assignments
------------------

Assignment 1: Container Inventory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students produce an inventory of the running Smarter containers: image, command, user, exposed
ports, volumes, networks and the main process of each.

**Turn in:** a table and the commands used to fill it in.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Completeness
     - 8
     - Every container and every column filled in correctly.
     - Gaps or errors.
   * - Method
     - 6
     - Uses ``inspect`` and ``exec`` rather than guessing from the Compose file.
     - Copied from the Compose file.
   * - Observations
     - 4
     - Notes which containers share an image and why.
     - None.
   * - Clarity
     - 2
     - Easy to read.
     - Disorganized.

Assignment 2: Annotated Dockerfile
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students annotate Smarter's ``Dockerfile``: what each stage does, why the application runs as a
non-root user, and three ways the image could be made smaller or faster to build.

**Turn in:** the annotated Dockerfile (comments added) in their fork.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Accuracy
     - 8
     - Every stage and instruction explained correctly.
     - Several explanations wrong.
   * - Reasoning
     - 5
     - Explains why, not only what, including the non-root user.
     - Restates the instruction.
   * - Improvements
     - 5
     - Three realistic improvements, with expected effect.
     - Generic advice.
   * - Observation
     - 2
     - Notes that the stages form a single chain, and what a separate build stage would change.
     - Not noticed.

Assignment 3: Request Trace
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students follow one chat request through the containers, with log lines and Redis activity as
evidence, and explain why the same image appears in every step.

**Turn in:** a sequence diagram with the evidence.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Trace
     - 8
     - Every hop between containers shown.
     - Hops missing.
   * - Evidence
     - 6
     - Log lines and Redis commands for each hop.
     - Inferred.
   * - Explanation
     - 4
     - Explains the one-image, many-roles design.
     - Not addressed.
   * - Diagram
     - 2
     - Clear.
     - Cluttered.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp.

Capstone A: A Leaner, Safer Image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Improve a real production image, and prove the improvement with
measurements.

Students make one or more changes to Smarter's ``Dockerfile`` on their fork, for example a separate
build stage so that compilers do not ship, better layer ordering, or a tighter ``.dockerignore``,
and measure image size, build time (cold and cached) and vulnerability count before and after.

**What students turn in:**

- A pull request against their fork with the changes.
- A before-and-after table of size, build times and Trivy findings, with the commands used.
- Evidence that the application still works: the containers start and a test chat succeeds.
- A one-page explanation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Improvement
     - 25
     - A meaningful, measured gain.
     - Marginal or unmeasured.
   * - Measurement
     - 25
     - Repeatable measurements of size, build time and vulnerabilities.
     - One measurement, or not repeatable.
   * - Still works
     - 20
     - All containers healthy; chat works.
     - Breaks a role (for example the worker).
   * - Dockerfile quality
     - 15
     - Readable, commented, passes Hadolint.
     - Hard to follow.
   * - Explanation
     - 15
     - Explains each change and its trade-off.
     - Lists changes only.

Capstone B: Containerize Your Own Application
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Apply the patterns learned from Smarter to a new application, from
Dockerfile to Compose.

Students containerize an application of their own (or an open source one) that has at least a web
process, a background worker or scheduled job, and a database, following Smarter's patterns: one
image for several roles, a non-root user, configuration through the environment, and health
checks.

**What students turn in:**

- A Git repository with the application, ``Dockerfile``, ``docker-compose.yml``,
  ``.dockerignore`` and a ``README.md``.
- A short recording of ``docker compose up`` and the application working.
- A one-page note comparing their choices with Smarter's.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Works
     - 25
     - Starts from a clean clone with one command.
     - Needs manual steps.
   * - Dockerfile
     - 20
     - Multi-stage, non-root, cache-friendly.
     - Single stage, runs as root.
   * - Compose
     - 20
     - Health checks, dependencies, volumes, environment file.
     - Services only.
   * - Twelve-factor configuration
     - 15
     - No secrets in images or the repository.
     - Secrets baked in.
   * - Documentation
     - 20
     - Clear ``README.md`` and comparison note.
     - Missing.

Recommended Texts
-----------------

- **Pre-reading:** Docker's `getting started guide <https://docs.docker.com/get-started/>`__.
- **Reference:** Nigel Poulton, *Docker Deep Dive* (latest edition, self-published).
- **Reference:** `The Twelve-Factor App <https://12factor.net/>`__.
- **Smarter documentation:** :doc:`/smarter-framework/technologies/docker`,
  :doc:`/adr/002-docker` and :doc:`/adr/004-12-factor`.

Further Study
-------------

.. include:: further-study.txt
