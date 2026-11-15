Case Studies
============

A Smarter case study takes one complex, non-trivial problem, of the kind that a business or an IT department meets
in practice, and follows it all the way to a working solution built on the Smarter platform. It first defines the
problem: the situation, the constraints, and what is at stake if it goes unsolved. It then weighs the options, and
presents the solution that was chosen in enough detail to rebuild it: its manifests, its code, its configuration and
the decisions behind them. It closes with what the solution achieved, and what other organizations can take from it.

Every claim in a case can be checked. The resources it describes are real, declared in public repositories, and the
fixes it reports are commits in the Smarter repositories, which the case cites. So a reader can verify what it says,
and reproduce its results on their own platform.

Most of the cases follow :ref:`Stackademy <case-studies-stackademy>`, a fictional code academy whose accounts,
assistants and database every Smarter platform loads when it is set up. Others, such as :doc:`the-smarter-doodle`,
are about the Smarter Project itself.

.. list-table::
   :header-rows: 1
   :widths: 30 45 25

   * - Case
     - The problem
     - Read it for
   * - :doc:`shadow-ai`
     - Departments built their own AI projects before there was a platform: no one knows how many, what they cost,
       or what private data they send to AI providers. Each must keep running while it is brought under control.
     - AI governance, API keys and budgets, migration without outage, data minimization
   * - :doc:`ask-stanley`
     - Prospective students in eleven countries need timely, accurate answers about courses and prices, which three
       advisors in one time zone can't give at every hour, and a general chatbot can only guess.
     - Customer-facing AI, tool calling, grounding answers in live data
   * - :doc:`organizing-for-ai`
     - The company's data is in open systems, but only two of its 40 employees can write SQL or call an API. Each
       department now asks its own assistant in plain language, with no loss of confidentiality.
     - Productivity, organizational design, identity and access
   * - :doc:`confidential-by-construction`
     - Four departments want AI assistants over one company database, without any of them seeing another's
       records, salaries above all.
     - Least privilege, data governance, AI cost control
   * - :doc:`the-board-pack`
     - The executives want one board pack from four departments' assistants, each behind its own account.
     - Multi-agent orchestration, authorization, architecture decisions
   * - :doc:`the-smarter-doodle`
     - The Smarter Project wants its sign-in page decorated for each region's special days, as a search engine's is,
       with no artists and no one to decide which days are special.
     - Workflow automation, AI with Python and Django, guardrails, LLM-as-judge, untrusted output

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
- **Sources**: the decisions, code and commits behind every claim.

The executive summaries and exhibits stand on their own, e.g. to explain to a decision maker what an AI platform
must do before a department may trust it. The Stackademy cases can also be reproduced on any Smarter platform, where
Stackademy is already loaded.

.. _case-studies-stackademy:

Stackademy
----------

Five of the cases follow one organization, Stackademy, as it puts AI assistants to work across its departments: how
it organized its teams in Smarter (:doc:`organizing-for-ai`), how it kept each department's records confidential
(:doc:`confidential-by-construction`), how its executives came to combine the departments' assistants into one
board pack (:doc:`the-board-pack`), how it answers prospective students, at any hour, from its own course
catalogue (:doc:`ask-stanley`), and how it took control of the AI projects its departments had built before it had a
platform (:doc:`shadow-ai`).

Stackademy is fictional, but nothing else in its cases is. Its accounts, people, assistants, database and
orchestrator are real resources, declared in the public repository
`smarter-sh/stackademy <https://github.com/smarter-sh/stackademy>`__, which every Smarter platform loads when it is
set up. The problems are the ones that came up while building it, and the figures are the ones its database
returns.

Stackademy is an online code academy, with 48 courses in programming, cloud and AI, taught mostly to companies
that buy team licenses, and also to individual students. In its fiscal year 2025 it had 40 employees in seven
departments, nine corporate contracts for 870 seats, 320 individual students in 45 cohorts, and about $4.4 million
of revenue, most of it from the corporate contracts. Its records, from payroll to
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

   organizing-for-ai
   confidential-by-construction
   the-board-pack
   ask-stanley
   shadow-ai
   the-smarter-doodle
