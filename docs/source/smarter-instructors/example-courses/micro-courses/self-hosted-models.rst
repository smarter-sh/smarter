Self-Hosting Open Models
========================

**Why Smarter.** Courses on serving open models usually stop at running one model in a notebook,
or on a single GPU server, and never reach the questions an organization actually faces: which
engine, which GPU, what it costs per thousand requests, and whether it is as good as a commercial
model. :doc:`LLMHost </smarter-resources/smarter-llmhost>` answers them on a real platform. It
serves freely downloadable models on a Kubernetes cluster, adds and removes the GPU or CPU nodes
that they need, and puts them in the same applications as commercial ones:

- **Models ready to serve.** Twenty-four built-in
  `LLMHost manifests <https://github.com/smarter-sh/example-manifests/tree/main/llmhosts>`__
  for Llama, Qwen, Gemma, Mistral, Phi, DeepSeek and gpt-oss models, GGUF models for CPU, and
  embedding models, each with its engine, resources, pinned revision and license, and
  `model discovery <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmhost/services/discovery.py>`__
  that drafts a manifest for any model on the Hugging Face Hub.
- **Seven inference engines.** vLLM, SGLang, Hugging Face TGI and TEI, llama.cpp, Ollama and a
  custom engine, each turned into the right command and arguments by
  `engines.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmhost/services/engines.py>`__,
  so a class can serve the same model two ways and compare them.
- **GPUs on demand.** Seven `compute profiles
  <https://github.com/smarter-sh/example-manifests/tree/main/llmhost-computes>`__,
  from small CPU nodes to eight H100s, become EKS `node groups
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmhost/services/nodegroups.py>`__
  that start at zero nodes, grow when a model needs a node, and shrink by removing an idle one.
- **Kubernetes underneath, visible.** A model volume, a Secret, a Deployment, a Service and an
  optional Ingress, rendered by a `pure function
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmhost/services/renderer.py>`__,
  and a lifecycle that students can watch, from ``provisioning`` and ``downloading`` to
  ``active``.
- **A fair comparison.** A self-hosted endpoint is registered as a
  :doc:`Provider </smarter-resources/smarter-provider>`, so an LLMClient uses it in exactly the
  same way as a commercial model, and its GPU hours are
  :doc:`charged </smarter-platform/cost-accounting>` at the compute profile's price, so quality,
  latency and cost per thousand requests are measured on the same records.

This suits an MLOps or machine learning systems course, and any course that has to decide when an
organization should host its own models.

**What the course covers.** Why self-host: privacy, data residency, cost, control and availability;
the open model landscape, model cards, and open weights versus open source; how inference works:
prefill and decode, the KV cache, batching and GPU memory arithmetic; serving models with LLMHost
and its manifest; compute, node groups and CPU inference with GGUF; endpoints, API keys, ingress
and gated models; inference engines; quantization and its cost in quality; benchmarking
throughput, latency and time to first token; applications on open models, including embedding
models for retrieval; operations, with health checks, monitoring and pinned revisions; and the
economics of utilization, idle time and break-even with commercial providers.

**Look at.**

- `example-manifests/llmhosts/ <https://github.com/smarter-sh/example-manifests/tree/main/llmhosts>`__
  and `example-manifests/llmhost-computes/ <https://github.com/smarter-sh/example-manifests/tree/main/llmhost-computes>`__,
  the example models and compute profiles.
- `llmhost/services/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/llmhost/services>`__,
  the engines, renderer, node groups, discovery and observability.
- `llmhost/manifest/models/llmhost/spec.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmhost/manifest/models/llmhost/spec.py>`__,
  every setting of an LLMHost, with its description.

Each course plan lists every manifest and file that it uses under *Smarter in the Source Code*.

**Read.** :doc:`/smarter-resources/smarter-llmhost`,
:doc:`/smarter-framework/smarter-on-kubernetes`, :doc:`/smarter-resources/smarter-provider`,
:doc:`/smarter-platform/cost-accounting`.

**Exercises.**

- Serve a small open model with two different inference engines, and compare their throughput
  and memory use.
- Put a self-hosted model and a commercial model behind the same LLMClient, and compare quality,
  latency and cost per thousand requests, including the cost of the GPU nodes.
- Follow an LLMHost from ``provisioning`` to ``active``, and explain what Smarter and Kubernetes
  are doing at each step.
- Discuss when an organization should host its own model: privacy, cost at scale, availability,
  and the work of keeping it running.

.. warning::

   GPU nodes keep costing money until the last LLMHost on them is undeployed. A compute
   :doc:`Budget </smarter-resources/smarter-budget>` stops new launches at its limit, but does not
   remove nodes that are already running.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <self-hosted-models/bootcamp>
   Two-week online course: 6 hours <self-hosted-models/two-week>
   Four-week online course: 12 hours <self-hosted-models/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
