The Economics of AI
===================

**Why Smarter.** Most discussion of what AI costs relies on estimates, list prices and vendor case
studies. Smarter lets business, economics and management students measure the real cost of an AI
application, and weigh it against quality, on a platform that they can run themselves:

- **Every token is charged.** Each model call, plugin call and tool call is recorded as a
  `charge <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/account/models/charge.py>`__,
  with its provider, model, prompt and completion tokens and cost in USD, against the user, the
  application and the account that used it. A long conversation, a reasoning model or a tool
  call shows up as what it is: more tokens, at a price.
- **Prices are data.** A price is a row of USD per million tokens, markup included, for each
  provider and model, in the
  `LLMPrices <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/account/models/llm_prices.py>`__
  table, so students can rebuild any cost by hand, change a markup, and see a budget respond.
- **Models are interchangeable.** An LLMClient's ``provider`` and ``defaultModel`` are two lines
  of its manifest, so the same tasks run on models from different providers with no other change,
  and the comparison is fair.
- **Self-hosting has a real price.** Smarter's
  `seven built-in compute profiles <https://github.com/smarter-sh/example-manifests/tree/main/llmhost-computes>`__
  carry their AWS on-demand price per hour, from one NVIDIA L4 at about $0.98 to eight H100s at
  about $55, and :doc:`LLMHost </smarter-resources/smarter-llmhost>` charges each ready node by
  the hour, so per-token APIs and open models can be compared on the same records.
- **The platform's own costs are visible.** A shared Smarter instance on a managed Kubernetes
  cluster costs around $350 USD a month, and every resource behind that figure is declared in
  `Terraform <https://github.com/smarter-sh/smarter-infrastructure/tree/main/aws/terraform>`__.
  The variable cost per learner is well under a dollar a month, which makes economies of scale
  concrete. See :doc:`kubernetes`.
- **Budgets enforce policy.** A :doc:`Budget </smarter-resources/smarter-budget>` turns a
  spending limit into an enforced control, in dollars or tokens, per hour, day, week or month, for
  a user, an application, an account, a provider or a GPU. The
  `six example budgets <https://github.com/smarter-sh/example-manifests/tree/main/budgets>`__
  include a $10 monthly allowance for each student and a $200 daily limit on one provider.

**What the course covers.** The unit of AI cost: tokens, input and output prices, cached input and
conversation length; quality, latency and cost, and comparing models fairly; tools, retrieval,
long system prompts and multi-step workflows as cost multipliers; the fixed and variable costs of
running an AI platform, and the marginal cost per user; self-hosting, GPU utilization and total
cost of ownership; measuring value, building a business case with scenarios and sensitivity
analysis, and pricing an AI product; budgets, warnings, limits and chargeback; and the wider
economy: falling prices, open and closed models, the data center build-out, vendor concentration,
and labor and productivity.

**Look at.**

- `example-manifests/budgets/ <https://github.com/smarter-sh/example-manifests/tree/main/budgets>`__,
  six budget policies, each a short manifest with a plain-English description.
- `example-manifests/llmhost-computes/ <https://github.com/smarter-sh/example-manifests/tree/main/llmhost-computes>`__,
  the GPU and CPU node profiles with their hourly prices.
- The charges and budgets on the web console's dashboard, and the cost records of a class's own
  conversations.

Each course plan lists every record, price and manifest that it uses under *Smarter in the Source
Code*.

**Read.** :doc:`/smarter-platform/cost-accounting`, :doc:`/smarter-resources/smarter-budget`,
:doc:`/smarter-resources/smarter-provider`, :doc:`/smarter-resources/smarter-llmhost`, `Django and
httpx: An LLM Proxy That Keeps Provider API Keys Away From Callers
<https://blog.smarter.sh/2026/03/07/smarter-llm-proxy-api-keys/>`__.

**Exercises.**

- Hold three conversations of different lengths, read their tokens and costs in Smarter's records,
  and rebuild the costs in a spreadsheet from the price list.
- Run the same set of tasks on three models from different providers. Record the cost, the
  latency and a quality score for each, and recommend one.
- Write a business case for an AI application: what it costs per user per month in model charges
  and in infrastructure, and what it saves. The infrastructure figures in :doc:`kubernetes` and
  the compute prices above are a realistic starting point.
- Design a budget policy for a department: who gets how much, what happens at the limit, and who
  is warned before it is reached. Then apply it as Budget manifests, and use one up.

.. note::

   A model without a price in Smarter's ``LLMPrices`` table is recorded with its tokens, at no
   cost, so budgets that measure cost do not see it. Load the prices of the models that the class
   will use before the first lab, as described in :doc:`/smarter-platform/cost-accounting`, or
   use budgets that measure tokens.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <ai-economics/bootcamp>
   Two-week online course: 6 hours <ai-economics/two-week>
   Four-week online course: 12 hours <ai-economics/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
