Case Studies
============

These case studies follow one organization, Stackademy, as it puts AI assistants to work across its departments:
how it organized its teams in Smarter, how it kept each department's records confidential, how its executives came
to combine the departments' assistants into one board pack, how it learned to trust the figures that its
assistants report, the security review that the work made necessary, and a release that published but never
shipped. Each one presents a complex business or IT problem, the options that were weighed, the solution that was
chosen and why, what it achieved, and what other organizations can take from it.

Stackademy is fictional, but nothing else in these cases is. Its accounts, people, assistants, database and
orchestrator are real resources, declared in the public repository
`smarter-sh/stackademy <https://github.com/smarter-sh/stackademy>`__, which every Smarter platform loads when it is
set up. The problems are the ones that came up while building it, the figures are the ones its database returns,
and the fixes are commits in the Smarter repositories, which each case cites. So a reader can check any claim, and
a class can reproduce any result on its own platform.

.. list-table::
   :header-rows: 1
   :widths: 30 45 25

   * - Case
     - The problem
     - Read it for
   * - :doc:`case-studies/organizing-for-ai`
     - An organization of departments needs shared services, private records, and administrators for each team,
       on a platform whose accounts had no relation to one another.
     - Multi-tenant design, identity and access, configuration as code
   * - :doc:`case-studies/confidential-by-construction`
     - Four departments want AI assistants over one company database, without any of them seeing another's
       records, salaries above all.
     - Least privilege, data governance, AI cost control
   * - :doc:`case-studies/the-board-pack`
     - The executives want one board pack from four departments' assistants, each behind its own account.
     - Multi-agent orchestration, authorization, architecture decisions
   * - :doc:`case-studies/when-the-numbers-dont-add-up`
     - The assistants' financial figures were wrong four different ways, each plausible, one of them repeated in
       every board pack.
     - Accuracy assurance, financial reporting, AI risk
   * - :doc:`case-studies/governance-review`
     - Loading the organization exposed twelve flaws, from a path for a customer's staff to take over any account
       to credentials written to the logs.
     - Security review, privilege escalation, secure defaults
   * - :doc:`case-studies/release-incident`
     - A release published its version, then failed, and nothing it should have shipped was built.
     - Release engineering, incident analysis, CI/CD

Using the cases
---------------

Each case is self-contained, and follows the same structure, so that a reader who knows one can find their way in
any other:

- **At a glance**: the organization, the challenge, the solution and the outcome, in one table.
- **Executive summary**: the case in four paragraphs, for a reader with five minutes.
- **Background** and **The challenge**: the situation, the constraints, and what was at stake.
- **Options considered**: the alternatives, and why each was or wasn't chosen.
- **The solution** and **Implementation**: what was built, with its exhibits, configuration and code.
- **Results** and **Lessons for practitioners**: what it achieved, measured, and what transfers.
- **Teaching notes**: discussion questions, and exercises that students carry out on a Smarter platform.
- **Sources**: the decisions, code and commits behind every claim.

In a course, assign a case before the session, and use its discussion questions to open it: each case has at least
one question without a single right answer. Its exercises turn the case into a lab, on a platform set up as the
:doc:`Smarter Instructor Guide </smarter-instructor>` explains, where Stackademy is already loaded. The
:doc:`master-classes/ai-application-development` and :doc:`master-classes/python-agentic-ai` fit them best, and
:doc:`master-classes` explains how their sessions run. Outside a course, the executive summaries and exhibits stand
on their own, e.g. to explain to a decision maker what an AI platform must do before a department may trust it.

Stackademy at a glance
----------------------

Stackademy is an online code academy, with 48 courses in programming, cloud and AI, taught to individual students
and to companies that buy team licenses. In its fiscal year 2025 it had 40 employees in seven departments, 320
students in 45 cohorts, nine corporate contracts, and about $4.4 million of revenue. Its records, from payroll to
the general ledger, are in one MariaDB database, ``stackademy``, of 25 tables, which a generator writes from a fixed
random seed, so that every question about them has the same answer every time.

.. figure:: /_static/case-studies/org-chart.svg
   :alt: Stackademy's accounts: the company, Stackademy Corp, under the Smarter platform, with five department
         accounts below it, IT, HR, Accounting, Course Content and Admissions, each with its administrator, a member
         and its assistant.
   :width: 100%

   Exhibit 0. Stackademy's accounts, people and assistants.

In Smarter, each department is an **account**, and the accounts form a tree under the company's,
``Stackademy Corp``. Ten employees may sign in. Each department's head administers their department's account, the
Head of IT administers every account, to manage its credentials, and the chief executive is a member of every
department. Each department has an assistant over its own records: **Harper** for HR, **Ledger** for Accounting,
**Reel** for Course Content and **Ada** for Admissions. The executives have **Atlas**, the Board Pack. All of them
are fictional, and sign in with a published demonstration password; the
:doc:`Stackademy page </smarter-framework/smarter-manifests/stackademy>` describes the repository and its
original course catalogue assistants.

.. toctree::
   :maxdepth: 1
   :hidden:

   case-studies/organizing-for-ai
   case-studies/confidential-by-construction
   case-studies/the-board-pack
   case-studies/when-the-numbers-dont-add-up
   case-studies/governance-review
   case-studies/release-incident
