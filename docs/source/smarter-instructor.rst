Smarter Instructor Guide
========================

This guide is for teachers, professors, bootcamp instructors, workshop leaders and corporate
trainers who use The Smarter Project in a classroom. It explains how to get Smarter running,
how to set it up for a class, and how to use it to teach more than a dozen subjects, from prompt
engineering for non-programmers to Kubernetes for platform engineers. The courses themselves,
with complete, ready-to-teach course plans, are in the
:doc:`Free Course Catalog <smarter-instructors/example-courses/index>`.

Smarter is a good fit for teaching for three reasons:

- **It is a real product, not a teaching toy.** Smarter is a production platform for building and
  running AI applications. Its code base is large, consistently structured, thoroughly tested and
  documented, and it uses the tools that employers use: Python, Django, Django REST Framework,
  Pydantic, React, Docker, Kubernetes, GitHub Actions and Sphinx.
- **It meets students where they are.** A student who has never programmed can build a working AI
  application in a YAML :doc:`manifest <smarter-framework/smarter-manifests>` during the first
  class. A computer science student can read, change and test the Python and React code behind it.
- **Everything is open.** Every line of code, every test, every architecture decision and every
  page of this documentation is public, so students can study how the whole system fits together,
  not just the part they are working on.


Open Source, Free, and Community Supported
-------------------------------------------

The Smarter Project is open source software, published under the
`GNU Affero General Public License v3 (AGPL-3.0) <https://www.gnu.org/licenses/agpl-3.0>`__.
It is freely downloadable, **by instructors and by their students alike**. There are no license
fees, no seat counts, no academic editions and no sign-up forms. Anyone can clone the
`source code <https://github.com/smarter-sh/smarter>`__, pull the
`Docker images <https://hub.docker.com/r/mcdaniel0073/smarter>`__, or install the
`Helm chart <https://artifacthub.io/packages/helm/project-smarter/smarter>`__, on their own
computer or their institution's servers, and keep using it after the course ends.

Smarter is community supported. Help comes from the project's maintainers and contributors through
`GitHub Discussions <https://github.com/smarter-sh/smarter/discussions>`__ and
`GitHub Issues <https://github.com/smarter-sh/smarter/issues>`__, and from the tutorials on the
`Smarter YouTube channel <https://www.youtube.com/@project-smarter>`__. There is no vendor support
desk, so plan your first installation well before your first class, and ask questions early.

.. note::

   **What is free, and what is not.** Smarter itself costs nothing. The large language models that
   it calls usually do: OpenAI, Google, Anthropic and the other :doc:`providers <smarter-resources/smarter-provider>`
   charge for each request, to whoever owns the API key. An introductory course costs very
   little if you use small, inexpensive models, and Smarter's :doc:`Budgets <smarter-resources/smarter-budget>`
   cap what any one student can spend. Running Smarter on your own computers is free, while a
   shared instance on Kubernetes in the cloud costs around $350 USD a month. See `Managing Cost`_
   below.

   The AGPL-3.0 license lets students use, study, change and redistribute Smarter. If a student
   runs a *modified* version of Smarter as a public service, the license requires them to offer
   their changes under the same license. This is a good topic for a class discussion of open
   source licensing in itself.


From Educational Sandbox to Live Production
-------------------------------------------

Smarter was designed for both learning and production, and the path between them is the same
software, not a rewrite. What a student builds in class is not thrown away at the end of the
term:

.. list-table::
   :header-rows: 1
   :widths: 22 39 39

   * - Stage
     - What the student does
     - What carries forward
   * - **1. Sandbox on a laptop**
     - Runs Smarter in Docker with the :doc:`Quick Start <smarter-platform/installation/quick-start>`,
       and builds LLMClients in the prompt engineering workbench. A new LLMClient runs in
       *Sandbox Mode*: it can be used only by a logged-in user, in the web console.
     - Their YAML manifests.
   * - **2. Shared class instance**
     - Uses an instance that the instructor runs, with their own login, API key and budget,
       alongside classmates in a shared :doc:`Account <smarter-resources/smarter-account>`.
     - The same manifests, applied with the same ``smarter apply`` command.
   * - **3. Developer**
     - Builds Smarter from source, changes its Python and React code, and runs its tests.
     - Their code, tests and documentation, as commits in their own fork.
   * - **4. Live production**
     - Deploys an LLMClient (``smarter deploy llmclient <name>``) so that it is reachable by
       URL and API key, and runs Smarter on Kubernetes with the Helm chart, for a real audience.
     - Everything. The manifests that ran on a laptop run unchanged on a production cluster.
   * - **5. Contributor**
     - Sends a pull request to the Smarter project itself.
     - A public, reviewed contribution to a real open source project, for their portfolio.

Point this out to your students early. It changes how they treat their coursework: a manifest
written for an assignment can become the AI application that a student club, a part-time employer,
or a startup actually uses.

Free Course Designs
--------------------

The :doc:`Free Course Designs <smarter-instructors/example-courses/index>` has 22 complete,
ready-to-teach course designs, from prompt engineering for non-programmers to
Kubernetes for platform engineers. Each course design comes with turnkey course plans,
with schedules, graded assignments and rubrics, capstone projects and reading lists, so
that an instructor can take a plan, set the dates, and teach it. Paths in the courses
are relative to the root of the `smarter <https://github.com/smarter-sh/smarter>`__ repository.




Getting Smarter Running
-----------------------

The first step for nearly every instructor is to run Smarter on their own computer. Do this at
least a week before you teach, so that you have time to get help if something goes wrong. Choose
one of two methods, depending on what you will teach.

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * -
     - Quick Start (pre-built images)
     - From source (developer setup)
   * - **Best for**
     - Prompt engineering, AI application design, AI governance, and any course in which
       students write manifests rather than Python.
     - Every software development course: backend, front end, full stack, security, Docker,
       quality assurance, documentation and agentic development.
   * - **Repository**
     - `smarter-sh/smarter-deploy <https://github.com/smarter-sh/smarter-deploy>`__
     - `smarter-sh/smarter <https://github.com/smarter-sh/smarter>`__
   * - **Prerequisites**
     - `Docker Desktop <https://docs.docker.com/desktop/>`__ and ``make``.
     - Docker, ``make``, ``git``, Python 3.14 or later, and Node 24 or later. See
       :doc:`smarter-platform/prerequisites`.
   * - **Time**
     - About 10 minutes.
     - About an hour the first time.

In either case you need an `OpenAI API key <https://platform.openai.com/api-keys>`__, because
OpenAI is the one provider that Smarter requires. Keys for Google, Meta, Anthropic and others are
optional. See :doc:`smarter-platform/adding-an-llm-provider`.

Quick Start
~~~~~~~~~~~

.. code-block:: console

   git clone https://github.com/smarter-sh/smarter-deploy.git
   cd smarter-deploy
   make            # creates a .env file. Add your OpenAI API key to it before continuing.
   make init       # pulls the Docker images and seeds the platform with example data
   make run        # starts the platform

Open http://localhost:9357/login/ and log in as ``admin@smarter.sh`` with the password
``smarter``. Change the password straight away. The
:doc:`Quick Start Guide <smarter-platform/installation/quick-start>` has screenshots of each step.

From Source
~~~~~~~~~~~

.. code-block:: console

   git clone https://github.com/smarter-sh/smarter.git
   cd smarter
   make            # creates a .env file and its encryption key. Add your API keys to it.
   make init       # creates the Python virtual environment, builds the containers, seeds the database
   make build      # rebuilds the containers from your working copy
   make run        # starts every container, and the web server on http://localhost:9357

``docker ps`` should list the ``smarter-app``, ``smarter-worker``, ``smarter-beat``,
``smarter-mariadb`` and ``smarter-redis`` containers. The
:doc:`Developer Setup Guide <smarter-framework/guides/developer-setup>` explains each part of the
environment, and :doc:`smarter-platform/trouble-shooting` covers the common problems.

The Command-Line Interface
~~~~~~~~~~~~~~~~~~~~~~~~~~

Students can optionally manage Smarter resources with the ``smarter`` :doc:`command-line interface <smarter-framework/smarter-cli>`,
which works much like ``kubectl`` and does everything that can be done through the web interface.
Download it from `smarter.sh/cli <https://smarter.sh/cli>`__,
then run ``smarter configure``. Use ``--environment local`` to point it at a Smarter that runs
on the same computer. Then try:

.. code-block:: console

   smarter whoami                       # who am I, and which account am I in?
   smarter get llmclients               # list the LLMClients that I can use
   smarter manifest llmclient           # print an example LLMClient manifest
   smarter apply -f my-llmclient.yaml   # create or update a resource from a manifest

A First Look Around
~~~~~~~~~~~~~~~~~~~

Smarter installs with a library of built-in example resources, so that there is something to explore on a
fresh installation. Before you plan a lesson, open the :doc:`web console <smarter-platform/smarter-web-console>`
and try a few of the built-in LLMClients in the workbench: ``simple``, ``calculator``,
``weather``, ``research_analyst``, ``data_analyst`` and ``customer_support`` show a progression
from a bare model to a completely styled, governed application with plugins, MCP servers and guardrails. Their
manifests, in ``smarter/smarter/apps/llmclient/data/llm-clients/``, make good starting points for
your own examples. The course advisors ``stackademy_sql`` and ``stackademy_api`` come from the
:doc:`Stackademy example project <smarter-framework/smarter-manifests/stackademy>`, a GitHub
repository of its own, which shows students how to manage a project of many AI resources with git
and GitHub.


Setting Up a Class
------------------

Choosing a Deployment Model
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * -
     - Each student runs their own Smarter
     - The instructor runs one Smarter for the class
   * - **How**
     - Students follow `Getting Smarter Running`_ on their own laptops.
     - The instructor runs Smarter on a lab server with Docker Compose, or on a Kubernetes cluster
       with the Helm chart (see :doc:`smarter-platform/installation/production-deployment`), for
       around $350 USD a month in the cloud.
   * - **Students need**
     - A laptop that runs Docker Desktop comfortably (8 GB of memory at the very least), and their own
       provider API key, or one that you give them.
     - A web browser, the ``smarter`` CLI, and a Smarter API key.
   * - **Strengths**
     - Students are administrators of their own platform, and can change its code. Nothing
       is shared, so nothing one student does affects another.
     - Nothing to install. Provider keys stay with you, budgets cap spending, and you can see
       every student's resources and prompts in one place.
   * - **Best for**
     - Software development, Docker, security and agentic development courses.
     - Prompt engineering, AI application design and governance courses, workshops, and
       students with low-powered or locked-down computers.

Many courses use both: a shared instance for the first weeks, and students' own installations
once they start changing code.

Accounts and Users
~~~~~~~~~~~~~~~~~~

Smarter places an :doc:`Account <smarter-platform/account-management>` above its users. Every
resource that a user creates is shared with everyone in the same account, and accounts cannot see
each other's resources at all. This maps naturally onto a classroom:

- **One account per class section**, so that students can reuse each other's plugins and
  guardrails by name, as a team would.
- **One account per student or per project team**, when work must be kept separate, for
  example for individually graded assignments.

On a shared instance, create accounts, users and API keys with ``manage.py`` commands in the
``smarter-app`` container (see :doc:`smarter-platform/user-management` and
:doc:`smarter-platform/api-keys`):

.. code-block:: console

   docker exec -it smarter-app bash
   cd /home/smarter_user/smarter

   python manage.py create_account --company_name "CS 4410 Fall Section 1" --account_number "####-####-####"

   python manage.py create_user --account_number "####-####-####" \
     --username "student1" --email "student1@example.edu" \
     --first_name "Student" --last_name "One" --password "a-temporary-password"

   python manage.py create_api_key --account_number "####-####-####" \
     --username "student1" --description "CS 4410 coursework"

Replace ``####-####-####`` with the account number that ``create_account`` prints. Each API key is
shown once, so hand it to the student straight away. A short shell script that reads your class
roster from a CSV file makes this quick for a large class, and is itself a good first exercise
for a scripting course.

Managing Cost
~~~~~~~~~~~~~

Teaching with Smarter has two kinds of cost: the cloud infrastructure that it runs on, if you
run it in the cloud, and the model provider charges for each request.

**Infrastructure.** Smarter on students' laptops, or on a lab server that your institution
already owns, costs nothing to run. A shared instance on a managed Kubernetes cluster in the cloud
has an expected baseline cost of around $350 USD a month, for the cluster, its nodes, the load
balancer, the database and the other services that Smarter needs. That cost grows very slightly
with each student: in production, the variable cloud infrastructure cost per student is
significantly less than a dollar a month. A class of 30 costs about the same to host as a class
of 300, so sharing one cluster between several courses, or across a department, spreads the
baseline cost further.

**Model providers.** Provider charges grow with use, and three features keep them predictable:

- **Inexpensive models.** Each LLMClient names its model in ``defaultModel``. Small models such as
  ``gpt-5-nano`` cost a small fraction of a cent per request, and are more than good enough for
  most exercises.
- **Budgets.** A :doc:`Budget <smarter-resources/smarter-budget>` sets a spending limit, in dollars
  or tokens, per hour, day, week or month and in total, on a user, an account, an LLMClient or a
  provider. When a student reaches a limit, their chat answers with your message instead of calling
  the model, until the limit renews. Smarter ships with an example for exactly this case:

  .. literalinclude:: ../../smarter/smarter/apps/account/data/example-manifests/budgets/student-monthly-allowance.yaml
     :language: yaml
     :caption: A per-student monthly allowance

- **Cost accounting.** Every token is charged to the user, LLMClient and account that used it, and
  the dashboard's Budget vs Actual chart shows where the money goes. See
  :doc:`smarter-platform/cost-accounting`.

On a shared instance, students never hold your provider keys. Smarter stores them as encrypted
:doc:`Secrets <smarter-resources/smarter-secret>` and applies them itself, and a
:doc:`Proxy <smarter-resources/smarter-proxy>` even lets students call the OpenAI, Anthropic or
Google SDK directly with a Smarter API key in place of the provider's.

Privacy and Academic Integrity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Smarter records every :doc:`Prompt <smarter-resources/smarter-prompt>`, tool call and guardrail
intervention in its :doc:`journal <smarter-platform/smarter-journal>`. That is valuable for
teaching, because you can review how a student arrived at an answer, not just the answer. It also
means that you should:

- **Tell students** that their prompts are recorded, and who can read them.
- **Keep personal data out of exercises.** Use invented names, addresses and records. The
  ``pii-redaction-input`` :doc:`guardrail <smarter-resources/smarter-guardrail>` is a useful safety
  net on a shared instance.
- **Follow your institution's rules** for student data and for sending it to third-party AI
  providers. For a strict policy, :doc:`LLMHost <smarter-resources/smarter-llmhost>` serves open
  models on your own Kubernetes cluster, so that prompts never leave your network.


Planning a Course
-----------------

Sample Formats
~~~~~~~~~~~~~~

The courses in the :doc:`Free Course Catalog <smarter-instructors/example-courses/index>` come
with plans for classroom bootcamps and online courses of two to six weeks. Other formats work
well too:

- **A half-day workshop.** Run a shared instance. Students log in, chat with the built-in
  LLMClients, copy one manifest, change its system prompt and model, add a plugin and a guardrail,
  and apply it. No installation is needed beyond the ``smarter`` CLI, or none at all if students
  work in the web console.
- **A six-week module in prompt engineering or AI applications.** A shared instance for the whole
  module. Each week adds one resource: LLMClients, plugins, vectorstores, MCP clients, guardrails,
  and orchestrators. The final project is an application designed for a real client.
- **A semester software engineering course.** Students install Smarter from source in the first
  two weeks, then work through backend, front end, testing, documentation and deployment, and
  finish with a feature, or a contribution to the project, that is reviewed as a pull request.

Assignments and Grading
~~~~~~~~~~~~~~~~~~~~~~~

- **Manifests are plain text.** Students can submit them in a Git repository, where they can be
  diffed, reviewed and tested, as infrastructure code is at work.
- **Pull requests are submissions.** For code courses, have students fork the repository and open
  pull requests against their fork. The pre-commit hooks and the GitHub Actions test workflow give
  fast, impartial feedback before you read the code.
- **The journal shows the process.** For prompt engineering, ask students to submit the prompts
  and tool calls that led to their result, not only the result.
- **Ask for the reasoning.** A short design note, or an Architecture Decision Record, for each
  substantial assignment shows whether a student understood what they built, which matters more
  when coding agents can write much of the code.


Instructor Checklist
--------------------

Before the first class:

- Install Smarter yourself, with the method that your students will use, and work through your
  first lesson on it.
- Decide between student installations and a shared instance, and set up accounts, users, API
  keys and budgets.
- Choose inexpensive default models, and attach a :doc:`Budget <smarter-resources/smarter-budget>`
  to every student.
- Change the ``admin@smarter.sh`` password on every installation.
- Teach students to keep API keys out of Git: the ``.env`` file is ignored by Git for this reason,
  and the ``detect-private-key`` hook is a second line of defense.
- Tell students that their prompts are recorded, and keep personal data out of exercises.


Getting Help and Giving Back
----------------------------

- **Questions:** `GitHub Discussions <https://github.com/smarter-sh/smarter/discussions>`__.
- **Bugs:** `GitHub Issues <https://github.com/smarter-sh/smarter/issues>`__.
- **Video tutorials:** the `Smarter YouTube channel <https://www.youtube.com/@project-smarter>`__.
- **Problems with installation:** :doc:`smarter-platform/trouble-shooting`.

Smarter improves when the people who use it share what they learn. If you write lesson plans,
exercises or slides for Smarter, consider sharing them in GitHub Discussions, so that other
instructors can use them, and encourage your students to contribute fixes and documentation
upstream. Every :doc:`contributor <contributors>` started with a first pull request.
