Confidential by Construction: AI Assistants over One Company Database
=====================================================================

*How four departments of Stackademy got AI assistants over the same database, without any assistant able to read
another department's records, and why the database, not the prompt, is where that is enforced.*

At a glance
-----------

.. list-table::
   :widths: 25 75

   * - Organization
     - Stackademy: HR, Accounting, Course Content and Admissions, whose records share one MariaDB database of 25
       tables.
   * - Challenge
     - Each department wants an assistant that answers questions about its own records in plain language. Salaries,
       students' payments and the general ledger sit side by side in one database, and an assistant writes no
       queries that anyone reviews before they run.
   * - Solution
     - One read-only database user per department, granted exactly its tables; a connection, a set of fixed SQL
       tools, a budget and an assistant per department, all in the department's own account; a company-wide PII
       guardrail; and a check, on every load, that each user can read its tables and nothing else.
   * - Smarter features
     - SqlConnection, Secret, SqlPlugin, LLMClient, Guardrail, Budget, account sharing (ADR-036)
   * - Outcome
     - Four assistants, Harper, Ledger, Reel and Ada, with 11 SQL tools between them; only one database user of
       seven may read compensation; every department's AI spending capped at $150 a month.

Executive summary
-----------------

The fastest way to give a department an AI assistant over a database is to hand the assistant a connection and let
the model write SQL. It is also the way to let any member of any department ask for the chief executive's salary,
and get it, the first time someone phrases the question well. The model is not the place to enforce
confidentiality: it can be persuaded, it can be mistaken, and its instructions are not a control that an auditor
can test.

Stackademy enforces it in three layers, each of which holds on its own. The **database** gives each department a
read-only user that may read only that department's tables, so that no query, however it is written, returns
another department's records. **Smarter's accounts** keep each department's connection, and the Secret that holds
its password, in the department's own account, where only its members may use them. And the **assistants** do not
write SQL: each has a few SqlPlugins, fixed, reviewed queries that take parameters, so what an assistant can ask is
known in advance.

Two further controls apply to everything that reaches a model: a guardrail that redacts credit card and social
security numbers from every message, shared by IT with the whole company, and a monthly budget per department,
which blocks the department's assistant and tools when it is spent.

The result is four assistants over one database, whose confidentiality can be proven by a query, ``SHOW GRANTS``,
that runs every time the database is loaded.

Background
----------

Stackademy keeps its back office in one MariaDB database, ``stackademy``, because its records are connected: an
enrollment belongs to a student and a cohort, a payment to an enrollment, a ledger line to a department, an
instructor's salary to an employee. A generator, ``scripts/generate_backoffice.py``, writes the whole database
from a fixed random seed: 40 employees, 320 students, 725 enrollments in 2025, 2,502 general ledger lines and the
departments' monthly budgets. Every question about it has the same answer every time, which makes it possible to
check an assistant's answers.

The departments' needs overlap. HR needs the directory of employees, and compensation. Accounting needs the
directory too, to allocate payroll, and enrollments and payments, to recognize revenue, but not compensation
records, from which it would learn each person's salary. Admissions needs students, enrollments and corporate
contracts. Course Content needs the catalogue and its production schedule, and the directory, to assign work.

The challenge
-------------

The organization set four requirements:

1. **No department reads another's confidential records**, whatever its members ask its assistant, and whatever
   the assistant does.
2. **The control must be testable.** "The assistant's instructions forbid it" is not a control; a grant that a
   query can check is.
3. **The credentials stay with the department.** A department's database password must not be usable outside it,
   even by mistake.
4. **AI spending is bounded per department**, so that one department's experiments can't spend another's money.

And one fact made them hard: the departments share tables. ``employees`` is read by HR, Accounting and Course
Content; ``enrollments`` by Admissions and Accounting. So "one schema per department" would have meant copying
data, and keeping the copies in step.

Options considered
------------------

.. list-table::
   :header-rows: 1
   :widths: 28 36 36

   * - Option
     - For
     - Against
   * - One connection; the model writes SQL; the system prompt lists what it may not read
     - Quick to build; answers any question
     - Confidentiality rests on the model's compliance; a reworded question, or a mistake, reads salaries
   * - A database per department, with copies of the shared tables
     - Strong isolation
     - Copies drift; reports across departments disagree; four times the data to secure
   * - Row-level security, or views per department
     - Fine-grained
     - MariaDB has no row-level security; a view per question multiplies objects without adding much over
       table grants
   * - **A read-only database user per department, granted its tables; fixed SQL tools** (chosen)
     - Enforced by the database, checked by a query; shared tables are shared by granting them twice
     - Confidentiality is per table: a column that one department may read and another may not must live in a
       table of its own, as compensation does

The chosen design accepts the last point and designs the schema around it: salaries are not a column of
``employees`` but rows of ``compensation``, so that the directory can be shared and the pay cannot.

The solution
------------

**Grants in the database.** The generator writes the grants along with the data. Each department's user is created
with every privilege revoked, then granted ``SELECT`` on its tables, one by one:

.. code-block:: sql

   CREATE USER IF NOT EXISTS 'stackademy_hr'@'%' IDENTIFIED BY 'stackademy_hr';
   REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'stackademy_hr'@'%';
   GRANT SELECT ON `stackademy`.`departments` TO 'stackademy_hr'@'%';
   GRANT SELECT ON `stackademy`.`employees` TO 'stackademy_hr'@'%';
   GRANT SELECT ON `stackademy`.`compensation` TO 'stackademy_hr'@'%';
   GRANT SELECT ON `stackademy`.`pto_balances` TO 'stackademy_hr'@'%';
   GRANT SELECT ON `stackademy`.`pto_requests` TO 'stackademy_hr'@'%';
   GRANT SELECT ON `stackademy`.`job_requisitions` TO 'stackademy_hr'@'%';

.. figure:: /_static/case-studies/access-matrix.svg
   :alt: A matrix of six database users against seven groups of tables. Only the HR user reads HR records; the
         executive user reads only the board views.
   :width: 100%

   Exhibit 1. What each department's database user may read.

The executives' user is the extreme case. It reads no table at all, only five views of totals, written ``SQL
SECURITY DEFINER`` so that they read the tables with their definer's rights and return only aggregates, such as a
department's headcount and payroll, never a person's salary. That design, and why it mattered, is the subject of
:doc:`the-board-pack`.

**Credentials in the department's account.** Each department has a SqlConnection, which names its database user,
and a Secret, which holds the password. The connection names the Secret; the password never appears in a manifest:

.. code-block:: yaml

   # departments/hr/connections/stackademy-hr-db.yaml
   apiVersion: smarter.sh/v1
   kind: SqlConnection
   metadata:
     name: stackademy_hr_db
     version: 1.0.0
   spec:
     connection:
       dbEngine: django.db.backends.mysql
       hostname: smarter-mariadb
       port: 3306
       database: stackademy
       username: stackademy_hr
       password: stackademy_hr_db_password   # the name of a Secret, not the password itself
       authenticationMethod: tcpip
       useSsl: false

Both live in Stackademy HR's account, which shares with no one (see :doc:`organizing-for-ai`). The Head of IT
manages them, as administrator of HR's account, but they are HR's: a member of Accounting can't name
``stackademy_hr_db`` in a plugin, because to them it doesn't exist.

**Fixed queries, not generated ones.** Each assistant's tools are SqlPlugins: a reviewed query, its parameters, and
a limit on the rows it returns. The model chooses a tool and fills in its parameters; it does not write SQL.

.. code-block:: yaml

   # departments/hr/plugins/stackademy-hr-headcount.yaml (abridged)
   kind: SqlPlugin
   metadata:
     name: stackademy_hr_headcount
     description: 'Headcount and pay by department: how many people each department has, and their average,
       lowest and highest salary.'
   spec:
     connection: stackademy_hr_db
     sqlData:
       limit: 25
       sqlQuery: |
         SELECT d.name AS department, COUNT(e.employee_id) AS headcount,
           ROUND(AVG(c.annual_salary), 0) AS average_salary, ...
         FROM employees e
         JOIN departments d ON d.department_id = e.department_id
         JOIN compensation c ON c.employee_id = e.employee_id AND ...
         WHERE (d.name LIKE CONCAT('%', {department}, '%') OR {department} IS NULL)
         GROUP BY d.name
       parameters:
         - name: department
           type: string
           required: false

.. figure:: /_static/case-studies/access-path.svg
   :alt: A chain from Harper, HR's assistant, through its SQL tools, the SqlConnection stackademy_hr_db and its
         Secret, the database user stackademy_hr, to HR's tables, all in Stackademy HR's account. Below it, IT's
         PII guardrail, the department's budget and the database's own grants.
   :width: 100%

   Exhibit 2. How HR's assistant reaches HR's records, and nothing else.

**A shared guardrail and a budget per department.** Every department's assistant lists
``stackademy_pii_redaction``, IT's guardrail, which redacts credit card and US social security numbers from each
message before it reaches the model. IT's account shares it with the company, so each department uses one
definition, which IT maintains. And each department has a Budget, ``stackademy_<department>_ai``, of $150 a month
and $1,800 in all, over its assistant and its plugins, which blocks them when it is spent, with a message that says
whom to ask.

.. code-block:: yaml

   # budgets/stackademy-hr-ai.yaml (abridged)
   kind: Budget
   metadata:
     name: stackademy_hr_ai
   spec:
     config:
       unit: cost
       period: month
       periodicLimit: 150.0
       absoluteLimit: 1800.0
       action: block
       warningThreshold: 80
       message: Stackademy HR has used this month's AI budget. Ask Stackademy's CFO to raise it.
     resources:
       - kind: LLMClient
         name: stackademy_hr_assistant
         accountNumber: 2718-2818-0002
       - kind: SqlPlugin
         name: stackademy_hr_headcount
         accountNumber: 2718-2818-0002

Implementation
--------------

The grants are data, not configuration. The generator holds one table of department users and their tables,
``GRANTS``, and writes from it both the SQL above and ``scripts/backoffice-grants.txt``, a plain list of each user
and its tables. The script that loads the database, ``scripts/create-course-database.sh``, then checks the result
against that list, user by user, with ``SHOW GRANTS``, and fails if any user may read a table it isn't listed for,
or can't read one it is:

.. code-block:: console

   checked: stackademy_hr may read its 6 tables, and nothing else
   checked: stackademy_accounting may read its 15 tables, and nothing else
   checked: stackademy_executive may read its 5 tables, and nothing else

Two details matter more than they appear to. Each user's privileges are revoked before they are granted, so that a
user that an earlier version of the database let read everything is narrowed on the next load rather than keeping
what it had. And the former course database, with users that could read all of it, is dropped by the same script,
which checks that it and its users are gone.

The work is two commits to the Stackademy repository, ``cc6099e`` (the back office, with a read-only user per
department) and ``de78c18`` (four departments' assistants, their SQL tools and budgets), and the tests of the
generator, ``4ac6392``, which check among other things that no user but HR's is granted ``compensation``.

Results
-------

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Measure
     - Result
   * - Database users, and tables each may read
     - 7 users. HR 6 tables, Accounting 15, Admissions 8, Course Content 8, the catalogue 4, its proxy 4, the
       executives 5 views and no table
   * - Users that may read compensation
     - 1 of 7: HR's
   * - Where that is proven
     - ``SHOW GRANTS`` for every user, on every load of the database, against the generated list
   * - Assistants, and their SQL tools
     - 4 assistants with 11 tools: HR 3, Accounting 4, Course Content 2, Admissions 2; and the executives' 6 tools
       over the board views
   * - SQL written by a model
     - None: every query is a reviewed SqlPlugin
   * - AI spending per department
     - At most $150 a month and $1,800 in all; the assistant and its tools are blocked when it is spent

Lessons for practitioners
-------------------------

- **Enforce confidentiality below the model.** Instructions to a model are a request, not a control. Put the
  boundary where the data is, and make it something a query can check.
- **Design the schema for the grants.** Table grants are simple and auditable, but they are per table. A field
  that one audience may read and another may not, such as pay, belongs in a table of its own.
- **Revoke, then grant.** Grants that are only ever added accumulate. Rebuild them from the declared list each
  time, and check the result against it.
- **Fixed tools before free SQL.** A tool that runs a reviewed query with parameters is less flexible than a model
  that writes SQL, and much easier to trust. Add free SQL, if ever, over a user whose grants already make the
  worst query harmless.
- **Keep credentials with their audience.** A connection lives in the account whose members may use it, even when
  someone in another department manages it.
- **Cap spending where it is decided.** A budget per department makes the cost of each assistant visible to the
  people who use it, and stops one department's experiment from spending another's money.

Sources
-------

- The Stackademy repository: ``scripts/generate_backoffice.py`` (``GRANTS``, ``BOARD_VIEWS``),
  ``scripts/backoffice-grants.txt``, ``scripts/create-course-database.sh``, ``departments/``, ``budgets/``:
  https://github.com/smarter-sh/stackademy
- Stackademy commits ``cc6099e``, ``de78c18`` and ``4ac6392``
- :doc:`ADR-036: Account Hierarchy and Resource Sharing </adr/036-account-hierarchy>`
- :doc:`/smarter-resources/smarter-guardrail`
