---
name: smarter-infrastructure-safety
description: Use before writing, testing, or running any Smarter code that touches Kubernetes, AWS (Route53, ACM, EKS node groups), outbound LLM providers, or Celery tasks that do. The local containers hold live production-grade credentials; this skill explains the fakes, guards, patch points and the infrastructure test tag that keep tests from creating real, billable resources.
---

# Smarter Infrastructure Safety

## Why this matters

Inside the local Docker containers:

- The kubeconfig points at the **real EKS cluster**.
- The AWS credentials can create and delete **real Route53 hosted zones and
  records, ACM certificates, and EKS managed node groups**.

An unguarded test once created two real EKS node groups, one of them a GPU
instance. Assume that any code path reaching the infrastructure services
(`smarter.apps.infrastructure.services.infrastructure`: `.dns`, `.certificates`,
`.kubernetes`, `.email`, `.provider`), boto3, or kubectl **will** change real
infrastructure unless you stop it.

The platform reaches its cloud only through `smarter.apps.infrastructure` (see
`docs/source/smarter-framework/technologies/infrastructure.rst`). Its real
services already refuse to reach their backends in the unit tests (the AWS
provider is never ready, kubectl and SMTP are refused), but don't rely on that:
fake them.

## Rules

1. **Fake it before the first run.** Add the fake, guard, or patch before you
   run a new test for the first time, not after something goes wrong.
2. **Patch at the point of use.** Patch the name in the module that calls it,
   for example `smarter.apps.llmclient.tasks.verify_custom_domain.infrastructure`,
   not `smarter.apps.infrastructure.services.infrastructure`.
3. **New AWS-mutating backends get a test guard.** Copy the pattern in
   `EKSNodeGroupBackend._session()`
   (`smarter/smarter/apps/llmhost/services/nodegroups.py`), or
   `refuse_in_unit_tests()` (`smarter.apps.infrastructure.services`): refuse to
   run when `running_unit_tests()` (`smarter.lib.unittest`), and give tests an
   in-memory replacement. A new cloud is a new provider in
   `smarter.apps.infrastructure.providers`, never SDK calls in an app.
4. **Real-infrastructure tests are tagged and skipped by default.** Tag them
   with `@tag(INFRASTRUCTURE)` (`smarter.lib.unittest.runner`). Run them only
   when the user asks for it.
5. **Don't run deploy, verify, or scale commands by hand in the containers**
   (`deploy_*`, `verify_*`, `register_custom_domain`, node group changes)
   unless the user asks you to, for that specific resource.

## The tools that exist

| Concern                                       | Fake / guard                                                                                                           | Where                                                                                                                                       |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Kubernetes cluster (llmhost)                  | `configure_cluster(lambda: InMemoryClusterBackend(...))`, reset with `configure_cluster(None)`                         | `smarter/smarter/apps/llmhost/services/cluster.py`                                                                                          |
| EKS node groups                               | `configure_nodegroups(lambda: InMemoryNodeGroupBackend(...))`. The real backend raises in tests                        | `smarter/smarter/apps/llmhost/services/nodegroups.py`                                                                                       |
| DNS records for llmhost                       | `patch("smarter.apps.llmhost.tasks.dns_enabled", return_value=False)`                                                  | see `smarter/smarter/apps/llmhost/tests/base_classes.py`                                                                                    |
| DNS, certificates (llmclient, custom domains) | `patch(f"{MODULE}.infrastructure", MagicMock())`, plus `patch(f"{MODULE}.is_taskable", return_value=True)`             | see `smarter/smarter/apps/llmclient/tests/tasks/test_task_verify_custom_domain.py`                                                          |
| A whole cloud, really exercised in memory     | `configure_provider(lambda: InMemoryProvider())`, reset with `configure_provider(None)`                                | `smarter/smarter/apps/infrastructure/providers/memory.py`; see `smarter/smarter/apps/api/management/tests/test_verify_dns_configuration.py` |
| kubectl (the Kubernetes service)              | `configure_kubernetes(lambda: fake)`, or `KubectlKubernetesService(allow_in_tests=True)` with `subprocess.run` patched | `smarter/smarter/apps/infrastructure/services/kubernetes.py`; see `smarter/smarter/apps/infrastructure/tests/test_kubernetes.py`            |
| Email                                         | `configure_email(InMemoryEmailService)`, or `patch(f"{MODULE}.infrastructure")`                                        | `smarter/smarter/apps/infrastructure/services/email.py`                                                                                     |
| Outbound proxy calls to LLM providers         | `configure_transport(...)`. Real calls raise `ProxyConfigurationError` in tests                                        | `smarter/smarter/apps/proxy/services.py`                                                                                                    |
| GitHub-hosted skills                          | `with mock_remote_skills(): ...`                                                                                       | `smarter/smarter/apps/plugin/plugin/tests/base_classes.py`                                                                                  |

The llmhost test base class (`smarter/smarter/apps/llmhost/tests/base_classes.py`)
is the model for a whole suite that runs against in-memory infrastructure:
install the fakes in `setUpClass`, and reset them in `tearDownClass`.

## Celery tasks

- Celery is **not** eager in tests. `.delay()` and `.apply_async()` send the task
  to the real worker containers, which have the same live credentials.
- Test a task by calling the task function directly, with its infrastructure
  patched. It runs synchronously, and exceptions propagate.
- Patch `.delay` or `.apply_async` on tasks that the code under test queues, and
  on the task itself when it re-queues (retries), so nothing reaches a worker.
- A task that calls Kubernetes or AWS is declared with
  `queue=smarter_settings.infrastructure_tasks_celery_task_queue`. That queue is
  served by `smarter-worker-infrastructure`, so slow infrastructure calls never
  block the operational queues, such as
  `smarter_settings.llmclient_tasks_celery_task_queue`. Copy the decorator of an
  existing task (`smarter/smarter/apps/llmclient/tasks/deploy_custom_api.py`):
  `autoretry_for`, `retry_backoff`, `max_retries`, and `queue`.
- `is_taskable()` (`smarter/smarter/apps/llmclient/tasks/utils.py`) checks that
  the cloud provider's DNS and certificate services are ready. Patch it to
  `True` together with a mocked `infrastructure`. Never satisfy it with real
  credentials.

## Domain knowledge that affects what you fake

- **Custom domain verification is ACM plus Route53, and nothing else.** A custom
  domain is verified when its Route53 hosted zone's NS records are delegated,
  and its ACM certificate (in us-east-1) is issued. Kubernetes ingresses play no
  part.
- **An LLMClient's HTTPS is its own business.** Each LLMClient serves a
  subdomain with its own Kubernetes-managed TLS certificate. Don't couple custom
  domain verification to LLMClient ingress or certificate state.
- Built-in example data (for example the `example.com` custom domain) is
  expected to fail verification locally. That's correct behavior, not a bug to
  fix by mocking production code.
