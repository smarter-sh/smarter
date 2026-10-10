# v0.16 Release: Host Your Own Models, Proxy Any Provider, Cap Every Dollar

October 2026 · The Smarter Project

v0.15 was about **describing** an AI application: one YAML manifest that wires a model, plugins, MCP servers and guardrails into an LLMClient. v0.16 is about **running** AI applications. That covers the models, the vector databases, the API keys and the bill.

This release adds four new resource kinds, and like everything else in Smarter, each is a manifest you `apply`:

| Resource                         | What it does                                                                                                                                                                                  |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **LLMHost** + **LLMHostCompute** | Run open-weight models (Llama, Qwen, Mistral, Gemma, DeepSeek, gpt-oss and more) on your own Kubernetes cluster. Smarter adds GPU servers when you need them and removes them when you don't. |
| **Proxy**                        | Give your developers the OpenAI, Anthropic or Gemini SDK they already use, pointed at Smarter. Your provider API keys never leave the platform.                                               |
| **Budget**                       | Set spending limits in dollars or tokens on any resource: a user, an account, a model, a proxy, a GPU server. Smarter enforces them.                                                          |
| **Vectorstore**                  | Self-hosted Qdrant, Qdrant Cloud or Pinecone for retrieval-augmented generation (RAG), managed from creation to deletion.                                                                     |

```bash
smarter apply -f my-resource.yaml
smarter deploy <kind> <name>
```

Each feature is described below.

---

## Run open-weight models on your own cluster: LLMHost

Until now, every model that Smarter used was hosted by a third party and reached through its API. With **LLMHost**, Smarter can serve the model itself, on the same AWS EKS cluster that Smarter runs on.

You write a short manifest that names the model, the inference server and the resources it needs. When you deploy it, Smarter downloads the weights, starts the server, and gives you an **OpenAI-compatible URL**. An LLMClient can then use that URL like any other provider.

```yaml
apiVersion: smarter.sh/v1
kind: LLMHost
metadata:
  name: llama_3_1_8b_instruct
  description: Meta Llama 3.1 8B Instruct, served by vLLM, with tool calling.
  version: 1.0.0
spec:
  model:
    source: huggingface
    repository: meta-llama/Llama-3.1-8B-Instruct
    servedName: llama-3.1-8b-instruct
    tokenSecret: huggingface_token
    capabilities:
      functionCalling: true
  engine:
    name: vllm
    contextLength: 16384
  compute: gpu_a10g_1x
  resources:
    gpuCount: 1
    cpu: "4"
    memory: 24Gi
  network:
    ingress: true
```

- **Six inference servers:** vLLM, SGLang, TGI, llama.cpp, Ollama, and Text Embeddings Inference for embedding models.
- **Two model sources:** Hugging Face, including gated models that use a token stored as a Smarter Secret, and the Ollama library.
- **Status you can follow:** a deployment goes through `provisioning`, `pending`, `downloading`, `deploying` and `active`.
- **24 built-in manifests** for popular models, from Qwen3 0.6B to Llama 3.3 70B and gpt-oss-120b, plus embedding models such as BGE-M3 and nomic-embed-text.

### GPUs only while you use them: LLMHostCompute

GPU servers are expensive, and an idle one costs as much as a busy one. So Smarter doesn't assume your cluster has GPUs, or an autoscaler set up for every GPU type. It manages the servers itself.

An **LLMHostCompute** is one kind of server, for example an AWS `g6.2xlarge` with one NVIDIA L4. Each one is an EKS managed node group:

- When you deploy an LLMHost and no server has room for it, Smarter creates the node group, adds a server, and starts the model once the server joins the cluster.
- When you destroy the last LLMHost on a server, Smarter terminates that server.
- A background job checks every 30 seconds while servers start, and every 5 minutes after that.

Seven LLMHostCompute definitions are built in, from a small CPU-only server to a server with eight NVIDIA H100 GPUs. Each one includes an hourly price, which Budgets use (see below). LLMHostCompute also has its own page in the web console, under **LLM Host Compute**. It shows each server type, its GPUs, CPU and memory, its price, how many servers are ready, and which LLMHosts use them.

> **Before you use this in a real environment:** Smarter needs IAM permissions to manage EKS node groups, and GPU servers need the NVIDIA device plugin. The details are in `smarter/apps/llmhost/data/README.md`.

📖 [LLMHost documentation](https://docs.smarter.sh/en/latest/smarter-resources/smarter-llmhost.html)

---

## Keep your provider keys private, and keep the SDK you know: Proxy

Many teams have code that calls OpenAI or Anthropic directly. Each developer has an API key, nobody can say who spent what, and revoking a key breaks everyone. A **Proxy** fixes this without changing the code.

Developers keep using the provider's own SDK. They change two things: the base URL, which points to Smarter, and the API key, which becomes a Smarter API key.

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://<your-smarter>/api/v1/proxy/openai/",
    api_key="<your Smarter API key>",
)
```

```python
from anthropic import Anthropic

client = Anthropic(
    base_url="https://<your-smarter>/api/v1/proxy/anthropic/",
    api_key="<your Smarter API key>",
)
```

Smarter forwards each request to the provider unchanged, adds the provider's API key from a **Smarter Secret**, and returns the response unchanged, including streams. The provider's key never leaves Smarter, and every token is charged to the user, their account and the Proxy.

- **Built-in Proxies** for OpenAI, Anthropic, Google Gemini (native and OpenAI-compatible), Mistral, Cohere, Fireworks, Together AI and Meta. Each one allows only its provider's inference endpoints.
- **The SDKs work as they are:** Smarter accepts its API key in whichever header the SDK sends: `Authorization: Bearer`, `x-api-key`, `x-goog-api-key` or `api-key`.
- **Errors your SDK understands:** Smarter's own errors use the `{"error": {...}}` shape that the OpenAI and Anthropic SDKs already report. Provider errors, such as a 429, are passed through unchanged.

### Security

- A Proxy can only use Secrets that belong to its own account. Smarter checks this when the manifest is applied and again on every request.
- Base URLs on private, loopback or link-local addresses are refused, so a Proxy can't be used to reach internal services.
- Redirects are not followed, so the key is only sent to the configured host.
- `allowedPaths` limits the endpoints callers can use, and paths that would leave the base URL, for example with `..`, are always refused.

📖 [Proxy documentation](https://docs.smarter.sh/en/latest/smarter-resources/smarter-proxy.html)

---

## Spending limits that Smarter enforces: Budget

Earlier releases had budget models in the database, but nothing enforced them. In v0.16, a **Budget** is a real control. You set limits in USD or tokens, per hour, day, week or month, and in total. Then you attach the Budget to any resource: a User, an Account, an LLMClient, a Provider, a Proxy, an LLMHostCompute, a plugin, an MCPClient, and so on.

```yaml
apiVersion: smarter.sh/v1
kind: Budget
metadata:
  name: student_monthly_allowance
  description: Each student may spend $10 a month on AI, and $100 in total.
  version: 1.0.0
spec:
  config:
    unit: cost
    period: month
    periodicLimit: 10.00
    absoluteLimit: 100.00
    action: block
    warningThreshold: 80
    message: You have used this month's AI allowance. It renews on the 1st of next month.
  resources:
    - kind: User
      name: student1
    - kind: User
      name: student2
```

### How it's enforced

- Smarter checks a Budget each time a charge is created for one of its resources, and again every hour. When a limit is reached, it locks the resource until the period ends.
- `action: warn` sends warnings without blocking anything, for when you want to watch spending first.
- When an LLMClient is over budget, its chat answers with your message and doesn't call the model. An over-budget plugin or MCP server isn't called, and the model is told why.
- The Proxy, prompt passthrough, vectorsearch and orchestrator APIs return **HTTP 402**.
- Self-hosted GPUs count too. LLMHostCompute servers are charged each hour at their price, and an LLMHost won't start while its compute, owner or account is over budget.
- A locked resource can still be viewed and managed. The lock only stops new spending.

### See where the money goes

- A new **Budgets** page in the web console shows each resource's spending, with a chart of its last 12 billing periods.
- A **Budget vs Actual** chart on the dashboard.
- Seven example manifests, including an account monthly cap, a provider daily limit, a project budget, a warn-only proxy, an hourly token limit per user, and a GPU compute budget.

📖 [Budget documentation](https://docs.smarter.sh/en/latest/smarter-resources/smarter-budget.html)

---

## RAG without managing a database: Vectorstore

Until now, Vectorstore was only a scaffold. In v0.16 it is a complete feature. A **Vectorstore** is a vector database for retrieval-augmented generation, and Smarter manages all of it: it creates the database, loads documents, keeps it running, backs it up and deletes it.

```yaml
apiVersion: smarter.sh/v1
kind: Vectorstore
metadata:
  name: example_knowledge_base
  description: A self-hosted Qdrant vector database of product documentation.
  version: 1.0.0
spec:
  backend: qdrant
  hosting: self_hosted
  index:
    dimension: 1536
    metric: cosine
  embeddings:
    provider: openai
    model: text-embedding-3-small
    chunkSize: 1000
    chunkOverlap: 200
  selfHosted:
    storage: 10Gi
  maintenance:
    snapshots: true
    snapshotIntervalHours: 24
    snapshotRetention: 7
```

```bash
smarter apply -f knowledge-base.yaml
smarter deploy vectorstore example_knowledge_base
curl -H "Authorization: Token $SMARTER_API_KEY" -F files=@manual.pdf \
  https://<your-smarter>/api/v1/vectorstores/<id>/documents/
```

- **Three backends:** self-hosted Qdrant, which runs on your cluster as an unprivileged, non-root StatefulSet with its own generated API key; Qdrant Cloud; and Pinecone. Accounts that share a Qdrant Cloud cluster or a Pinecone project never use the same index.
- **Documents:** upload PDF, text, Markdown, CSV, JSON, YAML or HTML, send text directly, or give a public HTTPS URL. Each chunk gets a fixed ID, so you can reload or remove a document cleanly, and a document that is already loaded isn't added twice.
- **Search:** similarity, similarity with a score threshold, and MMR, with metadata filters.
- **Maintenance:** scheduled snapshots (or Pinecone backups) with retention, and restore through the REST API.
- **Safe defaults:** `undeploy` stops serving but keeps the data. `deletionProtection` stops `delete` from destroying it.

📖 [Vectorstore documentation](https://docs.smarter.sh/en/latest/smarter-resources/smarter-vectorstore.html)

---

## Deleting a resource no longer breaks others

Before v0.16, deleting a resource could quietly break the resources that used it. Deleting a Secret deleted every connection that used it, and deleting a Guardrail removed it from every LLMClient without a warning.

Now, Smarter **refuses to delete a resource that other resources depend on**, and tells you which ones they are. Every manifest's status also has a new `dependencies` field, so `smarter describe` shows what uses a resource before you try to delete it. Only dependents you are allowed to see are named; dependents in other accounts are counted but not named.

In the web console, the **Delete** button is disabled for resources you can't delete, and its tooltip tells you why.

---

## Web console improvements

- **Clone, rename and delete now work on every list page.** On 13 list pages (AuthTokens, Connections, Guardrails, LLMHosts, MCPClients, Orchestrators, Plugins, Providers, Proxies, Secrets, Vectorsearches and Vectorstores), these toolbar buttons sent requests to the wrong URL, so they never worked. They do now.
- **Clearer toolbars:** Edit and Rename icons are blue, Clone is green, Delete is red, and Chat and Copy URL are teal. Disabled buttons are gray and still show their tooltips.
- **Small fixes:** dialogs no longer lose what you typed when the page refreshes, refreshing after an action loads fresh data, and error dialogs show the server's message.
- Turning ESLint back on across all React packages found and fixed 200 issues.

---

## Fixes and operations

- **MariaDB now uses `utf8mb4`.** A SkillPlugin with an emoji in its `SKILL.md` failed to apply, because the database had been created with the server's 3-byte `utf8mb3` default. New databases now use `utf8mb4`, and the Helm init job runs `ALTER DATABASE` so that new tables in existing databases use it too.
- **Helm:** a new `databaseInit.enabled` flag controls the database init job. It used to depend on the backup flag, so turning off scheduled backups also skipped migrations and platform setup. The backup CronJob now follows its own flag.
- **Configuration:** when AWS can't be reached, Smarter accepts AWS's default-enabled regions instead of failing.
- **API:** an inactive Smarter API key returns 401, instead of a 500 on every token-authenticated endpoint.
- **Provider base URLs** for Together AI and Meta are corrected.
- **Tests:** four tests that failed only in CI now pass reliably.

---

## Upgrading

- **New infrastructure permissions.** LLMHost needs IAM permissions to create, resize and delete EKS node groups, and GPU servers need the NVIDIA device plugin. If you don't plan to self-host models, you can skip this.
- **Optional settings:** `SMARTER_LLMHOST_NODE_ROLE_ARN` and `SMARTER_LLMHOST_NODE_SUBNET_IDS` set the IAM role and subnets of new node groups. By default, they are copied from the node group that Smarter runs on.
- **Vectorstore credentials:** set `PINECONE_API_KEY`, `QDRANT_CLOUD_URL` and `QDRANT_CLOUD_API_KEY` to use the managed backends.
- **If you ran a pre-release:** the `proxy` and `vectorstore` migrations were replaced by a single `0001_initial`. If you applied the old migrations from a v0.16 alpha, run `manage.py migrate proxy zero` and `manage.py migrate vectorstore zero` before you upgrade.
- **Existing MariaDB tables are not converted to `utf8mb4`.** If one of your columns needs 4-byte characters, such as a SkillPlugin's document, convert it by hand.
- `manage.py initialize_platform` loads the new built-in LLMHosts, LLMHostComputes, Proxies, Budgets and Vectorstores. Nothing is deployed and no server is started until you deploy something.

---

## What's next

v0.15 added Orchestrator, LLMHost and Vectorsearch as early versions. v0.16 completes LLMHost and its storage counterpart, Vectorstore. Next, we will connect these resources: LLMClients that use your self-hosted models, and Vectorsearch that uses your Vectorstores, so that a complete RAG application on models you host is a few manifests.

The full list of changes is in the [v0.16 changelog](https://github.com/smarter-sh/smarter/blob/main/changelogs/CHANGELOG-v0.16.md). To try the release, start with the [documentation](https://docs.smarter.sh), or browse the code on [GitHub](https://github.com/smarter-sh/smarter).
