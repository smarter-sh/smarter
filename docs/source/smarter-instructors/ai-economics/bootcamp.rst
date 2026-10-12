The Economics of AI: Classroom Bootcamp
=======================================

An eight-hour classroom bootcamp on what AI applications really cost, and what they are worth.
Students measure the cost of real requests in Smarter, compare models on cost and quality, build a
business case, and design a budget policy that Smarter enforces. No programming is needed. See
:doc:`../course-formats` for the standard bootcamp day, the grading scale and the course policies,
and :doc:`../ai-economics` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Business, economics, finance and management students, and professionals who must approve
       or budget for AI projects.
   * - **Deployment**
     - A shared Smarter instance run by the instructor, with at least three models from two or
       more providers configured.
   * - **Cost**
     - Expect less than $3 USD of model charges per student, capped by a per-student
       :doc:`Budget </smarter-resources/smarter-budget>`. That cap is itself a teaching example.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Explain how model providers price requests (input and output tokens, cached tokens) and what
   drives the cost of a conversation.
2. Measure the cost, latency and quality of an AI task, and compare models on all three.
3. Estimate the full cost of an AI application, including model charges and infrastructure, per
   user per month.
4. Build a business case that weighs those costs against measurable benefits.
5. Design a budget policy that turns spending limits into enforced controls.

Technical Prerequisites
-----------------------

- **Required:** a laptop with a current web browser and a spreadsheet program (Excel, Google
  Sheets or Numbers), and experience of using a chat assistant.
- **Required:** spreadsheet basics: formulas, references, charts.
- **Required:** reading a YAML file well enough to change a value (`Learn YAML in Y minutes
  <https://learnxinyminutes.com/docs/yaml/>`__).
- **Helpful:** introductory microeconomics (marginal cost, fixed and variable costs) and a basic
  business case or net present value calculation.
- **Not needed:** programming.

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
     - **Lecture 1: The unit of AI cost.** Tokens, input and output prices, context length,
       cached input, and why a long conversation costs more than its last message. Reading a
       provider's price list.
   * - 2
     - 45
     - **Lab 1: Price a conversation.** Hold three conversations of different lengths, read their
       tokens and costs in Smarter's records, and rebuild the costs in a spreadsheet from the
       price list. Produces Assignment 1.
   * - 3
     - 45
     - **Lecture 2: Quality costs money, sometimes.** Model tiers, reasoning models, tools and
       retrieval as cost multipliers. Latency as a cost. Why the cheapest model is sometimes the
       most expensive choice.
   * - 4
     - 45
     - **Lab 2: The model comparison.** Run the same ten tasks on three models from different
       providers, and record cost, latency and a quality score for each. Produces Assignment 2.
   * - 5
     - 45
     - **Lecture 3: Infrastructure.** Fixed and variable costs of running an AI platform. The
       baseline cost of a Kubernetes cluster (about $350 USD a month for Smarter), the marginal
       cost per user, and economies of scale. Self-hosting a model versus paying per token.
   * - 6
     - 45
     - **Lecture 4: The business case.** Benefits that can be measured (time saved, tickets
       deflected, revenue), adoption curves, and sensitivity analysis. Productivity research and
       its limits.
   * - 7
     - 45
     - **Lab 3: A business case.** Build a one-year cost and benefit model for an AI application
       for a fictional company, using the costs measured in Labs 1 and 2. Produces Assignment 3.
   * - 8
     - 45
     - **Lecture 5: Controlling spending.** :doc:`Budgets </smarter-resources/smarter-budget>` on
       users, applications, accounts and providers; warnings and hard limits;
       :doc:`cost accounting </smarter-platform/cost-accounting>` and chargeback to departments.
       The built-in budget examples.
   * - 9
     - 45
     - **Lab 4: Hit the limit.** Apply a small budget to yourself, use it up, and see what happens.
       Then design the warning that should have come first. Ungraded.
   * - 10
     - 45
     - **Lecture 6: The bigger picture.** Prices falling over time, the data center build-out,
       vendor concentration, labor market effects, and who captures the value of AI.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone and a company, and sketch their model with
       the instructor's feedback.

Graded Assignments
------------------

Assignment 1: Anatomy of a Bill
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students reconstruct the cost of three conversations of different lengths from the provider's price
list, compare their figures with Smarter's records, and explain why cost grows faster than the
number of messages.

**Turn in:** the spreadsheet and a half-page explanation.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Reconstruction
     - 8
     - Figures match Smarter's records, or the differences are explained.
     - Figures do not match, and the difference is unexplained.
   * - Spreadsheet
     - 4
     - Uses formulas and references, not typed-in results.
     - Hard-coded numbers.
   * - Explanation
     - 6
     - Explains that each request resends the conversation so far.
     - Says only that longer conversations cost more.
   * - Clarity
     - 2
     - Labeled and readable.
     - Unlabeled.

Assignment 2: Model Comparison
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students compare three models on ten tasks, scoring quality with a simple rubric, and recommend one
for a stated use.

**Turn in:** the spreadsheet of cost, latency and quality, a chart, and a one-paragraph
recommendation.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Data
     - 6
     - Complete, from Smarter's records, for all thirty runs.
     - Missing runs, or estimated figures.
   * - Quality scoring
     - 5
     - A stated rubric, applied consistently.
     - Impressions.
   * - Chart
     - 4
     - Shows the cost and quality trade-off clearly.
     - A table only, or a misleading chart.
   * - Recommendation
     - 5
     - Fits the stated use, with the trade-off explained.
     - Picks the cheapest or the best without reasons.

Assignment 3: One-Year Business Case
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students model the costs and benefits of an AI application for a fictional company over one year,
for three adoption scenarios.

**Turn in:** the spreadsheet model and a one-page summary.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Costs
     - 6
     - Model charges from measured data, plus infrastructure and people.
     - Model charges only.
   * - Benefits
     - 5
     - Measurable, with stated assumptions.
     - Vague benefits ("better productivity").
   * - Scenarios
     - 5
     - Low, expected and high adoption, with the break-even point.
     - One scenario.
   * - Summary
     - 4
     - A clear go or no-go recommendation, with the key assumption named.
     - No recommendation.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp.

Capstone A: An Investment Proposal for an AI Application
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build an evidence-based investment proposal for an AI application, from
measured unit costs to a three-year financial model.

Students choose a use case in a real or realistic company, such as customer support, document
review or sales email. They build a prototype assistant in Smarter, measure its cost and quality
on twenty realistic tasks, and use those measurements in a financial model.

**What students turn in:**

- The prototype LLMClient manifest, and the task set with measured results.
- A three-year financial model with costs, benefits, scenarios and sensitivity analysis.
- A three-page investment memo for a chief financial officer.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Measured unit costs
     - 25
     - From the prototype, on realistic tasks, with quality checked.
     - From price lists, not measured.
   * - Financial model
     - 25
     - Complete costs and benefits, scenarios and sensitivity.
     - Missing cost categories or scenarios.
   * - Assumptions
     - 15
     - Stated, sourced, and tested for sensitivity.
     - Hidden or unsupported.
   * - Risks
     - 15
     - Covers quality, adoption, price changes and vendor risk.
     - Not discussed.
   * - Memo
     - 20
     - Clear recommendation a CFO could act on.
     - Data without a recommendation.

Capstone B: A Departmental AI Budget Policy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design and implement a spending policy that balances access to AI with cost
control, and test it.

Students design a budget policy for a fictional university department or company division of
around two hundred users and four AI applications: who gets how much, how limits renew, who is
warned, and how costs are charged back. They implement it in Smarter and simulate a month of use.

**What students turn in:**

- A two-page policy document.
- The budget manifests.
- A simulation spreadsheet of a month's use, showing who hits limits and when, and the total cost.
- Evidence (screenshots) that the manifests behave as the policy says.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Policy design
     - 25
     - Limits based on expected use, fair and explained.
     - Arbitrary or one-size-fits-all.
   * - Implementation
     - 25
     - Manifests apply and enforce the policy.
     - Manifests do not match the policy.
   * - Simulation
     - 20
     - Realistic use patterns and a credible monthly total.
     - Unrealistic or missing.
   * - User experience
     - 15
     - Warnings before limits, and clear messages at them.
     - Users cut off without warning.
   * - Writing
     - 15
     - Clear enough for a department head.
     - Unclear or overlong.

Recommended Texts
-----------------

- **Pre-reading:** Ajay Agrawal, Joshua Gans and Avi Goldfarb, *Prediction Machines: The Simple
  Economics of Artificial Intelligence* (updated edition, Harvard Business Review Press, 2022),
  chapters 1 to 3.
- **Reference:** J.R. Storment and Mike Fuller, *Cloud FinOps* (2nd edition, O'Reilly, 2023), on
  managing variable cloud costs, which applies directly to model charges.
- **Smarter documentation:** :doc:`/smarter-platform/cost-accounting`,
  :doc:`/smarter-resources/smarter-budget` and :doc:`/smarter-resources/smarter-provider`.

Further Study
-------------

.. include:: further-study.txt
