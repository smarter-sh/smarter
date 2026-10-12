Self-Hosting Open Models: Classroom Bootcamp
============================================

An eight-hour classroom bootcamp on serving open models, such as Llama, Qwen, Gemma, Mistral and
gpt-oss, with Smarter's :doc:`LLMHost </smarter-resources/smarter-llmhost>`, which runs them on
Kubernetes with vLLM, SGLang, TGI, llama.cpp or Ollama and adds the GPU or CPU nodes they need.
Students serve models, compare inference engines, and put a self-hosted model beside a commercial
one in the same application. See :doc:`../course-formats` for the standard bootcamp day, the
grading scale and the course policies, and :doc:`../self-hosted-models` for an overview of the
subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Machine learning, MLOps and platform engineers, and developers who need to decide whether to
       host their own models.
   * - **Deployment**
     - A shared Smarter instance on a managed Kubernetes cluster run by the instructor, able to add
       GPU nodes (for example, NVIDIA L4). Each student also runs Ollama or llama.cpp on their
       laptop for the local labs.
   * - **Cost**
     - The GPU nodes dominate: around a dollar an hour for each L4 node while it runs. Plan for two
       or three nodes for about four hours, and undeploy every LLMHost at the end of the day. Cap
       spending with an LLMHost compute :doc:`Budget </smarter-resources/smarter-budget>` (the
       built-in ``llmhost-compute`` example).

.. warning::

   GPU nodes keep costing money until the last LLMHost on them is undeployed. Check
   ``smarter get llmhosts`` and the cluster's nodes before you leave the room.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Explain what it takes to serve a model: weights, an inference engine, GPU or CPU memory, and an
   OpenAI-compatible endpoint.
2. Choose a model, a quantization and an inference engine for a given hardware budget.
3. Deploy, monitor and undeploy a self-hosted model with an LLMHost manifest.
4. Measure throughput, latency and memory use, and compare inference engines.
5. Compare a self-hosted model with a commercial one on quality, latency and cost, and argue when
   self-hosting is worth it.

Technical Prerequisites
-----------------------

- **Required:** the Linux command line, Git, and YAML.
- **Required:** Docker, and basic Kubernetes concepts (pods, nodes, services). The
  :doc:`Kubernetes course <../kubernetes>` covers them.
- **Required:** generative AI basics: tokens, context windows, and chat completion APIs.
- **Required:** Python: running a script that calls an OpenAI-compatible API with the ``openai``
  package.
- **Required:** `Ollama <https://ollama.com/>`__ installed on the student's laptop, with a small
  model (for example ``llama3.2:3b``) pulled before the bootcamp.
- **Helpful:** basic machine learning (what parameters and inference are), and GPU concepts (VRAM,
  CUDA).

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
     - **Lecture 1: Why self-host.** Privacy, data residency, cost at scale, control and
       availability, against the work of running it. The open model landscape, licenses (open
       weights versus open source), and Hugging Face.
   * - 2
     - 45
     - **Lab 1: A model on your laptop.** Run a small model with Ollama, call it through its
       OpenAI-compatible API from Python, and measure tokens per second and memory use. Produces
       Assignment 1.
   * - 3
     - 45
     - **Lecture 2: Serving models.** How inference works (prefill and decode, the KV cache,
       batching), and the inference engines: vLLM and PagedAttention, SGLang, TGI, llama.cpp and
       Ollama. GPU memory arithmetic: parameters, precision and context.
   * - 4
     - 45
     - **Lab 2: Deploy an LLMHost.** Read the built-in ``qwen3-0.6b.yaml`` manifest, apply a copy,
       ``smarter deploy llmhost``, and follow ``status.hostStatus`` from ``provisioning`` to
       ``active``. Call the endpoint. Produces Assignment 2.
   * - 5
     - 45
     - **Lecture 3: Quantization and model choice.** FP16, FP8, INT8 and 4-bit formats, GGUF, AWQ
       and GPTQ; what quality you lose; CPU inference. Choosing a model size for a GPU.
   * - 6
     - 45
     - **Lecture 4: Inside LLMHost.** The manifest's ``model``, ``engine``, ``compute`` and
       ``resources`` sections, the built-in LLMHostCompute node groups, how Smarter adds and removes
       nodes, health checks, API keys as :doc:`Secrets </smarter-resources/smarter-secret>`, and
       registering the endpoint as a :doc:`Provider </smarter-resources/smarter-provider>`.
   * - 7
     - 45
     - **Lab 3: Engine bake-off.** In teams, serve the same small model with two inference engines
       (for example vLLM and SGLang, or llama.cpp on CPU and vLLM on GPU), and measure throughput at
       1, 4 and 16 concurrent requests. Produces Assignment 3.
   * - 8
     - 45
     - **Lecture 5: Self-hosted beside commercial.** Registering an LLMHost as a Provider, pointing
       an LLMClient at it, and comparing it with a commercial model in the workbench. Evaluating
       quality fairly.
   * - 9
     - 45
     - **Lab 4: Side by side.** Point two copies of the same LLMClient at a self-hosted model and a
       commercial one, and run the same prompts through both. Ungraded.
   * - 10
     - 45
     - **Lecture 6: The economics and operations of self-hosting.** Cost per thousand requests
       with GPU utilization, idle time and autoscaling, monitoring, upgrades, and when to stop.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone. The instructor undeploys every LLMHost.

Graded Assignments
------------------

Assignment 1: Local Inference Measurements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students run two model sizes (or two quantizations of one model) locally, call them from Python,
and measure tokens per second, time to first token and memory use.

**Turn in:** the script, a results table and a half-page explanation.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Script
     - 5
     - Calls the OpenAI-compatible API and times the response correctly.
     - Times the whole program, or uses the chat interface by hand.
   * - Measurements
     - 7
     - Three metrics, repeated runs, hardware stated.
     - One run, missing metrics.
   * - Explanation
     - 6
     - Relates results to model size, quantization and hardware.
     - Reports numbers only.
   * - Clarity
     - 2
     - Clear.
     - Unclear.

Assignment 2: An LLMHost from Manifest to Endpoint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students explain each section of their LLMHost manifest, deploy it, record the status transitions
and timings, and call the endpoint.

**Turn in:** the annotated manifest, the ``describe`` output at each stage, and a successful call.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Annotation
     - 6
     - Every field explained correctly.
     - Errors.
   * - Lifecycle
     - 6
     - Each status recorded, with time spent in it explained (node, download, load).
     - Final status only.
   * - Endpoint call
     - 4
     - Successful call with the API key from the Secret.
     - Not called.
   * - Clean up
     - 4
     - Undeployed afterwards, shown.
     - Left running.

Assignment 3: Engine Bake-off
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Teams compare two inference engines on the same model at several concurrency levels.

**Turn in:** the manifests, a load-testing script, a chart of throughput and latency, and a
one-page analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Fair comparison
     - 5
     - Same model, precision, hardware and prompts.
     - Uncontrolled differences.
   * - Measurement
     - 6
     - Throughput and latency at three concurrency levels.
     - One level.
   * - Analysis
     - 6
     - Explains the results with batching and memory.
     - Describes only.
   * - Recommendation
     - 3
     - Picks an engine for a stated workload.
     - None.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp. The instructor schedules GPU
time on the shared cluster, so that nodes are not left running.

Capstone A: A Self-Hosting Recommendation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Decide, with measurements, whether a given organization should self-host a
model for a given workload, and at what scale.

Students pick a workload (for example, summarizing support tickets for 500 agents) and compare a
self-hosted open model on LLMHost with a commercial model: quality on twenty representative tasks,
latency, and cost per thousand requests, including GPU time at realistic utilization.

**What students turn in:**

- The LLMHost, Provider and LLMClient manifests.
- The task set, the scores, latency measurements and a cost model.
- A three-page recommendation with the break-even volume.

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
     - Representative tasks, stated rubric, blind scoring where possible.
     - Impressions.
   * - Performance
     - 20
     - Latency and throughput measured under load.
     - Single requests only.
   * - Cost model
     - 25
     - Includes utilization, idle time and people; break-even computed.
     - GPU hourly price only.
   * - Non-financial factors
     - 15
     - Privacy, control, availability and maintenance weighed.
     - Ignored.
   * - Recommendation
     - 15
     - Clear and conditional.
     - None.

Capstone B: A Private Assistant on an Open Model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build an AI application whose prompts never leave the organization's
infrastructure, and show what that costs in quality and effort.

Students build an assistant for a privacy-sensitive job (for example, a clinic's internal policy
assistant with fictional documents) on a self-hosted chat model and a self-hosted embedding model,
with guardrails, and compare its answers with the same assistant on a commercial model.

**What students turn in:**

- The LLMHost, Provider, LLMClient and guardrail manifests.
- A data flow diagram showing that no prompt or document leaves the cluster.
- A comparison on twenty questions, and a two-page note on the trade-offs.

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
     - Answers questions from the documents using only self-hosted models.
     - Falls back to a commercial model somewhere.
   * - Privacy evidence
     - 25
     - Data flow diagram backed by configuration and logs.
     - Asserted.
   * - Comparison
     - 25
     - Fair, with a stated rubric.
     - Impressions.
   * - Configuration quality
     - 15
     - Model sizes and engines suit the hardware; resources set.
     - Defaults copied.
   * - Trade-off note
     - 15
     - Honest about quality, cost and effort.
     - One-sided.

Recommended Texts
-----------------

- **Pre-reading:** the :doc:`LLMHost page </smarter-resources/smarter-llmhost>`, and the
  `vLLM quickstart <https://docs.vllm.ai/en/latest/getting_started/quickstart.html>`__.
- **Reference:** Chip Huyen, *AI Engineering: Building Applications with Foundation Models*
  (O'Reilly, 2025), chapter 9, on inference optimization.
- **Smarter documentation:** :doc:`/smarter-resources/smarter-llmhost`,
  :doc:`/smarter-resources/smarter-provider` and :doc:`/smarter-framework/smarter-on-kubernetes`.

Further Study
-------------

.. include:: further-study.txt
