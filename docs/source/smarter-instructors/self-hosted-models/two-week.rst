Self-Hosting Open Models: Two-Week Online Course
================================================

A two-week online course on serving open models with Smarter's :doc:`LLMHost
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
comparison is fair. There are six 30-minute recorded lectures and a 90-minute live session each
week. Week 1 covers how inference works and serving a model, and week 2 covers performance,
comparison with commercial models, and the economics of self-hosting. See :doc:`../course-formats`
for the format, the grading scale and the course policies, and :doc:`../self-hosted-models` for an
overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Machine learning, MLOps and platform engineers, and developers.
   * - **Deployment**
     - A shared Smarter instance on a managed Kubernetes cluster with GPU node groups, run by the
       instructor, who schedules GPU time. Students also run Ollama or llama.cpp locally.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Around a dollar an hour for each L4 GPU node while it runs. Budget for about 20 GPU-hours for
       a class of twenty, with a ``llmhost-compute`` :doc:`Budget
       </smarter-resources/smarter-budget>` to stop new launches at a limit. It does not remove
       nodes that are already running.

.. warning::

   GPU nodes cost money until the last LLMHost on them is undeployed. Students undeploy at the end
   of every working session, and the instructor checks daily.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain how inference works, and estimate the memory a model needs.
2. Choose a model, quantization and inference engine for a hardware budget.
3. Deploy, monitor and undeploy models with LLMHost manifests.
4. Measure and compare the performance of inference engines.
5. Compare self-hosted and commercial models, and make a reasoned recommendation.

Technical Prerequisites
-----------------------

- **Required:** the Linux command line, Git and YAML.
- **Required:** Docker, and basic Kubernetes concepts.
- **Required:** generative AI basics: tokens, context windows and chat completion APIs.
- **Required:** Python, enough to call an OpenAI-compatible API and time it.
- **Required before Live session 1:** Ollama installed locally, with a small model pulled.
- **Helpful:** machine learning basics, and GPU concepts.

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
     - **Why self-host.** Privacy, cost, control and availability; open weights and licenses.
   * - 1
     - Lecture 2 (30 min)
     - **How inference works.** Prefill and decode, the KV cache, batching, and GPU memory
       arithmetic.
   * - 1
     - Lecture 3 (30 min)
     - **LLMHost.** The manifest, the built-in examples and compute node groups, the lifecycle,
       and calling the endpoint.
   * - 1
     - Live session 1 (90 min)
     - Live deployment of ``qwen3-0.6b``, then local Ollama measurements in pairs. Start
       Assignment 1.
   * - 2
     - Lecture 4 (30 min)
     - **Inference engines and quantization.** vLLM, SGLang, TGI, llama.cpp and Ollama; FP8,
       4-bit, GGUF, AWQ and GPTQ.
   * - 2
     - Lecture 5 (30 min)
     - **Self-hosted beside commercial.** Registering an LLMHost as a
       :doc:`Provider </smarter-resources/smarter-provider>`, and comparing models fairly.
   * - 2
     - Lecture 6 (30 min)
     - **Economics and operations.** Utilization, idle time, cost per thousand requests,
       monitoring and upgrades.
   * - 2
     - Live session 2 (90 min)
     - Capstone presentations (about 5 minutes each, with 2 minutes of questions).

Assignment 1 is due at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
and the capstone at the start of Live session 2.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Local and Hosted Inference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students measure a small model locally with Ollama, then deploy an LLMHost on the class cluster,
record its lifecycle, and measure it the same way.

**Turn in:** the script, the annotated manifest, ``describe`` output at each stage, and a results
table.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Measurements
     - 6
     - Tokens per second, time to first token and memory, repeated.
     - One run.
   * - Manifest annotation
     - 5
     - Every field correct.
     - Errors.
   * - Lifecycle
     - 5
     - Every status, with timings explained.
     - Final status only.
   * - Clean up
     - 4
     - Undeployed, shown.
     - Left running.

Assignment 2: Engine Bake-off
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Teams serve the same model with two engines, and measure throughput and latency at 1, 4 and 16
concurrent requests.

**Turn in:** manifests, the load-testing script, a chart and a one-page analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Fair comparison
     - 5
     - Controlled conditions.
     - Uncontrolled.
   * - Measurement
     - 6
     - Three concurrency levels.
     - One.
   * - Analysis
     - 6
     - Explained by batching and memory.
     - Describes.
   * - Recommendation
     - 3
     - For a stated workload.
     - None.

Assignment 3: Quantization Trade-off
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students compare two precisions of the same model (for example FP16 and a 4-bit GGUF) on fifteen
tasks for quality, and on speed and memory.

**Turn in:** the manifests or local configuration, the tasks and scores, and a one-page analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Quality evaluation
     - 7
     - Stated rubric, consistent scoring.
     - Impressions.
   * - Performance
     - 5
     - Speed and memory measured.
     - Missing.
   * - Analysis
     - 5
     - Where quality loss matters and where it does not.
     - Generic.
   * - Clarity
     - 3
     - Clear.
     - Unclear.

Capstone Projects
-----------------

Students choose one, and present it in Live session 2.

Capstone A: A Self-Hosting Recommendation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Decide, with measurements, whether an organization should self-host a model
for a workload, and at what scale.

Students compare a self-hosted model on LLMHost with a commercial model for a stated workload, on
quality (twenty-five tasks), latency under load, and cost per thousand requests at realistic
utilization.

**What students turn in:**

- Manifests, tasks, scores, measurements and a cost model.
- A three-page recommendation with the break-even volume.
- A five-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Quality comparison
     - 25
     - Representative, rubric-based, blind where possible.
     - Impressions.
   * - Performance
     - 20
     - Under load.
     - Single requests.
   * - Cost model
     - 25
     - Utilization, idle time and people; break-even.
     - Hourly price only.
   * - Non-financial factors
     - 15
     - Weighed.
     - Ignored.
   * - Recommendation and presentation
     - 15
     - Clear, conditional, on time.
     - None.

Capstone B: A Private Assistant on Open Models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build an AI application whose prompts never leave the organization's
infrastructure, and measure what that costs in quality.

Students build an assistant for a privacy-sensitive job on self-hosted chat and embedding models,
with guardrails, and compare it with the same assistant on a commercial model.

**What students turn in:**

- Manifests and a data flow diagram.
- A comparison on twenty questions.
- A two-page trade-off note, and a five-minute presentation.

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
     - Self-hosted models only.
     - Commercial fallback somewhere.
   * - Privacy evidence
     - 25
     - Backed by configuration and logs.
     - Asserted.
   * - Comparison
     - 25
     - Fair and rubric-based.
     - Impressions.
   * - Configuration
     - 15
     - Suited to the hardware.
     - Defaults copied.
   * - Note and presentation
     - 15
     - Honest; clear.
     - One-sided.

Recommended Texts
-----------------

- **Required:** Chip Huyen, *AI Engineering: Building Applications with Foundation Models*
  (O'Reilly, 2025). Week 1: chapter 2 (foundation models). Week 2: chapter 9 (inference
  optimization).
- **Required:** Kwon et al., *Efficient Memory Management for Large Language Model Serving with
  PagedAttention* (2023), in week 2.
- **Reference:** Jay Alammar and Maarten Grootendorst, *Hands-On Large Language Models* (O'Reilly,
  2024), chapters 1 to 3.
- **Smarter documentation:** :doc:`/smarter-resources/smarter-llmhost`,
  :doc:`/smarter-resources/smarter-provider` and :doc:`/smarter-framework/smarter-on-kubernetes`.

Further Study
-------------

.. include:: further-study.txt
