Docker for Software Development: Four-Week Online Course
========================================================

A four-week online course on Docker, taught on Smarter's multi-container application, with twelve
30-minute recorded lectures and a 90-minute live session each week. Week 1 covers containers and
images, week 2 the Dockerfile, week 3 Compose and configuration, and week 4 security, CI and the
path to production. See :doc:`../course-formats` for the format, the grading scale and the course
policies, and :doc:`../docker` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers and operations engineers who are new to containers.
   * - **Deployment**
     - Each student clones the repository and runs it with Docker. Week 1 includes time for
       ``make init``.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain images, layers, containers, volumes, networks and registries, and what a container
   runtime does.
2. Write multi-stage Dockerfiles that are small, fast to build and secure.
3. Run, debug and configure multi-container applications with Compose.
4. Apply the twelve-factor app to configuration, logs and processes.
5. Scan images for vulnerabilities, and build and publish images in CI.
6. Explain what changes between Compose in development and containers in production.

Technical Prerequisites
-----------------------

- **Required:** the Linux or macOS command line, files and permissions, environment variables
  and processes.
- **Required:** Git and GitHub, including pull requests.
- **Required:** Docker Desktop (or Docker Engine) with at least 8 GB of memory.
- **Required:** reading YAML.
- **Helpful:** reading Python, basic networking, and GitHub Actions.

Schedule
--------

.. list-table::
   :header-rows: 1
   :widths: 10 18 72

   * - Week
     - Item
     - Content
   * - 1
     - Lecture 1
     - **Why containers.** Virtual machines versus containers, and :doc:`ADR 002 </adr/002-docker>`.
   * - 1
     - Lecture 2
     - **Under the hood.** Namespaces, control groups, union file systems and container runtimes.
   * - 1
     - Lecture 3
     - **Inspecting containers.** ``ps``, ``images``, ``history``, ``inspect``, ``exec``, ``logs``
       and ``stats``.
   * - 1
     - Live session 1
     - Installation triage, and a live exploration of Smarter's containers. Start Assignment 1.
   * - 2
     - Lecture 4
     - **Dockerfile basics.** Instructions, context, the build cache and layer ordering.
   * - 2
     - Lecture 5
     - **Multi-stage builds.** Build and runtime stages, and Smarter's ``Dockerfile`` stage by stage.
   * - 2
     - Lecture 6
     - **Users and permissions.** Running as non-root, file ownership, and the ``docker cp``
       ownership trap.
   * - 2
     - Live session 2
     - Review of Assignment 1. Live refactoring of a small Dockerfile. Start Assignment 2.
   * - 3
     - Lecture 7
     - **Compose.** Services, networks, volumes, health checks and dependencies, in Smarter's
       ``docker-compose.yml``.
   * - 3
     - Lecture 8
     - **Configuration.** Environment files, secrets, and
       :doc:`ADR 004 on the twelve-factor app </adr/004-12-factor>`.
   * - 3
     - Lecture 9
     - **One image, many roles.** Web server, workers and scheduler, and logs as event streams.
   * - 3
     - Live session 3
     - Review of Assignment 2. Debugging a broken Compose setup, in pairs. Capstone proposals
       discussed. Start Assignment 3.
   * - 4
     - Lecture 10
     - **Image security.** Base image choice, vulnerability scanning with Trivy, signing, and
       software bills of materials.
   * - 4
     - Lecture 11
     - **Images in CI.** Building, testing and publishing images with GitHub Actions, and Smarter's
       :doc:`build pipeline </smarter-framework/developer-reference/devops/build>`.
   * - 4
     - Lecture 12
     - **Toward production.** Registries, development versus production images, and what
       Kubernetes adds.
   * - 4
     - Live session 4
     - Capstone presentations (about 6 minutes each, with 2 minutes of questions), and a course
       retrospective.

Assignments 1 to 3 are due before the next live session. Assignment 4 is due in the middle of week
4. The capstone proposal is due before Live session 3, and the capstone at the start of Live
session 4.

Graded Assignments
------------------

Assignment 1: Container Inventory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students produce an inventory of the running containers (image, command, user, ports, volumes,
networks and main process), and show the Linux namespaces of one container from the host or
Docker Desktop's virtual machine.

**Turn in:** the inventory table and commands, and a half-page on namespaces.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Inventory
     - 8
     - Complete and gathered with ``inspect`` and ``exec``.
     - Copied from Compose.
   * - Namespaces
     - 6
     - Correctly shown and explained.
     - Described without evidence.
   * - Observations
     - 4
     - Shared images and their reasons noted.
     - None.
   * - Clarity
     - 2
     - Readable.
     - Disorganized.

Assignment 2: Annotated Dockerfile and Improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students annotate Smarter's ``Dockerfile``, then refactor a small, deliberately poor Dockerfile
provided by the instructor, measuring size and build time before and after.

**Turn in:** the annotated Dockerfile, and a repository with the refactored one and measurements.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Annotation
     - 7
     - Accurate, explains why.
     - Errors or restatements.
   * - Refactoring
     - 7
     - Multi-stage, non-root, cache-friendly.
     - Partial.
   * - Measurement
     - 4
     - Before and after, repeatable.
     - Missing.
   * - Clarity
     - 2
     - Clear.
     - Unclear.

Assignment 3: Request Trace and Configuration Map
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students follow a chat request across the containers, and map every environment variable that
reaches the ``smarter-app`` container to where it is defined and what reads it (without copying
secret values).

**Turn in:** a sequence diagram with evidence, and the configuration map.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Trace
     - 7
     - Every hop, with evidence.
     - Gaps.
   * - Configuration map
     - 7
     - Sources and readers identified; no secret values.
     - Incomplete, or secrets included.
   * - Twelve-factor analysis
     - 4
     - Notes where the setup follows and departs from the twelve factors.
     - None.
   * - Clarity
     - 2
     - Clear.
     - Unclear.

Assignment 4: Scan and Publish
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students build an image of their Assignment 2 application in GitHub Actions, scan it with Trivy,
fail the build on critical vulnerabilities, and publish it to GitHub Container Registry.

**Turn in:** a repository with the workflow, and links to a passing run and the published image.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Build
     - 5
     - Builds in CI with caching.
     - Builds without caching.
   * - Scan gate
     - 6
     - Fails on critical findings, demonstrated.
     - Scans without gating.
   * - Publish
     - 5
     - Tagged sensibly and published.
     - Not published.
   * - Secrets
     - 4
     - Uses the workflow's token, no secrets in the repository.
     - Credentials committed.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and present it in Live session 4.

Capstone A: A Production-Grade Image for Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Redesign a real production image for size, build speed and security, and
prove it works in every role.

Students restructure Smarter's ``Dockerfile`` on their fork, for example with a separate build
stage, a smaller runtime base, better caching, and a software bill of materials. They measure size,
cold and cached build time, and vulnerabilities before and after, and show every container role
working.

**What students turn in:**

- A pull request against their fork.
- A measurement report with repeatable commands.
- Evidence that the web server, workers and scheduler all work, and a test chat succeeds.
- A six-minute presentation.

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
     - Significant gains in at least two dimensions.
     - Marginal.
   * - Measurement
     - 20
     - Repeatable and complete.
     - Partial.
   * - Every role works
     - 20
     - All roles verified.
     - A role broken.
   * - Security
     - 15
     - Fewer vulnerabilities; SBOM produced.
     - Not addressed.
   * - Presentation
     - 20
     - Clear trade-offs, on time.
     - Overruns.

Capstone B: A Containerized Application with CI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Containerize an application end to end, from Dockerfile and Compose to a CI
pipeline that tests, scans and publishes it.

Students containerize an application with a web process, a background job and a database, with
Compose for development, tests that run inside the container in CI, a vulnerability gate, and a
published image.

**What students turn in:**

- A public repository with the application, ``Dockerfile``, ``docker-compose.yml``, workflow and
  ``README.md``.
- Links to a passing CI run and the published image.
- A one-page comparison with Smarter's choices, and a six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Containers
     - 20
     - Multi-stage, non-root, one image for several roles.
     - Single stage, root.
   * - Compose
     - 15
     - Health checks, dependencies, volumes, environment file.
     - Services only.
   * - CI
     - 25
     - Tests in the container, scan gate, publish.
     - Build only.
   * - Configuration and secrets
     - 15
     - Twelve-factor; nothing secret committed.
     - Secrets committed.
   * - Documentation and presentation
     - 25
     - Runnable from the ``README.md``; clear presentation.
     - Missing steps.

Recommended Texts
-----------------

- **Required:** Nigel Poulton, *Docker Deep Dive* (latest edition, self-published), across weeks
  1 to 3.
- **Required:** `The Twelve-Factor App <https://12factor.net/>`__, in week 3.
- **Optional:** Sean P. Kane and Karl Matthias, *Docker: Up & Running* (3rd edition, O'Reilly,
  2023), for production topics in week 4.
- **Smarter documentation:** :doc:`/smarter-framework/technologies/docker`,
  :doc:`/adr/002-docker`, :doc:`/adr/004-12-factor`,
  :doc:`/smarter-framework/developer-reference/devops/build` and
  :doc:`/smarter-framework/developer-reference/devops/ci-cd`.

Further Study
-------------

.. include:: further-study.txt
