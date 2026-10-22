The Stackademy Example Project
==============================

Stackademy is a fictional online code academy, and the example project that much of this
documentation uses. Its two course advisors, the LLMClients ``stackademy_sql`` and
``stackademy_api``, answer students' questions about Stackademy's catalogue of computer science
courses: what they cover, what they cost, and which courses each one requires first.

No AI model can answer these questions on its own: Stackademy is fictional, so its catalogue was never in
any model's training data, as your own organization's data isn't. Asked anyway, a model either admits
that it doesn't know, or invents a plausible course at a plausible price. The course advisors look the
answers up instead, with tool calling: the model asks for a tool, a :doc:`SqlPlugin
</smarter-resources/llmtool/plugin/sql>` that queries Stackademy's database, or an :doc:`ApiPlugin
</smarter-resources/llmtool/plugin/api>` that calls its web API, with values that it chooses from the
student's question, and answers from the courses that the tool returns. Each tool is a manifest, not
code: Smarter describes it to the model, runs it, and keeps its credentials secret.

The project is a small but complete AI solution, built from ten resources of seven kinds, which
depend on each other. Its manifests are not part of the Smarter platform. They live in their own
GitHub repository, `smarter-sh/stackademy <https://github.com/smarter-sh/stackademy>`__, to show how
a prompt engineer can manage a project of many AI resources with git and GitHub: each change is a
commit, reviewed in a pull request, and the repository's history records who changed what, and why.

The case study `Stackademy Online Coding Academy <https://smarter.sh/case-studies/stackademy>`__, on
smarter.sh, teaches the project as a lesson: why a model can't answer from private data, how one tool
call works from question to answer, how to read a manifest, and how a team governs the project with
git. Readers chat with both course advisors live, and open each manifest of the repository in an
editor that checks it as they change it, against the same JSON Schemas that the repository's checks
use. Its learning objectives, labs and discussion questions are ready to use in a class.

The Repository
--------------

Each folder holds the manifests of one family of resources, in the order that they depend on each
other.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Folder
     - Resources
   * - ``secrets/``
     - Three :doc:`Secrets </smarter-resources/smarter-secret>`: the passwords of the Stackademy test
       database and its proxy, and of the Stackademy course catalogue api.
   * - ``connections/sql/``
     - The :doc:`SqlConnection </smarter-resources/smarter-connection>` ``smarter_test_db``, to the
       Stackademy test database.
   * - ``connections/api/``
     - The ApiConnection ``smarter_test_api``, to the course catalogue api of the platform that
       applies it. It is a :doc:`manifest template <manifest-templates>`, ``*.yaml.tpl``.
   * - ``plugins/sql/``
     - The :doc:`SqlPlugin </smarter-resources/smarter-llmtool>` ``stackademy_sql``, which queries the
       course catalogue with SQL.
   * - ``plugins/api/``
     - The ApiPlugin ``stackademy_api``, which queries the same catalogue through a REST api.
   * - ``llm-clients/``
     - The :doc:`LLMClients </smarter-resources/smarter-llmclient>` ``stackademy_sql`` and
       ``stackademy_api``, each with its plugin, and Stackademy's colors.
   * - ``budgets/``
     - The :doc:`Budget </smarter-resources/smarter-budget>` ``stackademy_project``, which limits
       what ``stackademy_sql`` may spend.
   * - ``scripts/``
     - Not manifests: the scripts that a platform runs when it loads the repository, listed in
       ``scripts.yaml``. ``create-course-database.sh`` runs ``smarter_test_db.sql``, which creates
       the course database, its ``courses`` table and its read-only users.

Its pre-commit hooks check every manifest against the JSON Schema of its kind, which the Smarter
platform publishes, before each commit, and a GitHub Actions workflow runs them on every pull request.

What the Platform Provides
--------------------------

The data that the course advisors read is served by the platform, so that the project works on every
Smarter platform without an external service:

- the ``smarter_test_db`` database, whose ``courses`` table is the course catalogue, in the
  platform's own database server. The repository's ``scripts/create-course-database.sh`` creates
  it, and ``manage.py initialize_platform`` runs that script, and

- the course catalogue api, ``/api/v1/demos/stackademy/course-catalogue/``, which accepts the
  value of the ``smarter_test_api`` Secret of the Smarter account as its password.

How a Platform Loads It
-----------------------

``manage.py load_from_github`` clones a GitHub repository of manifests and applies each of them, in
the order of their kinds' dependencies, :meth:`SAMKinds.apply_order()
<smarter.apps.api.v1.manifests.enum.SAMKinds.apply_order>`: Secrets first, then Connections,
plugins, LLMClients, and Budgets last. It fills in manifest templates with the platform's own scheme and domain, and an
LLMClient that is already deployed stays deployed.

A repository may also hold scripts, for what a manifest can't describe, such as the course
database. They are in its top-level ``scripts/`` folder, which holds no manifests, and its
``scripts/scripts.yaml`` lists the scripts to run, each with a ``stage``: ``pre``, before the
manifests are applied, or ``post``, after they are applied and the LLMClients deployed. A script
receives the platform's database server and its administrator, the owner's account and username,
and the repository, in its environment, and none of the platform's own credentials. See
:mod:`smarter.apps.account.repository_scripts`.

- ``manage.py initialize_platform`` loads the Stackademy repository for the Smarter admin, with
  ``--run_scripts``, so that its ``pre`` script creates the course database, as
  ``SMARTER_MYSQL_ROOT_USERNAME``, before its SqlConnection is applied. Then
  ``manage.py verify_stackademy`` sends each course advisor a real prompt, and fails unless its
  plugin returned course catalogue data.
- ``manage.py initialize_account`` loads it for each account's admin, without the Budget, which only
  a superuser may apply, and without its scripts, and deploys the account's course advisors.

.. code-block:: console

   python manage.py load_from_github --url https://github.com/smarter-sh/stackademy --account_number 3141-5926-5359

See :doc:`/smarter-resources/account/commands/load_from_github` and
:doc:`/smarter-resources/llmclient/commands/verify-stackademy`.
