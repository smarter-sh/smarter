The Economics of AI: Two-Week Online Course
===========================================

A two-week online course on what AI applications cost and what they are worth. Smarter records every
model call as a `charge
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/account/models/charge.py>`__,
with its tokens and its cost in USD, against the user, the application and the account that made it,
priced from a table of `prices per million tokens
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/account/models/llm_prices.py>`__.
Self-hosted GPU nodes are charged by the hour from the `price of each compute profile
<https://github.com/smarter-sh/example-manifests/tree/main/llmhost-computes>`__, and
`Budget manifests
<https://github.com/smarter-sh/example-manifests/tree/main/budgets>`__
turn spending limits into enforced controls, so students measure real costs and test real policies
rather than estimate them. There are six 30-minute recorded lectures and a 90-minute live session
each week. Week 1 measures costs, and week 2 builds business cases and controls. No programming is
needed. See :doc:`../course-formats` for the format, the grading scale and the course policies, and
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
     - Expect less than $5 USD of model charges per student, capped by a per-student
       :doc:`Budget </smarter-resources/smarter-budget>`.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain how model providers price requests, and what drives the cost of a conversation.
2. Measure and compare the cost, latency and quality of AI tasks across models.
3. Estimate the full cost per user per month of an AI application, including infrastructure.
4. Build a business case with scenarios and sensitivity analysis.
5. Design a budget policy and implement it as enforced controls.

Technical Prerequisites
-----------------------

- **Required:** a computer with a current web browser, a reliable connection for video calls, and
  a spreadsheet program.
- **Required:** spreadsheet basics: formulas, references and charts.
- **Required:** reading a YAML file well enough to change a value (`Learn YAML in Y minutes
  <https://learnxinyminutes.com/docs/yaml/>`__).
- **Helpful:** introductory microeconomics and a basic business case or net present value
  calculation.
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
     - Lecture 1 (30 min)
     - **The unit of AI cost.** Tokens, input and output prices, cached input, and why long
       conversations cost more than they seem to.
   * - 1
     - Lecture 2 (30 min)
     - **Quality, latency and cost.** Model tiers, reasoning models, tools and retrieval as cost
       multipliers, and comparing models fairly. The lab "Compare the costs" in the case study
       `Guardrails: Can You Trust the Model? <https://smarter.sh/case-studies/guardrails>`__
       shows safety checks as a cost too.
   * - 1
     - Lecture 3 (30 min)
     - **Infrastructure.** Fixed and variable costs, the baseline cost of a cluster (about $350
       USD a month for Smarter), marginal cost per user, and self-hosting versus paying per token.
   * - 1
     - Live session 1 (90 min)
     - Live walk through Smarter's cost records and the dashboard. Groups run a model comparison
       together. Start Assignment 1.
   * - 2
     - Lecture 4 (30 min)
     - **The business case.** Measurable benefits, adoption curves, scenarios, sensitivity, and
       what productivity research does and does not show, tested on the case study `Converge or
       Diverge: AI Coding Agents <https://smarter.sh/case-studies/ai-coding-agents>`__ and its
       claim of about 25 times the author's long-run pace.
   * - 2
     - Lecture 5 (30 min)
     - **Controlling spending.** :doc:`Budgets </smarter-resources/smarter-budget>`, warnings and
       limits, :doc:`cost accounting </smarter-platform/cost-accounting>` and chargeback.
   * - 2
     - Lecture 6 (30 min)
     - **The bigger picture.** Falling prices, the data center build-out, vendor concentration,
       labor market effects, and who captures the value.
   * - 2
     - Live session 2 (90 min)
     - Capstone presentations (about 5 minutes each, with 2 minutes of questions), then a debate:
       will AI be cheaper or more expensive for businesses in five years?

Assignment 1 is due at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
and the capstone at the start of Live session 2.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Measured Model Comparison
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students run twelve realistic tasks on three models from different providers, record cost, latency
and a quality score for each from Smarter's records, and reconstruct one cost from the price list.

**Turn in:** the spreadsheet, a chart of cost against quality, and a one-paragraph recommendation.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Data
     - 6
     - Complete and taken from Smarter's records.
     - Missing runs or estimates.
   * - Price list check
     - 4
     - One cost rebuilt from the price list, with any difference explained.
     - Not attempted, or unexplained mismatch.
   * - Quality scoring
     - 5
     - Stated rubric applied consistently.
     - Impressions.
   * - Recommendation
     - 5
     - Fits a stated use, with the trade-off explained.
     - Cheapest or best, without reasons.

Assignment 2: Cost per User per Month
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students estimate the monthly cost per user of an AI assistant for organizations of 50, 500 and
5,000 users, combining measured model charges, a usage assumption, and infrastructure, and explain
how the cost per user changes with scale.

**Turn in:** the spreadsheet and a one-page explanation with a chart.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Model charges
     - 5
     - From measurements, with a stated usage assumption.
     - Guessed.
   * - Infrastructure
     - 5
     - Fixed and variable costs separated.
     - Infrastructure ignored.
   * - Scale analysis
     - 6
     - Shows and explains economies of scale.
     - Three numbers without explanation.
   * - Assumptions
     - 4
     - Stated and reasonable.
     - Hidden.

Assignment 3: Budget Policy
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students design a budget policy for a team of twenty with two AI applications, implement it in
Smarter, use up a small budget to show the limit working, and propose the warnings that should come
first.

**Turn in:** a one-page policy, the budget manifests and screenshots of the limit.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Policy
     - 6
     - Limits based on expected use, with reasons.
     - Arbitrary.
   * - Implementation
     - 6
     - Manifests enforce the policy.
     - Do not match the policy.
   * - Evidence
     - 4
     - Limit reached and shown.
     - Not shown.
   * - User experience
     - 4
     - Warnings and messages designed for the user.
     - Users cut off without warning.

Capstone Projects
-----------------

Students choose one, and present it in Live session 2.

Capstone A: An Investment Proposal for an AI Application
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build an evidence-based investment proposal, from measured unit costs to a
three-year financial model, and present it to decision makers.

Students choose a use case in a real or realistic company, build a prototype assistant in Smarter,
measure its cost and quality on twenty-five realistic tasks, and use the measurements in a
financial model.

**What students turn in:**

- The prototype manifest and the measured task results.
- A three-year financial model with scenarios and sensitivity analysis.
- A three-page investment memo, and a five-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Measured unit costs
     - 20
     - From the prototype on realistic tasks, quality checked.
     - From price lists.
   * - Financial model
     - 25
     - Complete, with scenarios and sensitivity.
     - Missing categories or scenarios.
   * - Assumptions and risks
     - 20
     - Stated, sourced, tested; risks include price changes and vendor lock-in.
     - Hidden assumptions; risks ignored.
   * - Memo
     - 20
     - Clear recommendation a CFO could act on.
     - No recommendation.
   * - Presentation
     - 15
     - Persuasive and on time.
     - Overruns or reads slides.

Capstone B: Build, Buy or Self-Host
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Compare the total cost of ownership of different ways to provide an AI
capability, and identify the volume at which the best choice changes.

A fictional organization needs an internal assistant for 2,000 employees. Students compare three
options: a commercial chat product with per-seat pricing, an assistant built on Smarter with a
commercial model provider, and an assistant on Smarter with a self-hosted open model on rented GPU
nodes. They measure what they can in Smarter, and research the rest.

**What students turn in:**

- A total cost of ownership model for each option over three years, including people.
- A break-even chart showing which option is cheapest at different usage levels.
- A three-page recommendation, and a five-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Cost completeness
     - 25
     - Licenses, model charges, infrastructure, people and switching costs.
     - Only the obvious costs.
   * - Evidence
     - 20
     - Measured where possible, sourced otherwise.
     - Unsourced numbers.
   * - Break-even analysis
     - 20
     - Correct, with the crossover points explained.
     - Missing or wrong.
   * - Non-financial factors
     - 15
     - Privacy, control, quality and risk weighed.
     - Cost only.
   * - Recommendation and presentation
     - 20
     - Clear, conditional and on time.
     - No clear choice.

Recommended Texts
-----------------

- **Required:** Ajay Agrawal, Joshua Gans and Avi Goldfarb, *Prediction Machines: The Simple
  Economics of Artificial Intelligence* (updated edition, Harvard Business Review Press, 2022).
  Week 1: parts 1 and 2. Week 2: parts 3 to 5.
- **Required:** J.R. Storment and Mike Fuller, *Cloud FinOps* (2nd edition, O'Reilly, 2023),
  chapters on the FinOps lifecycle and unit economics, in week 2.
- **Optional:** Ethan Mollick, *Co-Intelligence* (Portfolio, 2024), on AI and work.
- **Smarter documentation:** :doc:`/smarter-platform/cost-accounting`,
  :doc:`/smarter-resources/smarter-budget`, :doc:`/smarter-resources/smarter-provider` and
  :doc:`/smarter-resources/smarter-llmhost`.

Further Study
-------------

.. include:: further-study.txt
