Self-Hosting Open Models
========================

**Why Smarter.** :doc:`LLMHost </smarter-resources/smarter-llmhost>` serves freely downloadable
models, such as Llama, Qwen, Gemma, Mistral and gpt-oss, on a Kubernetes cluster with vLLM,
SGLang, TGI, llama.cpp or Ollama, and adds and removes the GPU or CPU nodes that they need. An
LLMClient uses a self-hosted model in exactly the same way as a commercial one, so students can
compare them side by side. This suits an MLOps or machine learning systems course.

**Look at.** ``smarter/smarter/apps/llmhost/``.

**Read.** :doc:`/smarter-resources/smarter-llmhost`, :doc:`/smarter-framework/smarter-on-kubernetes`.

**Exercises.**

- Serve a small open model with two different inference servers, and compare their throughput
  and memory use.
- Put a self-hosted model and a commercial model behind the same LLMClient, and compare quality,
  latency and cost per thousand requests, including the cost of the GPU nodes.
- Discuss when an organization should host its own model: privacy, cost at scale, availability,
  and the work of keeping it running.

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
