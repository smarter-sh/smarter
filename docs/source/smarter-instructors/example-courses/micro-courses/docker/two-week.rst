Docker for Software Development: Two-Week Online Course
=======================================================

A two-week online course on Docker, taught on Smarter's multi-container application. The `Dockerfile
<https://github.com/smarter-sh/smarter/blob/main/Dockerfile>`__ has twelve stages, from a slim
Python 3.14 base to a non-root user whose files are made read-only outside development, and
`docker-compose.yml <https://github.com/smarter-sh/smarter/blob/main/docker-compose.yml>`__ runs six
services: the Django web server, two Celery workers on separate queues, the Celery scheduler,
MariaDB and Redis. The same image plays four roles, the ``docker-*`` targets in the `Makefile
<https://github.com/smarter-sh/smarter/blob/main/Makefile>`__ wrap every step, and the same image
runs in production on Kubernetes, so nothing students learn is a classroom simplification. The files
also have real flaws to find, such as unpinned base images. There are six 30-minute recorded
lectures and a 90-minute live session each week. Week 1 covers images and the Dockerfile, and week 2
covers Compose, configuration and production images. See :doc:`../course-formats` for the format,
the grading scale and the course policies, and :doc:`../docker` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers and operations engineers who are new to containers.
   * - **Deployment**
     - Each student clones the repository and runs it with Docker. ``make init`` is done before
       Live session 1.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain images, layers, containers, volumes, networks and registries.
2. Read and write multi-stage Dockerfiles.
3. Run and debug multi-container applications with Compose.
4. Configure containers through the environment, following the twelve-factor app.
5. Build small, fast and secure images, and measure them.

Technical Prerequisites
-----------------------

- **Required:** the Linux or macOS command line, files and permissions, environment variables
  and processes.
- **Required:** Git: clone, branch, commit and push, and a GitHub account.
- **Required:** Docker Desktop (or Docker Engine) with at least 8 GB of memory, and the
  repository built with ``make init`` before Live session 1.
- **Required:** reading YAML.
- **Helpful:** reading Python, and basic networking.

Schedule
--------

The files that the lectures refer to are listed in full under `Smarter in the Source Code`_.

.. list-table::
   :header-rows: 1
   :widths: 10 18 72

   * - Week
     - Item
     - Content
   * - 1
     - Lecture 1 (30 min)
     - **Why containers.** Virtual machines versus containers, images, layers and registries.
       :doc:`ADR 002 </adr/002-docker>`.
   * - 1
     - Lecture 2 (30 min)
     - **Inspecting containers.** ``ps``, ``images``, ``history``, ``inspect``, ``exec``, ``logs``
       and ``stats``.
   * - 1
     - Lecture 3 (30 min)
     - **The Dockerfile.** Instructions, the build cache, multi-stage builds, and Smarter's
       ``Dockerfile`` stage by stage.
   * - 1
     - Live session 1 (90 min)
     - Installation triage, then a live exploration of Smarter's running containers. Pairs answer
       questions about them. Start Assignment 1.
   * - 2
     - Lecture 4 (30 min)
     - **Compose.** Services, networks, volumes, environment files and health checks, in
       Smarter's ``docker-compose.yml``.
   * - 2
     - Lecture 5 (30 min)
     - **One image, many roles.** Web server, workers and scheduler from one image;
       :doc:`ADR 004 on the twelve-factor app </adr/004-12-factor>`.
   * - 2
     - Lecture 6 (30 min)
     - **Better images.** Layer order, slim bases, ``.dockerignore``, non-root users, secrets, and
       scanning with Trivy.
   * - 2
     - Live session 2 (90 min)
     - Capstone presentations (about 5 minutes each, with 2 minutes of questions).

Assignment 1 is due at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
and the capstone at the start of Live session 2.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Inventory and Annotated Dockerfile
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students produce an inventory of the running containers, and annotate Smarter's ``Dockerfile``
stage by stage.

**Turn in:** the inventory table, and the annotated Dockerfile in their fork.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Inventory
     - 6
     - Complete, gathered with ``inspect`` and ``exec``.
     - Copied from the Compose file.
   * - Annotation accuracy
     - 8
     - Every stage and instruction correct.
     - Several errors.
   * - Reasoning
     - 4
     - Explains why, including the non-root user.
     - Restates instructions.
   * - Clarity
     - 2
     - Easy to read.
     - Disorganized.

Assignment 2: Request Trace
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students follow a chat request from the web server to a Celery worker and back, with evidence, and
explain the one-image, many-roles design.

**Turn in:** a sequence diagram and evidence.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Trace
     - 8
     - Every hop.
     - Gaps.
   * - Evidence
     - 6
     - Logs and Redis activity.
     - Inferred.
   * - Explanation
     - 6
     - Clear explanation of roles and configuration.
     - Missing.

Assignment 3: Compose for a Small App
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write a Dockerfile and Compose file for a small provided application (a web process, a
worker and a database) using the patterns from Smarter.

**Turn in:** a Git repository that starts with ``docker compose up``.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Works
     - 6
     - Starts from a clean clone.
     - Manual steps needed.
   * - Dockerfile
     - 5
     - Non-root, cache-friendly.
     - Root, uncached.
   * - Compose
     - 5
     - Health checks, dependencies, volumes.
     - Services only.
   * - Configuration
     - 4
     - Environment file, no secrets committed.
     - Secrets committed.

Capstone Projects
-----------------

Students choose one, and present it in Live session 2.

Capstone A: A Leaner, Safer Image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Improve a real production image, and prove the improvement with
measurements.

Students change Smarter's ``Dockerfile`` on their fork (for example, a separate build stage, better
layer ordering, a tighter ``.dockerignore``) and measure size, cold and cached build time, and Trivy
findings before and after.

**What students turn in:**

- A pull request against their fork, and a measurement table with commands.
- Evidence that every container still works.
- A five-minute presentation.

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
     - Meaningful and measured.
     - Marginal.
   * - Measurement
     - 25
     - Repeatable, three dimensions.
     - One, or not repeatable.
   * - Still works
     - 20
     - Every role healthy.
     - A role broken.
   * - Dockerfile quality
     - 15
     - Readable, passes Hadolint.
     - Hard to follow.
   * - Presentation
     - 15
     - Clear trade-offs, on time.
     - Overruns.

Capstone B: Containerize Your Own Application
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Apply Smarter's container patterns to a new application.

Students containerize an application of their own or an open source one, with a web process, a
background job and a database: one image for several roles, non-root, configured through the
environment, with health checks.

**What students turn in:**

- A Git repository with the application, ``Dockerfile``, ``docker-compose.yml``, ``.dockerignore``
  and ``README.md``.
- A one-page comparison with Smarter's choices.
- A five-minute presentation with a live start from a clean clone.

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
     - One command from a clean clone.
     - Manual steps.
   * - Dockerfile
     - 20
     - Multi-stage, non-root, cache-friendly.
     - Single stage, root.
   * - Compose
     - 20
     - Health checks, dependencies, volumes.
     - Services only.
   * - Configuration
     - 15
     - Twelve-factor, no secrets in the image.
     - Secrets baked in.
   * - Documentation and presentation
     - 20
     - Clear.
     - Missing.

Recommended Texts
-----------------

- **Required:** Nigel Poulton, *Docker Deep Dive* (latest edition, self-published). Week 1: the
  chapters on images, containers and containerizing an app. Week 2: the chapters on Compose,
  networking, volumes and security.
- **Required:** `The Twelve-Factor App <https://12factor.net/>`__, in week 2.
- **Reference:** Docker's `building best practices
  <https://docs.docker.com/build/building/best-practices/>`__.
- **Smarter documentation:** :doc:`/smarter-framework/technologies/docker`,
  :doc:`/adr/002-docker` and :doc:`/adr/004-12-factor`.

Further Study
-------------

.. include:: further-study.txt
