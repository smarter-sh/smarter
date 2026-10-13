Self-Hosting Open Models: Four-Week Online Course
=================================================

A four-week online course on serving open models with Smarter's :doc:`LLMHost
</smarter-resources/smarter-llmhost>`, which runs them on Kubernetes and adds the GPU or CPU nodes
they need. Smarter ships with `twenty-four ready-to-apply model manifests
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/llmhost/data/llmhost>`__ and
`seven compute profiles
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/llmhost/data/compute>`__
priced per hour, supports seven `inference engines
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmhost/services/engines.py>`__,
renders each model's Kubernetes resources with a `pure function
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmhost/services/renderer.py>`__
that can be previewed, and creates and removes EKS `node groups
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmhost/services/nodegroups.py>`__
of GPU nodes as models need them. A self-hosted model is registered as a Provider and used by an
LLMClient exactly like a commercial one, and its hours are charged like any other cost, so the
comparison is fair. There are twelve 30-minute recorded lectures and a 90-minute live session each
week. Week 1 covers open models and how inference works, week 2 serving models with LLMHost, week 3
performance and quantization, and week 4 applications, operations and economics. See
:doc:`../course-formats` for the format, the grading scale and the course policies, and
:doc:`../self-hosted-models` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Machine learning, MLOps and platform engineers, and developers.
   * - **Deployment**
     - A shared Smarter instance on a managed Kubernetes cluster with GPU and CPU node groups, run
       by the instructor, who schedules GPU time. Students also run Ollama or llama.cpp locally.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Around a dollar an hour for each L4 GPU node while it runs. Budget for about 40 GPU-hours for
       a class of twenty, with a ``llmhost-compute`` :doc:`Budget
       </smarter-resources/smarter-budget>` to stop new launches at a limit. It does not remove
       nodes that are already running.

.. warning::

   GPU nodes cost money until the last LLMHost on them is undeployed. Students undeploy at the end
   of every working session, and the instructor checks daily.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain the open model landscape, licenses, and how transformer inference works.
2. Estimate the memory and hardware a model needs, and choose a model and quantization.
3. Deploy, monitor and undeploy models with LLMHost, including gated and embedding models.
4. Benchmark inference engines, and tune them for a workload.
5. Build applications on self-hosted models, beside commercial ones.
6. Model the cost of self-hosting, and operate self-hosted models responsibly.

Technical Prerequisites
-----------------------

- **Required:** the Linux command line, Git and YAML.
- **Required:** Docker, and basic Kubernetes concepts.
- **Required:** generative AI basics: tokens, context windows and chat completion APIs.
- **Required:** Python, enough to call an OpenAI-compatible API and write a small load test.
- **Required by the end of week 1:** Ollama or llama.cpp installed locally.
- **Required by week 2:** a Hugging Face account, with the licenses of the gated models used in
  class accepted.
- **Helpful:** machine learning basics, linear algebra, and GPU concepts.

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
     - **Why self-host.** Privacy, data residency, cost, control and availability.
   * - 1
     - Lecture 2
     - **The open model landscape.** Model families, sizes, licenses (open weights versus open
       source), and reading a model card.
   * - 1
     - Lecture 3
     - **How inference works.** Transformers at a high level, prefill and decode, the KV cache,
       and memory arithmetic.
   * - 1
     - Live session 1
     - Local inference with Ollama, measured live. Start Assignment 1.
   * - 2
     - Lecture 4
     - **LLMHost.** The manifest (``model``, ``engine``, ``compute``, ``resources``, ``network``,
       ``storage``, ``scaling`` and ``healthCheck``), the built-in examples, and finding new models
       in the Hugging Face Hub with Smarter's model discovery.
   * - 2
     - Lecture 5
     - **Compute.** LLMHostCompute node groups, how Smarter adds and removes nodes, GPUs, and
       CPU inference with GGUF models.
   * - 2
     - Lecture 6
     - **Endpoints and access.** OpenAI-compatible endpoints, API keys in
       :doc:`Secrets </smarter-resources/smarter-secret>`, ingress, gated models and access tokens.
   * - 2
     - Live session 2
     - Review of Assignment 1. Live deployment and lifecycle of an LLMHost. Start Assignment 2.
   * - 3
     - Lecture 7
     - **Inference engines.** vLLM and PagedAttention, SGLang, TGI, llama.cpp and Ollama.
   * - 3
     - Lecture 8
     - **Quantization.** FP8, INT8, 4-bit, GGUF, AWQ and GPTQ, and measuring quality loss.
   * - 3
     - Lecture 9
     - **Benchmarking.** Throughput, latency, time to first token, concurrency and load testing.
   * - 3
     - Live session 3
     - Review of Assignment 2. Engine comparison, live. Capstone proposals discussed. Start
       Assignment 3.
   * - 4
     - Lecture 10
     - **Applications on open models.** Registering a
       :doc:`Provider </smarter-resources/smarter-provider>`, LLMClients, embedding models for
       retrieval, and evaluation.
   * - 4
     - Lecture 11
     - **Operations.** Health checks, monitoring, upgrades, model versioning with pinned
       revisions, and incident response.
   * - 4
     - Lecture 12
     - **Economics.** Utilization, idle time, autoscaling to zero, cost per thousand requests, and
       the break-even with commercial providers.
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

Assignment 1: Model Selection and Memory Estimates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students choose three open models for a stated job, read their model cards and licenses, estimate
the GPU memory each needs at two precisions and a stated context length, and check one estimate by
running the model locally.

**Turn in:** a table of models, licenses, estimates and the measurement, and a one-page
recommendation.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Model choice
     - 4
     - Suited to the job, with reasons.
     - Arbitrary.
   * - Licenses
     - 4
     - Restrictions correctly summarized.
     - Not read.
   * - Memory estimates
     - 7
     - Weights and KV cache estimated correctly; one checked.
     - Weights only.
   * - Recommendation
     - 5
     - Clear and reasoned.
     - None.

Assignment 2: LLMHost Lifecycle and a CPU Model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students deploy a GPU LLMHost and a CPU (GGUF) LLMHost from the built-in examples, record both
lifecycles, call both endpoints, and compare them.

**Turn in:** annotated manifests, ``describe`` output, measurements and a half-page comparison.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Annotation
     - 5
     - Every field correct.
     - Errors.
   * - Lifecycles
     - 5
     - Every status, with timings explained.
     - Final status only.
   * - Comparison
     - 6
     - Speed, memory and cost compared.
     - Partial.
   * - Clean up
     - 4
     - Both undeployed, shown.
     - Left running.

Assignment 3: Engine Bake-off
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Teams benchmark one model on two engines at four concurrency levels, and tune one engine argument
(for example the maximum batch size or context length) to improve throughput.

**Turn in:** manifests, the load test, a chart, and a one-page analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Fair comparison
     - 5
     - Controlled.
     - Uncontrolled.
   * - Measurement
     - 5
     - Four levels, repeated.
     - One level.
   * - Tuning
     - 5
     - Measured effect, explained.
     - Unmeasured.
   * - Analysis
     - 5
     - Explained by batching and memory.
     - Describes.

Assignment 4: Quantization and Quality
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students compare three precisions of one model on twenty tasks, scored by a rubric and checked by
a second person or a validated judge, and on speed and memory.

**Turn in:** the tasks, scores, measurements and a one-page analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Evaluation
     - 7
     - Rubric, double-checked scores.
     - Impressions.
   * - Performance
     - 5
     - Speed and memory for each precision.
     - Missing.
   * - Analysis
     - 5
     - Which tasks degrade, and why.
     - Generic.
   * - Recommendation
     - 3
     - A precision for a stated use.
     - None.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and present it in Live session 4.

Capstone A: A Self-Hosting Business Case with Benchmarks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Produce an evidence-based recommendation on self-hosting for an
organization, from benchmarks to a three-year cost model.

Students choose a workload and an organization, select and tune a self-hosted model on LLMHost,
compare it with two commercial models on quality (thirty tasks), latency under load and cost, and
build a three-year cost model with utilization scenarios.

**What students turn in:**

- Manifests, tasks, scores, benchmarks and the cost model.
- A four-page recommendation with the break-even volume and an operations plan.
- A six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Quality comparison
     - 20
     - Rubric-based, validated scoring.
     - Impressions.
   * - Benchmarks
     - 20
     - Under load, after tuning.
     - Untuned single requests.
   * - Cost model
     - 25
     - Scenarios, utilization, people; break-even.
     - Hourly price only.
   * - Operations plan
     - 15
     - Monitoring, upgrades and incidents covered.
     - Missing.
   * - Recommendation and presentation
     - 20
     - Clear, conditional, on time.
     - None.

Capstone B: A Fully Self-Hosted AI Application
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build and operate an AI application that runs entirely on self-hosted
models, with retrieval and guardrails, and document how to run it.

Students build an assistant with retrieval over fictional private documents, using a self-hosted
chat model, a self-hosted embedding model, and guardrails that use a self-hosted judge model, then
compare it with a commercial equivalent and write a runbook.

**What students turn in:**

- Manifests and a data flow diagram showing that nothing leaves the cluster.
- A comparison on twenty-five questions.
- A runbook: deploy, scale, upgrade the model, monitor, and recover.
- A six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Works
     - 20
     - Self-hosted end to end.
     - Commercial fallback.
   * - Privacy evidence
     - 20
     - Configuration and logs.
     - Asserted.
   * - Comparison
     - 20
     - Fair and rubric-based.
     - Impressions.
   * - Runbook
     - 25
     - Tested by another student.
     - Untested.
   * - Presentation
     - 15
     - Clear and on time.
     - Overruns.

Recommended Texts
-----------------

- **Required:** Chip Huyen, *AI Engineering: Building Applications with Foundation Models*
  (O'Reilly, 2025), chapters 2 and 9, in weeks 1 and 3.
- **Required:** Jay Alammar and Maarten Grootendorst, *Hands-On Large Language Models* (O'Reilly,
  2024), chapters 1 to 3, in week 1.
- **Required:** Christopher Brousseau and Matthew Sharp, *LLMs in Production* (Manning, 2025), the
  chapters on serving and deployment, in weeks 2 and 4.
- **Required:** Kwon et al., *Efficient Memory Management for Large Language Model Serving with
  PagedAttention* (2023), in week 3.
- **Smarter documentation:** :doc:`/smarter-resources/smarter-llmhost`,
  :doc:`/smarter-resources/smarter-provider`, :doc:`/smarter-resources/smarter-budget` and
  :doc:`/smarter-framework/smarter-on-kubernetes`.

Further Study
-------------

.. include:: further-study.txt
