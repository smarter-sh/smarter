The Economics of AI: Four-Week Online Course
============================================

A four-week online course on what AI applications cost and what they are worth. Smarter records
every model call as a `charge
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/account/models/charge.py>`__,
with its tokens and its cost in USD, against the user, the application and the account that made it,
priced from a table of `prices per million tokens
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/account/models/llm_prices.py>`__.
Self-hosted GPU nodes are charged by the hour from the `price of each compute profile
<https://github.com/smarter-sh/example-manifests/tree/main/llmhost-computes>`__, and
`Budget manifests
<https://github.com/smarter-sh/example-manifests/tree/main/budgets>`__
turn spending limits into enforced controls, so students measure real costs and test real policies
rather than estimate them. There are twelve 30-minute recorded lectures and a 90-minute live session
each week. Week 1 covers unit costs, week 2 infrastructure and total cost of ownership, week 3 value
and business cases, and week 4 controls and the wider economy. No programming is needed. See
:doc:`../course-formats` for the format, the grading scale and the course policies, and
:doc:`../ai-economics` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Business, economics, finance and management students and professionals.
   * - **Deployment**
     - A shared Smarter instance run by the instructor, with at least three models from two or
       more providers configured.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Expect less than $10 USD of model charges per student, capped by a per-student
       :doc:`Budget </smarter-resources/smarter-budget>`.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain how model providers price requests, and predict the cost of a conversation.
2. Measure and compare the cost, latency and quality of AI tasks across models and designs.
3. Build a total cost of ownership model for an AI application, including infrastructure and
   people, and compare build, buy and self-host options.
4. Build a business case with scenarios and sensitivity analysis.
5. Design and implement budget policies and chargeback.
6. Discuss the macroeconomics of AI: prices, market structure, labor and productivity.

Technical Prerequisites
-----------------------

- **Required:** a computer with a current web browser, a reliable connection for video calls, and
  a spreadsheet program.
- **Required:** spreadsheet basics: formulas, references and charts.
- **Required:** reading a YAML file well enough to change a value (`Learn YAML in Y minutes
  <https://learnxinyminutes.com/docs/yaml/>`__).
- **Helpful:** introductory microeconomics, and net present value.
- **Not needed:** programming.

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
     - Lecture 1
     - **The unit of AI cost.** Tokens, input and output prices, cached input, and conversation
       length.
   * - 1
     - Lecture 2
     - **Quality and latency.** Model tiers, reasoning models, and comparing models fairly.
   * - 1
     - Lecture 3
     - **Design choices that cost money.** Tools, retrieval, long system prompts and multi-step
       workflows as cost multipliers. Guardrails are one too: the lab "Compare the costs" and the
       note "Ordering is a cost control" in the case study `Guardrails: Can You Trust the Model?
       <https://smarter.sh/case-studies/guardrails>`__ show a cheap keyword check sparing the
       price of an LLM judge.
   * - 1
     - Live session 1
     - Smarter's cost records and the dashboard, live. Groups price a conversation by hand. Start
       Assignment 1.
   * - 2
     - Lecture 4
     - **Infrastructure.** Fixed and variable costs, the baseline cost of a cluster (about $350
       USD a month for Smarter), and the marginal cost per user.
   * - 2
     - Lecture 5
     - **Self-hosting.** GPU costs, utilization, and when an open model on
       :doc:`LLMHost </smarter-resources/smarter-llmhost>` beats paying per token, priced from
       Smarter's seven built-in compute profiles, from one L4 at about $0.98 an hour to eight
       H100s at about $55 an hour.
   * - 2
     - Lecture 6
     - **Total cost of ownership.** People, support, switching costs, and build versus buy.
   * - 2
     - Live session 2
     - Review of Assignment 1. A total cost of ownership exercise in groups. Start Assignment 2.
   * - 3
     - Lecture 7
     - **Measuring value.** Time saved, deflection, revenue, quality, and the difficulty of
       measuring productivity, tested on the case study `Converge or Diverge: AI Coding Agents
       <https://smarter.sh/case-studies/ai-coding-agents>`__: about 25 times the author's
       long-run pace, and the question of what to measure instead of lines of code.
   * - 3
     - Lecture 8
     - **The business case.** Adoption curves, scenarios, sensitivity, net present value, and
       presenting to a CFO.
   * - 3
     - Lecture 9
     - **Pricing an AI product.** Per-seat, per-use and outcome-based pricing, and margins when
       your costs are per token.
   * - 3
     - Live session 3
     - Review of Assignment 2. Students critique each other's business case assumptions.
       Capstone proposals discussed. Start Assignment 3.
   * - 4
     - Lecture 10
     - **Controlling spending.** :doc:`Budgets </smarter-resources/smarter-budget>`, warnings,
       limits, :doc:`cost accounting </smarter-platform/cost-accounting>` and chargeback.
   * - 4
     - Lecture 11
     - **Market structure.** Falling prices, open versus closed models, the data center build-out
       and vendor concentration.
   * - 4
     - Lecture 12
     - **Labor and productivity.** Automation and augmentation, who gains and who loses, and the
       evidence so far.
   * - 4
     - Live session 4
     - Capstone presentations (about 6 minutes each, with 2 minutes of questions), and a course
       retrospective.

Assignments 1 to 3 are due before the next live session. Assignment 4 is due in the middle of week
4. The capstone proposal is due before Live session 3, and the capstone at the start of Live
session 4.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: The Cost of a Design
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students take one task and run it four ways: a small model, a large model, the small model with a
tool plugin, and the small model with a long system prompt. They measure cost, latency and quality,
and explain what drives the differences.

**Turn in:** the spreadsheet, a chart, and a one-page explanation.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Data
     - 6
     - Complete, from Smarter's records, with repeated runs.
     - Missing or estimated.
   * - Cost drivers
     - 6
     - Explains each difference by tokens and calls.
     - Reports differences without causes.
   * - Quality
     - 4
     - Scored with a stated rubric.
     - Impressions.
   * - Presentation
     - 4
     - A clear chart and concise writing.
     - Raw data only.

Assignment 2: Total Cost of Ownership
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students build a three-year total cost of ownership model for an assistant used by 1,000
employees, comparing a commercial model provider with a self-hosted open model, and find the
usage level at which the cheaper option changes.

**Turn in:** the spreadsheet model with a break-even chart, and a one-page summary.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Completeness
     - 6
     - Model charges, GPUs, cluster, people and support.
     - Model charges and GPUs only.
   * - Evidence
     - 5
     - Measured or sourced figures.
     - Unsourced.
   * - Break-even
     - 5
     - Correct crossover, explained.
     - Missing or wrong.
   * - Summary
     - 4
     - States the conditions under which each option wins.
     - Picks one without conditions.

Assignment 3: Business Case
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students build a three-year business case for an AI application with three adoption scenarios, a
net present value and a sensitivity analysis on the two most uncertain assumptions.

**Turn in:** the spreadsheet and a two-page memo.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Costs and benefits
     - 6
     - Measured costs, measurable benefits.
     - Vague benefits.
   * - Scenarios and NPV
     - 5
     - Three scenarios, correct NPV.
     - One scenario, or NPV errors.
   * - Sensitivity
     - 5
     - Identifies and tests the key assumptions.
     - Not done.
   * - Memo
     - 4
     - Clear recommendation.
     - No recommendation.

Assignment 4: Budget Policy and Chargeback
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students design budget limits and a chargeback scheme for an organization with three departments
and four AI applications, implement the budgets in Smarter, and produce a mock monthly chargeback
report from cost accounting data.

**Turn in:** a one-page policy, the manifests, evidence of a limit reached, and the chargeback
report.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Policy
     - 5
     - Limits and chargeback rules that are fair and explained.
     - Arbitrary.
   * - Implementation
     - 6
     - Manifests enforce the policy; limit shown.
     - Mismatch, or not shown.
   * - Chargeback report
     - 5
     - Accurate allocation from real cost data.
     - Made-up figures.
   * - Incentives
     - 4
     - Discusses how the scheme changes behavior.
     - Not discussed.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and present it in Live session 4.

Capstone A: An AI Product Business Plan
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design the economics of an AI product: unit costs, pricing, margins and
growth, grounded in measured costs.

Students propose an AI product sold to customers, such as an assistant for small law firms or a
tutor for language learners. They build a prototype in Smarter, measure its unit costs on thirty
realistic tasks, choose a pricing model, and build a three-year plan.

**What students turn in:**

- The prototype manifests and measured results.
- A financial model: unit costs, pricing, gross margin per customer, customer growth, fixed costs,
  break-even and sensitivity.
- A five-page business plan, and a six-minute pitch.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Unit economics
     - 25
     - Measured unit costs, margin per customer, heavy-user risk addressed.
     - Price-list costs; heavy users ignored.
   * - Pricing
     - 20
     - Pricing model justified against costs and competitors.
     - Arbitrary price.
   * - Financial model
     - 20
     - Complete, with break-even and sensitivity.
     - Incomplete.
   * - Risks
     - 15
     - Model price changes, vendor dependence and competition.
     - Not discussed.
   * - Plan and pitch
     - 20
     - Clear, persuasive and on time.
     - Unclear or overruns.

Capstone B: An AI Spending Strategy for an Organization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Advise an organization on how much to spend on AI, where, and how to keep
control, using total cost of ownership, business cases and budgets together.

A fictional organization of 3,000 people asks for an AI spending strategy for the next two years.
Students identify three candidate applications, build a business case for each, compare provider
and self-hosting options, design budgets and chargeback, and implement the budgets in Smarter.

**What students turn in:**

- A six-page strategy: priorities, business cases, sourcing choices, budget policy and governance
  of spending.
- The supporting spreadsheets.
- The budget manifests, with evidence that they work.
- A six-minute presentation to the "executive team" (the class).

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Prioritization
     - 20
     - Applications ranked by value and feasibility, with evidence.
     - No ranking or rationale.
   * - Business cases
     - 20
     - Sound, with scenarios.
     - Superficial.
   * - Sourcing
     - 20
     - Build, buy and self-host compared on total cost of ownership.
     - One option assumed.
   * - Controls
     - 20
     - Budgets and chargeback implemented and shown.
     - Proposed only.
   * - Presentation
     - 20
     - Clear decisions requested, on time.
     - Data without decisions.

Recommended Texts
-----------------

- **Required:** Ajay Agrawal, Joshua Gans and Avi Goldfarb, *Prediction Machines* (updated
  edition, Harvard Business Review Press, 2022), in weeks 1 and 3.
- **Required:** J.R. Storment and Mike Fuller, *Cloud FinOps* (2nd edition, O'Reilly, 2023), in
  weeks 2 and 4.
- **Required:** Daron Acemoglu and Simon Johnson, *Power and Progress: Our Thousand-Year Struggle
  Over Technology and Prosperity* (PublicAffairs, 2023), selected chapters, in week 4.
- **Optional:** Ajay Agrawal, Joshua Gans and Avi Goldfarb, *Power and Prediction: The Disruptive
  Economics of Artificial Intelligence* (Harvard Business Review Press, 2022), on system-level
  change.
- **Smarter documentation:** :doc:`/smarter-platform/cost-accounting`,
  :doc:`/smarter-resources/smarter-budget`, :doc:`/smarter-resources/smarter-provider`,
  :doc:`/smarter-resources/smarter-llmhost` and :doc:`kubernetes <../kubernetes>` (for the
  infrastructure figures).

Further Study
-------------

.. include:: further-study.txt
