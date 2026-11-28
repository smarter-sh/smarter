# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).



## [1.0.0-alpha.4](https://github.com/smarter-sh/smarter/compare/v1.0.0-alpha.3...v1.0.0-alpha.4) (2026-11-28)

### Bug Fixes

* **settings:** say which pods hold each credential (ADR-038, phase 3) ([7bb6904](https://github.com/smarter-sh/smarter/commit/7bb6904395aeffd342f2809ce78234a4c0f7c8e2)), closes [#1084](https://github.com/smarter-sh/smarter/issues/1084)

## [1.0.0-alpha.3](https://github.com/smarter-sh/smarter/compare/v1.0.0-alpha.2...v1.0.0-alpha.3) (2026-11-28)

### Bug Fixes

* **celery:** prefetch one task per process, and never sleep in a task ([80bc4d8](https://github.com/smarter-sh/smarter/commit/80bc4d8c04f9266856f8ac6edddd2d71eeed3ecf)), closes [#1097](https://github.com/smarter-sh/smarter/issues/1097) [#1097](https://github.com/smarter-sh/smarter/issues/1097)

## [1.0.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v1.0.0-alpha.1...v1.0.0-alpha.2) (2026-11-28)

### ⚠ BREAKING CHANGES

* **vectorstore:** to the REST api (pre-1.0, so no breaking-change marker): POST /api/v1/vectorstores/{id}/undeploy/ now answers 202 instead of 200, with the message Undeploy queued. and the status unchanged until the worker has stopped serving. The console's delete answers 200 with Vectorstore N is being deleted. for a deployed one. openapi.json is regenerated with make api-contract: undeploy's description and status changed. The SDKs that copy it pick this up with make contracts. The cli's undeploy and delete return the same journaled response, with the queued message.

Tests:

- VectorstoreTestBase patches the three new tasks' .delay for each test (provision_task, undeploy_task, delete_vectorstore_task), as it does deploy_vectorstore's, so nothing reaches a worker. A test runs a task itself, as deploy_now does a deploy's checks.

- test_tasks.py: provision_vectorstore applies the server, and records a cluster error; undeploy_vectorstore stops serving, and records a failure keeping the status; delete_vectorstore deletes the vectorstore, its Secret and its volume; a deletionProtection enabled since, or a backend error, keeps the vectorstore with why; and each returns None or False for a vectorstore that no longer exists.

- test_service.py: queue_provision and queue_undeploy record their message and queue their task, and the cluster sees no apply and no delete; queue_delete queues for a deployed vectorstore, deletes one never deployed at once, and refuses a protected one.

- The broker's lifecycle, the REST api's undeploy, the OpenAPI contract test and the console's delete now assert that the request queues, writes nothing to the cluster, and answers with the queued message or 202, then run the task and assert its result. The console's delete also deletes a never-deployed vectorstore at once.

- make docker-test: 8367 tests in 9 shards, OK; the vectorstore app alone, 112. The pre-commit hooks and check-docs.sh pass. Not run by hand: a self-hosted deploy, which would create a Qdrant server and volume in the shared cluster's smarter-local namespace.

Docs: the Vectorstore page says that undeploy and delete return at once, what the status message says until the worker is done, that a deployed Vectorstore is listed, deleting, until its database is destroyed, and that a changed self-hosted spec is applied by the worker. ADR-038's inventory of the app's cluster writes records that the vectorstore's are infrastructure tasks too, so the app only reads the cluster.

Co-authored-by: Lawrence McDaniel <lpm0073@gmail.com>

### Bug Fixes

* **vectorstore:** queue cluster writes for the infrastructure worker ([f2e2344](https://github.com/smarter-sh/smarter/commit/f2e2344e7819165ad9d8ced9a9944dc275343964)), closes [#1080](https://github.com/smarter-sh/smarter/issues/1080) [#1084](https://github.com/smarter-sh/smarter/issues/1084)

## [1.0.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.16-alpha.2...v1.0.0-alpha.1) (2026-11-28)

### ⚠ BREAKING CHANGES

* **llmhost:** to the REST api (pre-1.0, so no breaking-change marker): POST /api/v1/llmhosts/{id}/undeploy/ now answers 202 instead of 200, and DELETE /api/v1/llmhosts/{id}/ answers 202 instead of 204. Deploy already answered 202. All three return before the infrastructure worker has acted, so a client follows the status, whose message is the queued one until the task replaces it. openapi.json is regenerated with make api-contract: the two descriptions and undeploy's status changed. The SDKs that copy it (smarter-python, smarter-nodejs, smarter-golang) pick this up with make contracts. The cli's deploy, undeploy and delete return the same journaled response as before, with the queued message.

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

* **llmhost:** queue LLMHost and compute writes for the infra worker ([e49c17a](https://github.com/smarter-sh/smarter/commit/e49c17a25376a478118a72fba75bf42b1292680a)), closes [#1080](https://github.com/smarter-sh/smarter/issues/1080) [#1084](https://github.com/smarter-sh/smarter/issues/1084)

## [0.48.16-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.48.16-alpha.1...v0.48.16-alpha.2) (2026-11-28)

### Bug Fixes

* **celery:** each worker registers only its own queue's tasks ([ab4d0cf](https://github.com/smarter-sh/smarter/commit/ab4d0cfdc134519b2308e0a57d85f040b41fb41c))

## [0.48.16-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.15...v0.48.16-alpha.1) (2026-11-28)

### Bug Fixes

* **cache:** serve the console and LLMClients while Redis is down ([508e4f7](https://github.com/smarter-sh/smarter/commit/508e4f7702af4abddeccc4147350faed8320251f)), closes [#1052](https://github.com/smarter-sh/smarter/issues/1052) [#1052](https://github.com/smarter-sh/smarter/issues/1052)

## [0.48.15](https://github.com/smarter-sh/smarter/compare/v0.48.14...v0.48.15) (2026-11-27)

### Bug Fixes

* **settings:** keep credentials out of the tool workers, name each pod ([6dbbc20](https://github.com/smarter-sh/smarter/commit/6dbbc20bd9183600450912ad2ff29d150468c414)), closes [#1077](https://github.com/smarter-sh/smarter/issues/1077)

## [0.48.15-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.14...v0.48.15-alpha.1) (2026-11-27)

### Bug Fixes

* **settings:** keep credentials out of the tool workers, name each pod ([6dbbc20](https://github.com/smarter-sh/smarter/commit/6dbbc20bd9183600450912ad2ff29d150468c414)), closes [#1077](https://github.com/smarter-sh/smarter/issues/1077)

## [0.48.14](https://github.com/smarter-sh/smarter/compare/v0.48.13...v0.48.14) (2026-11-27)

### Bug Fixes

* **asgi:** run the web server's startup checks off uvicorn's event loop ([0ace3e0](https://github.com/smarter-sh/smarter/commit/0ace3e07b01fdd937837e774027b76f03d09ff9f)), closes [#1092](https://github.com/smarter-sh/smarter/issues/1092)
* **cache:** cache results in the tool workers' own redis keys ([cc31aec](https://github.com/smarter-sh/smarter/commit/cc31aec395a36ca9d4a797807fbf42b0a01ce794))

## [0.48.14-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.48.14-alpha.1...v0.48.14-alpha.2) (2026-11-27)

### Bug Fixes

* **asgi:** run the web server's startup checks off uvicorn's event loop ([0ace3e0](https://github.com/smarter-sh/smarter/commit/0ace3e07b01fdd937837e774027b76f03d09ff9f)), closes [#1092](https://github.com/smarter-sh/smarter/issues/1092)

## [0.48.14-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.13...v0.48.14-alpha.1) (2026-11-27)

### Bug Fixes

* **cache:** cache results in the tool workers' own redis keys ([cc31aec](https://github.com/smarter-sh/smarter/commit/cc31aec395a36ca9d4a797807fbf42b0a01ce794))

## [0.48.13](https://github.com/smarter-sh/smarter/compare/v0.48.12...v0.48.13) (2026-11-27)

### Bug Fixes

* **llmtool:** run extensions' tool calls in a worker of their own ([0cb303a](https://github.com/smarter-sh/smarter/commit/0cb303a9be289e22d1126e8daa68141609c60328)), closes [#1077](https://github.com/smarter-sh/smarter/issues/1077)

## [0.48.13-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.12...v0.48.13-alpha.1) (2026-11-27)

### Bug Fixes

* **llmtool:** run extensions' tool calls in a worker of their own ([0cb303a](https://github.com/smarter-sh/smarter/commit/0cb303a9be289e22d1126e8daa68141609c60328)), closes [#1077](https://github.com/smarter-sh/smarter/issues/1077)

## [0.48.12](https://github.com/smarter-sh/smarter/compare/v0.48.11...v0.48.12) (2026-11-27)

### Bug Fixes

* **infrastructure:** sum up the tool worker's startup checks ([db2b97a](https://github.com/smarter-sh/smarter/commit/db2b97ae34d34200a44122749c3ed29b8c574688))

## [0.48.12-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.11...v0.48.12-alpha.1) (2026-11-27)

### Bug Fixes

* **infrastructure:** sum up the tool worker's startup checks ([db2b97a](https://github.com/smarter-sh/smarter/commit/db2b97ae34d34200a44122749c3ed29b8c574688))

## [0.48.11](https://github.com/smarter-sh/smarter/compare/v0.48.10...v0.48.11) (2026-11-27)

### Bug Fixes

* **helm:** check the tool worker's liveness without pinging it ([89487b4](https://github.com/smarter-sh/smarter/commit/89487b49c6205b0ef50dc267eb3938cad63824e7))

## [0.48.11-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.10...v0.48.11-alpha.1) (2026-11-27)

### Bug Fixes

* **helm:** check the tool worker's liveness without pinging it ([89487b4](https://github.com/smarter-sh/smarter/commit/89487b49c6205b0ef50dc267eb3938cad63824e7))

## [0.48.10](https://github.com/smarter-sh/smarter/compare/v0.48.9...v0.48.10) (2026-11-27)

### Bug Fixes

* **helm:** define redis's tools user at start, not with auth.acl ([260bd6e](https://github.com/smarter-sh/smarter/commit/260bd6ef52025d3e178aad167fbab0d93f6ada1c))

## [0.48.10-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.9...v0.48.10-alpha.1) (2026-11-27)

### Bug Fixes

* **helm:** define redis's tools user at start, not with auth.acl ([260bd6e](https://github.com/smarter-sh/smarter/commit/260bd6ef52025d3e178aad167fbab0d93f6ada1c))

## [0.48.9](https://github.com/smarter-sh/smarter/compare/v0.48.8...v0.48.9) (2026-11-27)

### Bug Fixes

* **docker:** give build-time manage.py a throwaway redis password ([0274b0a](https://github.com/smarter-sh/smarter/commit/0274b0a3308ce73daa70874cfb4d0a3ddcfc7e0e)), closes [#1073](https://github.com/smarter-sh/smarter/issues/1073)
* **llmtool:** give the tool worker a redis acl user of its own ([5e20664](https://github.com/smarter-sh/smarter/commit/5e206644b075af8993298d450b078f52bb845026)), closes [#1065](https://github.com/smarter-sh/smarter/issues/1065) [#1073](https://github.com/smarter-sh/smarter/issues/1073) [#1077](https://github.com/smarter-sh/smarter/issues/1077)
* **settings:** generate redis's password per environment, never public ([d1a7d32](https://github.com/smarter-sh/smarter/commit/d1a7d32524da7335ad78a55255d3c28080998603)), closes [#1073](https://github.com/smarter-sh/smarter/issues/1073)

## [0.48.9-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.48.9-alpha.1...v0.48.9-alpha.2) (2026-11-27)

### Bug Fixes

* **docker:** give build-time manage.py a throwaway redis password ([0274b0a](https://github.com/smarter-sh/smarter/commit/0274b0a3308ce73daa70874cfb4d0a3ddcfc7e0e)), closes [#1073](https://github.com/smarter-sh/smarter/issues/1073)
* **llmtool:** give the tool worker a redis acl user of its own ([5e20664](https://github.com/smarter-sh/smarter/commit/5e206644b075af8993298d450b078f52bb845026)), closes [#1065](https://github.com/smarter-sh/smarter/issues/1065) [#1073](https://github.com/smarter-sh/smarter/issues/1073) [#1077](https://github.com/smarter-sh/smarter/issues/1077)

## [0.48.9-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.8...v0.48.9-alpha.1) (2026-11-27)

### Bug Fixes

* **settings:** generate redis's password per environment, never public ([d1a7d32](https://github.com/smarter-sh/smarter/commit/d1a7d32524da7335ad78a55255d3c28080998603)), closes [#1073](https://github.com/smarter-sh/smarter/issues/1073)

## [0.48.8](https://github.com/smarter-sh/smarter/compare/v0.48.7...v0.48.8) (2026-11-27)

### Bug Fixes

* **api:** log api requests' users by id, not username ([395248b](https://github.com/smarter-sh/smarter/commit/395248bb96c431fc70729e6ced7c339e03acd097)), closes [#1067](https://github.com/smarter-sh/smarter/issues/1067)
* **llmclient:** roll back a new llmclient when its apply fails ([ac903e5](https://github.com/smarter-sh/smarter/commit/ac903e56df9a30b17936bde9b61aff5a2f71f9fe))
* **settings:** confirm smtp is disabled in the tool worker ([adbbf8c](https://github.com/smarter-sh/smarter/commit/adbbf8c7d1cd809d18ca05b70ab8e3400c61dab3))

## [0.48.8-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.48.8-alpha.1...v0.48.8-alpha.2) (2026-11-27)

### Bug Fixes

* **llmclient:** roll back a new llmclient when its apply fails ([ac903e5](https://github.com/smarter-sh/smarter/commit/ac903e56df9a30b17936bde9b61aff5a2f71f9fe))
* **settings:** confirm smtp is disabled in the tool worker ([adbbf8c](https://github.com/smarter-sh/smarter/commit/adbbf8c7d1cd809d18ca05b70ab8e3400c61dab3))

## [0.48.8-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.7...v0.48.8-alpha.1) (2026-11-27)

### Bug Fixes

* **api:** log api requests' users by id, not username ([395248b](https://github.com/smarter-sh/smarter/commit/395248bb96c431fc70729e6ced7c339e03acd097)), closes [#1067](https://github.com/smarter-sh/smarter/issues/1067)

## [0.48.7](https://github.com/smarter-sh/smarter/compare/v0.48.6...v0.48.7) (2026-11-26)

### Bug Fixes

* **infrastructure:** add startup checks, confirm tool worker isolation ([7bd2b67](https://github.com/smarter-sh/smarter/commit/7bd2b67c47a7b7e0b601c90ec143560e0a9e423d))

## [0.48.7-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.6...v0.48.7-alpha.1) (2026-11-26)

### Bug Fixes

* **infrastructure:** add startup checks, confirm tool worker isolation ([7bd2b67](https://github.com/smarter-sh/smarter/commit/7bd2b67c47a7b7e0b601c90ec143560e0a9e423d))

## [0.48.6](https://github.com/smarter-sh/smarter/compare/v0.48.5...v0.48.6) (2026-11-26)

### Bug Fixes

* **celery:** register only run_tool_call in the tool worker ([6c146c0](https://github.com/smarter-sh/smarter/commit/6c146c070008c652416c2d3606f09efc4cf098a3))
* **llmclient:** log the url and LLMClient that the middleware verified ([3c51d0d](https://github.com/smarter-sh/smarter/commit/3c51d0d3bb83be21f89f933e02cbf28a1c993305))

## [0.48.6-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.5...v0.48.6-alpha.1) (2026-11-26)

### Bug Fixes

* **celery:** register only run_tool_call in the tool worker ([6c146c0](https://github.com/smarter-sh/smarter/commit/6c146c070008c652416c2d3606f09efc4cf098a3))
* **llmclient:** log the url and LLMClient that the middleware verified ([3c51d0d](https://github.com/smarter-sh/smarter/commit/3c51d0d3bb83be21f89f933e02cbf28a1c993305))

## [0.48.5](https://github.com/smarter-sh/smarter/compare/v0.48.4...v0.48.5) (2026-11-26)

### Bug Fixes

* **llmtool:** log one labeled line per tool call in the tool worker ([eea7350](https://github.com/smarter-sh/smarter/commit/eea7350a2984e2629529c07ab5d7fca281088095))
* **logging:** log prompts by id and simplify verbose request messages ([c09e0d6](https://github.com/smarter-sh/smarter/commit/c09e0d63c27037b6a4677f029f9840c824278803))

### Refactoring

* import json from smarter.lib everywhere in the package ([15c4e55](https://github.com/smarter-sh/smarter/commit/15c4e559f76def70a6ec196ddba7e821bc00881d))

## [0.48.5-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.4...v0.48.5-alpha.1) (2026-11-26)

### Bug Fixes

* **llmtool:** log one labeled line per tool call in the tool worker ([eea7350](https://github.com/smarter-sh/smarter/commit/eea7350a2984e2629529c07ab5d7fca281088095))
* **logging:** log prompts by id and simplify verbose request messages ([c09e0d6](https://github.com/smarter-sh/smarter/commit/c09e0d63c27037b6a4677f029f9840c824278803))

### Refactoring

* import json from smarter.lib everywhere in the package ([15c4e55](https://github.com/smarter-sh/smarter/commit/15c4e559f76def70a6ec196ddba7e821bc00881d))

## [0.48.4](https://github.com/smarter-sh/smarter/compare/v0.48.3...v0.48.4) (2026-11-26)

### Bug Fixes

* **connection:** describe shows Secrets' names, never their values ([28767e9](https://github.com/smarter-sh/smarter/commit/28767e9771d44818fa800ca4fd0599ba7fe74efb))
* **connection:** make the SqlConnection SSH tunnel work, via the runner ([d320401](https://github.com/smarter-sh/smarter/commit/d32040170b3cb547c6e0bf2ec763fcebc52f69c8))
* **connection:** refuse api connection urls that aren't public (SSRF) ([4ce9e59](https://github.com/smarter-sh/smarter/commit/4ce9e597026a61e41aee04773de88a7c0dc63d16))
* **helm:** deploy the tool worker, off by default ([48a485c](https://github.com/smarter-sh/smarter/commit/48a485c7c81eafead26b5885d6e65dbbad3a8b50))
* **llmtool:** run tool calls in a worker without credentials ([8f7285c](https://github.com/smarter-sh/smarter/commit/8f7285c386492c8da8122a4e20620e17e2b4e05a))

### Refactoring

* **connection:** run ApiPlugin requests through the tool runner ([f5842ab](https://github.com/smarter-sh/smarter/commit/f5842ab4cd233f410a4d1c602b0c0c5f121f45c3))
* **llmtool:** run Extension tool calls through the tool runner ([fa04d8f](https://github.com/smarter-sh/smarter/commit/fa04d8f1fbaa622cca3d11ea27083d749094bb96))
* **llmtool:** run web and image search requests through the runner ([d53ebcd](https://github.com/smarter-sh/smarter/commit/d53ebcde3037858fefea1220e440ccb235de8ecc))
* **llmtool:** run web search page fetches through the tool runner ([a88d0f2](https://github.com/smarter-sh/smarter/commit/a88d0f28176c849c780d013655ce47875b1d961e))
* **mcpclient:** run MCP tool calls through the new tool runner ([3114186](https://github.com/smarter-sh/smarter/commit/31141865e03a21678e2217213511e78df11293b6))

## [0.48.4-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.48.4-alpha.3...v0.48.4-alpha.4) (2026-11-26)

### Bug Fixes

* **helm:** deploy the tool worker, off by default ([48a485c](https://github.com/smarter-sh/smarter/commit/48a485c7c81eafead26b5885d6e65dbbad3a8b50))
* **llmtool:** run tool calls in a worker without credentials ([8f7285c](https://github.com/smarter-sh/smarter/commit/8f7285c386492c8da8122a4e20620e17e2b4e05a))

## [0.48.4-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.48.4-alpha.2...v0.48.4-alpha.3) (2026-11-26)

### Bug Fixes

* **connection:** describe shows Secrets' names, never their values ([28767e9](https://github.com/smarter-sh/smarter/commit/28767e9771d44818fa800ca4fd0599ba7fe74efb))

### Refactoring

* **llmtool:** run Extension tool calls through the tool runner ([fa04d8f](https://github.com/smarter-sh/smarter/commit/fa04d8f1fbaa622cca3d11ea27083d749094bb96))

## [0.48.4-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.48.4-alpha.1...v0.48.4-alpha.2) (2026-11-26)

### Bug Fixes

* **connection:** make the SqlConnection SSH tunnel work, via the runner ([d320401](https://github.com/smarter-sh/smarter/commit/d32040170b3cb547c6e0bf2ec763fcebc52f69c8))

### Refactoring

* **connection:** run ApiPlugin requests through the tool runner ([f5842ab](https://github.com/smarter-sh/smarter/commit/f5842ab4cd233f410a4d1c602b0c0c5f121f45c3))
* **llmtool:** run web and image search requests through the runner ([d53ebcd](https://github.com/smarter-sh/smarter/commit/d53ebcde3037858fefea1220e440ccb235de8ecc))
* **llmtool:** run web search page fetches through the tool runner ([a88d0f2](https://github.com/smarter-sh/smarter/commit/a88d0f28176c849c780d013655ce47875b1d961e))
* **mcpclient:** run MCP tool calls through the new tool runner ([3114186](https://github.com/smarter-sh/smarter/commit/31141865e03a21678e2217213511e78df11293b6))

## [0.48.4-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.3...v0.48.4-alpha.1) (2026-11-26)

### Bug Fixes

* **connection:** refuse api connection urls that aren't public (SSRF) ([4ce9e59](https://github.com/smarter-sh/smarter/commit/4ce9e597026a61e41aee04773de88a7c0dc63d16))

## [0.48.3](https://github.com/smarter-sh/smarter/compare/v0.48.2...v0.48.3) (2026-11-25)

### Bug Fixes

* **account:** log users by id, not username, on sign-in and User saves ([2154890](https://github.com/smarter-sh/smarter/commit/2154890d6125da358f51575f4c0b9cd4f64068fa)), closes [#1001](https://github.com/smarter-sh/smarter/issues/1001) [#1055](https://github.com/smarter-sh/smarter/issues/1055) [#1055](https://github.com/smarter-sh/smarter/issues/1055)
* **helm:** default the image to mcdaniel0073/smarter on docker hub ([3b1d771](https://github.com/smarter-sh/smarter/commit/3b1d7711526999b5e76cc78dcff0a4cc7c8cce80))

## [0.48.3-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.2...v0.48.3-alpha.1) (2026-11-25)

### Bug Fixes

* **account:** log users by id, not username, on sign-in and User saves ([2154890](https://github.com/smarter-sh/smarter/commit/2154890d6125da358f51575f4c0b9cd4f64068fa)), closes [#1001](https://github.com/smarter-sh/smarter/issues/1001) [#1055](https://github.com/smarter-sh/smarter/issues/1055) [#1055](https://github.com/smarter-sh/smarter/issues/1055)
* **helm:** default the image to mcdaniel0073/smarter on docker hub ([3b1d771](https://github.com/smarter-sh/smarter/commit/3b1d7711526999b5e76cc78dcff0a4cc7c8cce80))

## [0.48.2](https://github.com/smarter-sh/smarter/compare/v0.48.1...v0.48.2) (2026-11-25)

### Bug Fixes

- **helm:** run mariadb, redis and loki on the stateful node pool ([19cc09c](https://github.com/smarter-sh/smarter/commit/19cc09c7cbdf214721052ffb6a11f95ba36cd9b0)), closes [#942](https://github.com/smarter-sh/smarter/issues/942) [#1052](https://github.com/smarter-sh/smarter/issues/1052) [#929](https://github.com/smarter-sh/smarter/issues/929) [#931](https://github.com/smarter-sh/smarter/issues/931)

## [0.48.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.1...v0.48.2-alpha.1) (2026-11-25)

### Bug Fixes

- **helm:** run mariadb, redis and loki on the stateful node pool ([19cc09c](https://github.com/smarter-sh/smarter/commit/19cc09c7cbdf214721052ffb6a11f95ba36cd9b0)), closes [#942](https://github.com/smarter-sh/smarter/issues/942) [#1052](https://github.com/smarter-sh/smarter/issues/1052) [#929](https://github.com/smarter-sh/smarter/issues/929) [#931](https://github.com/smarter-sh/smarter/issues/931)

## [0.48.1](https://github.com/smarter-sh/smarter/compare/v0.48.0...v0.48.1) (2026-11-25)

### Bug Fixes

- **account:** add a Tutorials row to the welcome email ([414fb59](https://github.com/smarter-sh/smarter/commit/414fb59182ae2b188f1c34f5c00457e143c8f66e))
- **account:** link the welcome email's video to YouTube ([b7b594c](https://github.com/smarter-sh/smarter/commit/b7b594cb15ae52973fc3f701bf723c71b917012c))
- **cache:** bump cache-results to 0.2.2 to survive redis outages ([dde5f84](https://github.com/smarter-sh/smarter/commit/dde5f84abc95aadbd7b911c9be9841ba4c9293c6)), closes [smarter-sh/cache-results#11](https://github.com/smarter-sh/cache-results/issues/11) [#941](https://github.com/smarter-sh/smarter/issues/941)

### Refactoring

- **helm:** rename the api's values key from app to api ([0ccf00b](https://github.com/smarter-sh/smarter/commit/0ccf00bff881e64cfc0eb2b59f4d97b3e0ee771a))

## [0.48.1-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.48.1-alpha.2...v0.48.1-alpha.3) (2026-11-24)

### Bug Fixes

- **cache:** bump cache-results to 0.2.2 to survive redis outages ([dde5f84](https://github.com/smarter-sh/smarter/commit/dde5f84abc95aadbd7b911c9be9841ba4c9293c6)), closes [smarter-sh/cache-results#11](https://github.com/smarter-sh/cache-results/issues/11) [#941](https://github.com/smarter-sh/smarter/issues/941)

### Refactoring

- **helm:** rename the api's values key from app to api ([0ccf00b](https://github.com/smarter-sh/smarter/commit/0ccf00bff881e64cfc0eb2b59f4d97b3e0ee771a))

## [0.48.1-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.48.1-alpha.1...v0.48.1-alpha.2) (2026-11-24)

### Bug Fixes

- **account:** add a Tutorials row to the welcome email ([414fb59](https://github.com/smarter-sh/smarter/commit/414fb59182ae2b188f1c34f5c00457e143c8f66e))

## [0.48.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.0...v0.48.1-alpha.1) (2026-11-24)

### Bug Fixes

- **account:** link the welcome email's video to YouTube ([b7b594c](https://github.com/smarter-sh/smarter/commit/b7b594cb15ae52973fc3f701bf723c71b917012c))

## [0.48.0](https://github.com/smarter-sh/smarter/compare/v0.47.6...v0.48.0) (2026-11-24)

### Features

- **account:** batch apply GitHub repositories, and check LLM prices ([f6fa0bf](https://github.com/smarter-sh/smarter/commit/f6fa0bf3aeb6bd94374246d48a01364b0aab5b0a))
- **doodle:** email new drawings; serve the newest, and any one doodle ([38d9b31](https://github.com/smarter-sh/smarter/commit/38d9b3105eb90002445c17662b4c514bdad9cbff))

### Bug Fixes

- **docs:** list every page in the sitemap after an incremental build ([f60aec0](https://github.com/smarter-sh/smarter/commit/f60aec0b894a42f68725e087a538e5f62c74916b))
- **settings:** indent the startup environment log by two spaces ([ed6f71f](https://github.com/smarter-sh/smarter/commit/ed6f71f5b93791be8f218ccf8a55e14cdf72181d))

## [0.48.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.47.7-alpha.1...v0.48.0-alpha.1) (2026-11-24)

### Features

- **account:** batch apply GitHub repositories, and check LLM prices ([f6fa0bf](https://github.com/smarter-sh/smarter/commit/f6fa0bf3aeb6bd94374246d48a01364b0aab5b0a))
- **doodle:** email new drawings; serve the newest, and any one doodle ([38d9b31](https://github.com/smarter-sh/smarter/commit/38d9b3105eb90002445c17662b4c514bdad9cbff))
