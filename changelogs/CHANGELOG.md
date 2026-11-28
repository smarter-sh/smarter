# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).



## [1.0.2](https://github.com/smarter-sh/smarter/compare/v1.0.1...v1.0.2) (2026-11-28)

### Bug Fixes

* **helm:** give the restricted workers only the settings they read ([082ca37](https://github.com/smarter-sh/smarter/commit/082ca3747d024038b447552aaaf1b482c4b4b3ce))
* **llmtool:** send MCP catalogs and vectorstores through the runner ([cdfc2fc](https://github.com/smarter-sh/smarter/commit/cdfc2fc4b3fa8353649cb003a71efa4ff6c9a94c)), closes [#1081](https://github.com/smarter-sh/smarter/issues/1081) [#1082](https://github.com/smarter-sh/smarter/issues/1082) [#1082](https://github.com/smarter-sh/smarter/issues/1082) [#1099](https://github.com/smarter-sh/smarter/issues/1099)

## [1.0.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v1.0.1...v1.0.2-alpha.1) (2026-11-28)

### Bug Fixes

* **helm:** give the restricted workers only the settings they read ([082ca37](https://github.com/smarter-sh/smarter/commit/082ca3747d024038b447552aaaf1b482c4b4b3ce))
* **llmtool:** send MCP catalogs and vectorstores through the runner ([cdfc2fc](https://github.com/smarter-sh/smarter/commit/cdfc2fc4b3fa8353649cb003a71efa4ff6c9a94c)), closes [#1081](https://github.com/smarter-sh/smarter/issues/1081) [#1082](https://github.com/smarter-sh/smarter/issues/1082) [#1082](https://github.com/smarter-sh/smarter/issues/1082) [#1099](https://github.com/smarter-sh/smarter/issues/1099)

## [1.0.1](https://github.com/smarter-sh/smarter/compare/v1.0.0...v1.0.1) (2026-11-28)

### Bug Fixes

- **helm:** give each kind of pod its own IAM role ([5d649e9](https://github.com/smarter-sh/smarter/commit/5d649e9144130952f49370fb6621ee0c0a573d7d)), closes [#1084](https://github.com/smarter-sh/smarter/issues/1084)

## [1.0.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v1.0.0...v1.0.1-alpha.1) (2026-11-28)

### Bug Fixes

- **helm:** give each kind of pod its own IAM role ([5d649e9](https://github.com/smarter-sh/smarter/commit/5d649e9144130952f49370fb6621ee0c0a573d7d)), closes [#1084](https://github.com/smarter-sh/smarter/issues/1084)

## [1.0.0](https://github.com/smarter-sh/smarter/compare/v0.48.15...v1.0.0) (2026-11-28)

### ⚠ BREAKING CHANGES

- **vectorstore:** to the REST api (pre-1.0, so no breaking-change marker): POST /api/v1/vectorstores/{id}/undeploy/ now answers 202 instead of 200, with the message Undeploy queued. and the status unchanged until the worker has stopped serving. The console's delete answers 200 with Vectorstore N is being deleted. for a deployed one. openapi.json is regenerated with make api-contract: undeploy's description and status changed. The SDKs that copy it pick this up with make contracts. The cli's undeploy and delete return the same journaled response, with the queued message.

Tests:

- VectorstoreTestBase patches the three new tasks' .delay for each test (provision_task, undeploy_task, delete_vectorstore_task), as it does deploy_vectorstore's, so nothing reaches a worker. A test runs a task itself, as deploy_now does a deploy's checks.

- test_tasks.py: provision_vectorstore applies the server, and records a cluster error; undeploy_vectorstore stops serving, and records a failure keeping the status; delete_vectorstore deletes the vectorstore, its Secret and its volume; a deletionProtection enabled since, or a backend error, keeps the vectorstore with why; and each returns None or False for a vectorstore that no longer exists.

- test_service.py: queue_provision and queue_undeploy record their message and queue their task, and the cluster sees no apply and no delete; queue_delete queues for a deployed vectorstore, deletes one never deployed at once, and refuses a protected one.

- The broker's lifecycle, the REST api's undeploy, the OpenAPI contract test and the console's delete now assert that the request queues, writes nothing to the cluster, and answers with the queued message or 202, then run the task and assert its result. The console's delete also deletes a never-deployed vectorstore at once.

- make docker-test: 8367 tests in 9 shards, OK; the vectorstore app alone, 112. The pre-commit hooks and check-docs.sh pass. Not run by hand: a self-hosted deploy, which would create a Qdrant server and volume in the shared cluster's smarter-local namespace.

Docs: the Vectorstore page says that undeploy and delete return at once, what the status message says until the worker is done, that a deployed Vectorstore is listed, deleting, until its database is destroyed, and that a changed self-hosted spec is applied by the worker. ADR-038's inventory of the app's cluster writes records that the vectorstore's are infrastructure tasks too, so the app only reads the cluster.

Co-authored-by: Lawrence McDaniel <lpm0073@gmail.com>

- **llmhost:** to the REST api (pre-1.0, so no breaking-change marker): POST /api/v1/llmhosts/{id}/undeploy/ now answers 202 instead of 200, and DELETE /api/v1/llmhosts/{id}/ answers 202 instead of 204. Deploy already answered 202. All three return before the infrastructure worker has acted, so a client follows the status, whose message is the queued one until the task replaces it. openapi.json is regenerated with make api-contract: the two descriptions and undeploy's status changed. The SDKs that copy it (smarter-python, smarter-nodejs, smarter-golang) pick this up with make contracts. The cli's deploy, undeploy and delete return the same journaled response as before, with the queued message.

Tests:

- New InMemoryLLMHostInfrastructureMixin (tests/base_classes.py) owns the in-memory cluster and node groups, disables DNS, and patches the .delay of each queued task to run it in the test process, and reconcile_llmhost_compute.apply_async to record only. It is listed last among the bases, so it is set up before any fixture is created and torn down after every fixture is deleted. That matters because deleting a compute, e.g. when the test account's deletion cascades, now queues delete_llmhost_nodegroup, and an unpatched .delay would reach a shard's real infrastructure worker. holding_queued_tasks() records the tasks without running them, so a test can see what the request alone did. LLMHostTestBase and both broker test classes use it, in place of their own copies of that setup, and it also resets the backends before each test.

- New test_tasks_queue.py: each queue function queues its task and writes nothing to the cluster; refuses at once on a missing Secret or an unreachable cluster, queuing nothing; delete allows an undeployed LLMHost without the cluster and refuses a deployed one; the receiver queues the node group's deletion by name, and not for an absent node group; and the admin action queues and reports.

- test_tasks.py: a launch, destroy or delete that fails in the task is recorded on the LLMHost; delete_llmhost deletes the LLMHost and its resources and reconciles the compute; delete_llmhost_nodegroup succeeds, and logs a cloud error; every task keeps its name. Its own apply_async patch gave way to the mixin's.

- The broker and api tests: the response carries the queued message, the task's result shows in describe, the status and the in-memory cluster, and with the tasks held the request applies, deletes and creates nothing. The compute broker's node group error is now the task's: logged, and the reconcile queued again.

- make docker-test: 8361 tests in 9 shards, OK; the llmhost app alone, 256. The pre-commit hooks and check-docs.sh pass. Not run by hand: a real deploy, because the dev stack's infrastructure worker would launch on the shared EKS cluster and could add a billable GPU node.

Docs: the LLMHost page says what deploy checks at once, that the worker launches and undeploys, and how delete behaves until the worker is done. The tasks reference is one page per module. ADR-038's inventory of the app's cluster writes records that the LLMHost and LLMHostCompute writes are infrastructure tasks now, and that the vectorstore's remain.

Follow-ups: the vectorstore's apply (re-provisioning a self-hosted server), undeploy and delete, from the broker, the REST api and the console's list view, are the rest of #1080. ComputeProvisioner.delete_nodegroup is now called only by its test.

Co-authored-by: Lawrence McDaniel <lpm0073@gmail.com>

### Bug Fixes

- **cache:** serve the console and LLMClients while Redis is down ([508e4f7](https://github.com/smarter-sh/smarter/commit/508e4f7702af4abddeccc4147350faed8320251f)), closes [#1052](https://github.com/smarter-sh/smarter/issues/1052) [#1052](https://github.com/smarter-sh/smarter/issues/1052)
- **celery:** each worker registers only its own queue's tasks ([ab4d0cf](https://github.com/smarter-sh/smarter/commit/ab4d0cfdc134519b2308e0a57d85f040b41fb41c))
- **celery:** prefetch one task per process, and never sleep in a task ([80bc4d8](https://github.com/smarter-sh/smarter/commit/80bc4d8c04f9266856f8ac6edddd2d71eeed3ecf)), closes [#1097](https://github.com/smarter-sh/smarter/issues/1097) [#1097](https://github.com/smarter-sh/smarter/issues/1097)
- **helm:** give each kind of pod a Secret of its own credentials ([b130796](https://github.com/smarter-sh/smarter/commit/b130796b00f1f8a5417a2550e8b87cd76d0809cb)), closes [#1084](https://github.com/smarter-sh/smarter/issues/1084)
- **helm:** give each kind of pod its own ServiceAccount and Role ([e6258f3](https://github.com/smarter-sh/smarter/commit/e6258f37a1f12e4175f04d77a785a024a6df3e96)), closes [#1084](https://github.com/smarter-sh/smarter/issues/1084) [smarter-sh/smarter-infrastructure#21](https://github.com/smarter-sh/smarter-infrastructure/issues/21) [#1080](https://github.com/smarter-sh/smarter/issues/1080) [smarter-sh/smarter-infrastructure#21](https://github.com/smarter-sh/smarter-infrastructure/issues/21)
- **llmhost:** queue LLMHost and compute writes for the infra worker ([e49c17a](https://github.com/smarter-sh/smarter/commit/e49c17a25376a478118a72fba75bf42b1292680a)), closes [#1080](https://github.com/smarter-sh/smarter/issues/1080) [#1084](https://github.com/smarter-sh/smarter/issues/1084)
- **secret:** bootstrap the app keys from a Kubernetes Secret ([24932d1](https://github.com/smarter-sh/smarter/commit/24932d1b62a8b582e7d10c720d32d4e14e327bfe))
- **settings:** say which pods hold each credential (ADR-038, phase 3) ([7bb6904](https://github.com/smarter-sh/smarter/commit/7bb6904395aeffd342f2809ce78234a4c0f7c8e2)), closes [#1084](https://github.com/smarter-sh/smarter/issues/1084)
- **vectorstore:** queue cluster writes for the infrastructure worker ([f2e2344](https://github.com/smarter-sh/smarter/commit/f2e2344e7819165ad9d8ced9a9944dc275343964)), closes [#1080](https://github.com/smarter-sh/smarter/issues/1080) [#1084](https://github.com/smarter-sh/smarter/issues/1084)

## [1.0.0-alpha.7](https://github.com/smarter-sh/smarter/compare/v1.0.0-alpha.6...v1.0.0-alpha.7) (2026-11-28)

### Bug Fixes

- **helm:** give each kind of pod its own ServiceAccount and Role ([e6258f3](https://github.com/smarter-sh/smarter/commit/e6258f37a1f12e4175f04d77a785a024a6df3e96)), closes [#1084](https://github.com/smarter-sh/smarter/issues/1084) [smarter-sh/smarter-infrastructure#21](https://github.com/smarter-sh/smarter-infrastructure/issues/21) [#1080](https://github.com/smarter-sh/smarter/issues/1080) [smarter-sh/smarter-infrastructure#21](https://github.com/smarter-sh/smarter-infrastructure/issues/21)

## [1.0.0-alpha.6](https://github.com/smarter-sh/smarter/compare/v1.0.0-alpha.5...v1.0.0-alpha.6) (2026-11-28)

### Bug Fixes

- **helm:** give each kind of pod a Secret of its own credentials ([b130796](https://github.com/smarter-sh/smarter/commit/b130796b00f1f8a5417a2550e8b87cd76d0809cb)), closes [#1084](https://github.com/smarter-sh/smarter/issues/1084)

## [1.0.0-alpha.5](https://github.com/smarter-sh/smarter/compare/v1.0.0-alpha.4...v1.0.0-alpha.5) (2026-11-28)

### Bug Fixes

- **secret:** bootstrap the app keys from a Kubernetes Secret ([24932d1](https://github.com/smarter-sh/smarter/commit/24932d1b62a8b582e7d10c720d32d4e14e327bfe))

## [1.0.0-alpha.4](https://github.com/smarter-sh/smarter/compare/v1.0.0-alpha.3...v1.0.0-alpha.4) (2026-11-28)

### Bug Fixes

- **settings:** say which pods hold each credential (ADR-038, phase 3) ([7bb6904](https://github.com/smarter-sh/smarter/commit/7bb6904395aeffd342f2809ce78234a4c0f7c8e2)), closes [#1084](https://github.com/smarter-sh/smarter/issues/1084)

## [1.0.0-alpha.3](https://github.com/smarter-sh/smarter/compare/v1.0.0-alpha.2...v1.0.0-alpha.3) (2026-11-28)

### Bug Fixes

- **celery:** prefetch one task per process, and never sleep in a task ([80bc4d8](https://github.com/smarter-sh/smarter/commit/80bc4d8c04f9266856f8ac6edddd2d71eeed3ecf)), closes [#1097](https://github.com/smarter-sh/smarter/issues/1097) [#1097](https://github.com/smarter-sh/smarter/issues/1097)

## [1.0.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v1.0.0-alpha.1...v1.0.0-alpha.2) (2026-11-28)

### ⚠ BREAKING CHANGES

- **vectorstore:** to the REST api (pre-1.0, so no breaking-change marker): POST /api/v1/vectorstores/{id}/undeploy/ now answers 202 instead of 200, with the message Undeploy queued. and the status unchanged until the worker has stopped serving. The console's delete answers 200 with Vectorstore N is being deleted. for a deployed one. openapi.json is regenerated with make api-contract: undeploy's description and status changed. The SDKs that copy it pick this up with make contracts. The cli's undeploy and delete return the same journaled response, with the queued message.

Tests:

- VectorstoreTestBase patches the three new tasks' .delay for each test (provision_task, undeploy_task, delete_vectorstore_task), as it does deploy_vectorstore's, so nothing reaches a worker. A test runs a task itself, as deploy_now does a deploy's checks.

- test_tasks.py: provision_vectorstore applies the server, and records a cluster error; undeploy_vectorstore stops serving, and records a failure keeping the status; delete_vectorstore deletes the vectorstore, its Secret and its volume; a deletionProtection enabled since, or a backend error, keeps the vectorstore with why; and each returns None or False for a vectorstore that no longer exists.

- test_service.py: queue_provision and queue_undeploy record their message and queue their task, and the cluster sees no apply and no delete; queue_delete queues for a deployed vectorstore, deletes one never deployed at once, and refuses a protected one.

- The broker's lifecycle, the REST api's undeploy, the OpenAPI contract test and the console's delete now assert that the request queues, writes nothing to the cluster, and answers with the queued message or 202, then run the task and assert its result. The console's delete also deletes a never-deployed vectorstore at once.

- make docker-test: 8367 tests in 9 shards, OK; the vectorstore app alone, 112. The pre-commit hooks and check-docs.sh pass. Not run by hand: a self-hosted deploy, which would create a Qdrant server and volume in the shared cluster's smarter-local namespace.

Docs: the Vectorstore page says that undeploy and delete return at once, what the status message says until the worker is done, that a deployed Vectorstore is listed, deleting, until its database is destroyed, and that a changed self-hosted spec is applied by the worker. ADR-038's inventory of the app's cluster writes records that the vectorstore's are infrastructure tasks too, so the app only reads the cluster.

Co-authored-by: Lawrence McDaniel <lpm0073@gmail.com>

### Bug Fixes

- **vectorstore:** queue cluster writes for the infrastructure worker ([f2e2344](https://github.com/smarter-sh/smarter/commit/f2e2344e7819165ad9d8ced9a9944dc275343964)), closes [#1080](https://github.com/smarter-sh/smarter/issues/1080) [#1084](https://github.com/smarter-sh/smarter/issues/1084)

## [1.0.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.16-alpha.2...v1.0.0-alpha.1) (2026-11-28)

### ⚠ BREAKING CHANGES

- **llmhost:** to the REST api (pre-1.0, so no breaking-change marker): POST /api/v1/llmhosts/{id}/undeploy/ now answers 202 instead of 200, and DELETE /api/v1/llmhosts/{id}/ answers 202 instead of 204. Deploy already answered 202. All three return before the infrastructure worker has acted, so a client follows the status, whose message is the queued one until the task replaces it. openapi.json is regenerated with make api-contract: the two descriptions and undeploy's status changed. The SDKs that copy it (smarter-python, smarter-nodejs, smarter-golang) pick this up with make contracts. The cli's deploy, undeploy and delete return the same journaled response as before, with the queued message.

Tests:

- New InMemoryLLMHostInfrastructureMixin (tests/base_classes.py) owns the in-memory cluster and node groups, disables DNS, and patches the .delay of each queued task to run it in the test process, and reconcile_llmhost_compute.apply_async to record only. It is listed last among the bases, so it is set up before any fixture is created and torn down after every fixture is deleted. That matters because deleting a compute, e.g. when the test account's deletion cascades, now queues delete_llmhost_nodegroup, and an unpatched .delay would reach a shard's real infrastructure worker. holding_queued_tasks() records the tasks without running them, so a test can see what the request alone did. LLMHostTestBase and both broker test classes use it, in place of their own copies of that setup, and it also resets the backends before each test.

- New test_tasks_queue.py: each queue function queues its task and writes nothing to the cluster; refuses at once on a missing Secret or an unreachable cluster, queuing nothing; delete allows an undeployed LLMHost without the cluster and refuses a deployed one; the receiver queues the node group's deletion by name, and not for an absent node group; and the admin action queues and reports.

- test_tasks.py: a launch, destroy or delete that fails in the task is recorded on the LLMHost; delete_llmhost deletes the LLMHost and its resources and reconciles the compute; delete_llmhost_nodegroup succeeds, and logs a cloud error; every task keeps its name. Its own apply_async patch gave way to the mixin's.

- The broker and api tests: the response carries the queued message, the task's result shows in describe, the status and the in-memory cluster, and with the tasks held the request applies, deletes and creates nothing. The compute broker's node group error is now the task's: logged, and the reconcile queued again.

- make docker-test: 8361 tests in 9 shards, OK; the llmhost app alone, 256. The pre-commit hooks and check-docs.sh pass. Not run by hand: a real deploy, because the dev stack's infrastructure worker would launch on the shared EKS cluster and could add a billable GPU node.

Docs: the LLMHost page says what deploy checks at once, that the worker launches and undeploys, and how delete behaves until the worker is done. The tasks reference is one page per module. ADR-038's inventory of the app's cluster writes records that the LLMHost and LLMHostCompute writes are infrastructure tasks now, and that the vectorstore's remain.

Follow-ups: the vectorstore's apply (re-provisioning a self-hosted server), undeploy and delete, from the broker, the REST api and the console's list view, are the rest of #1080. ComputeProvisioner.delete_nodegroup is now called only by its test.

Co-authored-by: Lawrence McDaniel <lpm0073@gmail.com>

### Bug Fixes

- **llmhost:** queue LLMHost and compute writes for the infra worker ([e49c17a](https://github.com/smarter-sh/smarter/commit/e49c17a25376a478118a72fba75bf42b1292680a)), closes [#1080](https://github.com/smarter-sh/smarter/issues/1080) [#1084](https://github.com/smarter-sh/smarter/issues/1084)
