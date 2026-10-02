Smarter LLM Host
=====================

Overview
--------

The Smarter LLMHost app provides a standardized interface for deploying and
managing self-hosted large language models within Smarter-orchestrated applications.
Rather than routing every inference request through a third-party model provider,
LLMHost lets an organization register its own model deployments — whether
served from a Hugging Face checkpoint via vLLM, a quantized GGUF model through
Ollama, or a custom inference stack — as first-class, managed resources.
This allows prompts and engineering loops to target self-hosted models with
the same consistency as any hosted provider, while Smarter remains responsible
for endpoint configuration, credential resolution, health monitoring, and
cost tracking. By separating model deployment from application logic, LLMHost
enables new models to be brought online, swapped, or retired without modifying
the surrounding AI application.

LLMHost operates as a managed registry and health-tracking layer between Smarter
and the underlying inference infrastructure. During initialization it captures
a deployment's provenance (its source repository and revision), its capabilities
(context window, quantization, supported modalities), and its serving
configuration (inference engine, API format, endpoint), then makes that deployment
available for controlled invocation by prompts, agents, and workflows. Each
configured host is continuously monitored through Smarter's health-check
infrastructure, and its authentication credentials are resolved through Smarter's
Secret store rather than persisted as plaintext, ensuring that self-hosted
capabilities remain subject to the same governance and operational controls as
any other Smarter resource. This architecture allows organizations to run open,
freely downloadable models alongside commercial providers while maintaining centralized
configuration, observability, and cost visibility across all AI-assisted interactions.

The Smarter LLMHost app is included in v0.15.0 and later. It enables Account administrators
to register and manage self-hosted model deployments through the Smarter administration
interface, eliminating the need to hard-code inference endpoints or distribute
deployment details across individual applications.

.. seealso::

    - :doc:`Smarter Installation Guide <../smarter-platform/installation>`
    - :doc:`OpenAI Getting Started Guide <../smarter-framework/guides/openai-api-getting-started-guide>`

Example: Self-Hosting a Hugging Face Model
------------------------------------------

This example self-hosts `Qwen/Qwen3-0.6B <https://huggingface.co/Qwen/Qwen3-0.6B>`__, the most
downloaded text-generation model on Hugging Face at the time of writing. It is small enough to run
on a single NVIDIA L4 GPU, and it is one of the built-in examples in
``smarter/apps/llmhost/data/llmhost/``:

.. literalinclude:: ../../../smarter/smarter/apps/llmhost/data/llmhost/qwen3-0.6b.yaml
   :language: yaml
   :caption: qwen3-0.6b.yaml

The manifest describes four things:

- ``spec.model``: where the weights come from. ``source: huggingface`` and ``repository`` name the
  Hugging Face repository, and ``revision`` the branch, tag or commit to download. Pin a commit SHA
  for a reproducible deployment. ``servedName`` is the model name that clients send in their
  requests.
- ``spec.engine``: the inference server that loads the weights, here
  `vLLM <https://github.com/vllm-project/vllm>`__, with its own command-line ``args``. Here they
  enable Qwen3's reasoning parser.
- ``spec.compute``: the kind of node to run on, here ``gpu_l4_1x``, one of the built-in
  LLMHostCompute node groups in ``smarter/apps/llmhost/data/compute/``. Smarter adds a node to its
  node group when the LLMHost is launched, and removes it when no LLMHost needs it any more.
- ``spec.resources``: what one replica's pod requests of that node: GPUs, VRAM, CPU and memory.

**1. Apply the manifest, and launch it.** ``manage.py initialize_platform`` already applies the
built-in LLMHosts for the Smarter admin. To run your own copy, give it a ``metadata.name`` of your
own, then:

.. code-block:: console

   smarter apply -f qwen3-0.6b.yaml
   smarter deploy llmhost qwen3_0_6b

``deploy`` returns as soon as Kubernetes accepts the resources. A new GPU node takes a few minutes
to start, and downloading and loading the weights takes a few more.

**2. Follow its status.**

.. code-block:: console

   smarter describe llmhost qwen3_0_6b

``status.hostStatus`` goes from ``provisioning`` (waiting for its node), to ``pending``,
``downloading`` and ``deploying``, to ``active``. ``status.endpoint`` is the model's
OpenAI-compatible URL inside the cluster, and ``status.apiKeySecret`` names the
:doc:`Secret <smarter-secret>` that holds its API key. Smarter generates the key when the
LLMHost is launched, unless ``spec.network.apiKeySecret`` names one of your own.

**3. Call it.** The model speaks the OpenAI API, so any OpenAI client can use it, with the
endpoint as its base URL, the API key, and the ``servedName`` as the model:

.. code-block:: python

   from openai import OpenAI

   client = OpenAI(base_url=ENDPOINT, api_key=LLMHOST_API_KEY)
   response = client.chat.completions.create(
       model="qwen3-0.6b",
       messages=[{"role": "user", "content": "Hello!"}],
   )

The endpoint is reachable only inside the cluster. To reach the model from outside it, add
``spec.network.ingress: true``, and Smarter creates an Ingress at ``https://<hostname>``, with a TLS
certificate. To use the model in your AI applications, register its endpoint and API key Secret as a
:doc:`Provider <smarter-provider>`, which LLMClients can then use.

**4. Stop it.**

.. code-block:: console

   smarter undeploy llmhost qwen3_0_6b

This removes its Kubernetes resources. The downloaded weights are kept on their volume, so the next
launch is faster, unless ``spec.storage.retain`` is ``false``. The node is removed once no LLMHost
needs it.

Gated models, such as Llama, Gemma and Mistral, also need a Hugging Face access token, in a Smarter
Secret named in ``spec.model.tokenSecret``, and their license accepted on huggingface.co. The other
examples in ``smarter/apps/llmhost/data/llmhost/`` cover larger models, every inference engine,
GGUF models on CPU, and embedding models, such as
`sentence-transformers/all-MiniLM-L6-v2 <https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2>`__,
the most downloaded model of all on Hugging Face.

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   llmhost/api
   llmhost/const
   llmhost/management
   llmhost/manifest
   llmhost/models
   llmhost/serializers
   llmhost/signals
   llmhost/tasks
   llmhost/views
