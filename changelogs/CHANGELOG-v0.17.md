# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

## [0.17.4-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.17.3...v0.17.4-alpha.1) (2026-10-05)

### Bug Fixes

- **passthrough:** make the prompt passthrough work across providers, and test every template against every provider ([68ba9a5](https://github.com/smarter-sh/smarter/commit/68ba9a5fa62b29837bd2ff5476f5aeef2c7e0ad5))

## [0.17.3](https://github.com/smarter-sh/smarter/compare/v0.17.2...v0.17.3) (2026-10-04)

### Bug Fixes

- **api:** return intelligible errors with matching status codes from apply and prompt ([9c3e451](https://github.com/smarter-sh/smarter/commit/9c3e451520724ef33d2e52cf92b300b46d119ba7))

## [0.17.2-alpha.9](https://github.com/smarter-sh/smarter/compare/v0.17.2-alpha.8...v0.17.2-alpha.9) (2026-10-04)

### Bug Fixes

- **api:** return intelligible errors with matching status codes from apply and prompt ([9c3e451](https://github.com/smarter-sh/smarter/commit/9c3e451520724ef33d2e52cf92b300b46d119ba7))

## [0.17.2](https://github.com/smarter-sh/smarter/compare/v0.17.1...v0.17.2) (2026-10-04)

### Bug Fixes

- **dashboard:** live service health, activity, budget alerts, onboarding and quick actions ([a7d449d](https://github.com/smarter-sh/smarter/commit/a7d449d7d8e40603de32330da983b33ebaaace37))
- fix 18 vectorsearch and llmclient api bugs that unit tests had marked as expected failures ([f1f197f](https://github.com/smarter-sh/smarter/commit/f1f197fe29c1d0130bfca72e6654705e7d5663c0))
- fix 43 bugs that unit tests had marked as expected failures ([9b7f0ea](https://github.com/smarter-sh/smarter/commit/9b7f0ea598ba1d5946b9cc6e7b398d3b815a9689))
- fix LLMClient custom domains, Prompt manifests, example manifests, undeploy and kubectl deletes ([05f7ad4](https://github.com/smarter-sh/smarter/commit/05f7ad4a1562fc29d3786c08f6169625ddee8596))
- fix the last 10 bugs that unit tests had marked as expected failures ([f6c2458](https://github.com/smarter-sh/smarter/commit/f6c2458c73b0bc7f5d7db3d5ea4854d275d24b1c))
- **guardrail:** patch prompt Celery tasks in prompt integration tests to stop teardown races ([b0fee8b](https://github.com/smarter-sh/smarter/commit/b0fee8b3fccd29fc1df194ff87615c6c0bb4ef9d))
- isolate infrastructure tasks from operational tasks, never block a worker, and refresh the smarter LLMClient, its plugins and OpenAI models ([5a378b4](https://github.com/smarter-sh/smarter/commit/5a378b47fc8cae82d60f82875486528d1cce8ac8))
- stop retrying create_plugin_selector_history for a user who no longer exists ([84c72fa](https://github.com/smarter-sh/smarter/commit/84c72fab0da173e8e1c477aa5b40dc56251bcdfa))

## [0.17.2-alpha.8](https://github.com/smarter-sh/smarter/compare/v0.17.2-alpha.7...v0.17.2-alpha.8) (2026-10-04)

### Bug Fixes

- **dashboard:** live service health, activity, budget alerts, onboarding and quick actions ([a7d449d](https://github.com/smarter-sh/smarter/commit/a7d449d7d8e40603de32330da983b33ebaaace37))

## [0.17.2-alpha.7](https://github.com/smarter-sh/smarter/compare/v0.17.2-alpha.6...v0.17.2-alpha.7) (2026-10-04)

### Bug Fixes

- **guardrail:** patch prompt Celery tasks in prompt integration tests to stop teardown races ([b0fee8b](https://github.com/smarter-sh/smarter/commit/b0fee8b3fccd29fc1df194ff87615c6c0bb4ef9d))

## [0.17.2-alpha.6](https://github.com/smarter-sh/smarter/compare/v0.17.2-alpha.5...v0.17.2-alpha.6) (2026-10-04)

### Bug Fixes

- isolate infrastructure tasks from operational tasks, never block a worker, and refresh the smarter LLMClient, its plugins and OpenAI models ([5a378b4](https://github.com/smarter-sh/smarter/commit/5a378b47fc8cae82d60f82875486528d1cce8ac8))

## [0.17.2-alpha.5](https://github.com/smarter-sh/smarter/compare/v0.17.2-alpha.4...v0.17.2-alpha.5) (2026-10-04)

### Bug Fixes

- fix LLMClient custom domains, Prompt manifests, example manifests, undeploy and kubectl deletes ([05f7ad4](https://github.com/smarter-sh/smarter/commit/05f7ad4a1562fc29d3786c08f6169625ddee8596))

## [0.17.2-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.17.2-alpha.3...v0.17.2-alpha.4) (2026-10-04)

### Bug Fixes

- stop retrying create_plugin_selector_history for a user who no longer exists ([84c72fa](https://github.com/smarter-sh/smarter/commit/84c72fab0da173e8e1c477aa5b40dc56251bcdfa))

## [0.17.2-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.17.2-alpha.2...v0.17.2-alpha.3) (2026-10-04)

### Bug Fixes

- fix the last 10 bugs that unit tests had marked as expected failures ([f6c2458](https://github.com/smarter-sh/smarter/commit/f6c2458c73b0bc7f5d7db3d5ea4854d275d24b1c))

## [0.17.2-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.17.2-alpha.1...v0.17.2-alpha.2) (2026-10-04)

### Bug Fixes

- fix 18 vectorsearch and llmclient api bugs that unit tests had marked as expected failures ([f1f197f](https://github.com/smarter-sh/smarter/commit/f1f197fe29c1d0130bfca72e6654705e7d5663c0))

## [0.17.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.17.1...v0.17.2-alpha.1) (2026-10-04)

### Bug Fixes

- fix 43 bugs that unit tests had marked as expected failures ([9b7f0ea](https://github.com/smarter-sh/smarter/commit/9b7f0ea598ba1d5946b9cc6e7b398d3b815a9689))

## [0.17.0-alpha.8](https://github.com/smarter-sh/smarter/compare/v0.17.0-alpha.7...v0.17.0-alpha.8) (2026-10-04)

### Bug Fixes

- fix 43 bugs that unit tests had marked as expected failures ([9b7f0ea](https://github.com/smarter-sh/smarter/commit/9b7f0ea598ba1d5946b9cc6e7b398d3b815a9689))

## [0.17.0-alpha.7](https://github.com/smarter-sh/smarter/compare/v0.17.0-alpha.6...v0.17.0-alpha.7) (2026-10-04)

### Bug Fixes

- **tests:** provide EKS cluster name and region in kubeconfig tests ([436c7bd](https://github.com/smarter-sh/smarter/commit/436c7bd471932fbd18c394f60f8f9103f8f91b97))

## [0.17.1](https://github.com/smarter-sh/smarter/compare/v0.17.0...v0.17.1) (2026-10-04)

### Bug Fixes

- **tests:** provide EKS cluster name and region in kubeconfig tests ([436c7bd](https://github.com/smarter-sh/smarter/commit/436c7bd471932fbd18c394f60f8f9103f8f91b97))

## [0.17.0](https://github.com/smarter-sh/smarter/compare/v0.16.7...v0.17.0) (2026-10-04)

### Features

- edit, validate, save, clone and delete manifests in the web console's manifest editor ([b78b1d2](https://github.com/smarter-sh/smarter/commit/b78b1d200ac905d7a1aa3fb22ae2dd25b4e77e81))

### Bug Fixes

- color list view toolbar icons, gray out disabled toolbar buttons, and bump React package versions ([ba5d342](https://github.com/smarter-sh/smarter/commit/ba5d342acf1f1b4eb666a89b3ffb9035c7e6d301))
- fix 13 account and llmclient bugs found while raising the unit test coverage of smarter.apps.account to 91% ([e92adae](https://github.com/smarter-sh/smarter/commit/e92adae594a3942f1e8544c347cf8c284776f8da))
- fix 23 bugs found while raising the unit test coverage of smarter.common and smarter.lib to 90% ([da46f38](https://github.com/smarter-sh/smarter/commit/da46f38a96c62ae7e491e95115ed7a41fc95302f))
- fix 5 connection and plugin bugs, and add unit tests that raise the coverage of smarter.apps from 85% to 89.8% ([6240434](https://github.com/smarter-sh/smarter/commit/6240434a1651c51b6fb2d3d3df996c3cb01549e5))
- fix 9 api and cli bugs found while raising the unit test coverage of smarter.apps.api to 93% ([d118c6b](https://github.com/smarter-sh/smarter/commit/d118c6bd6f8c3da42a05669a214faadbfc8c3bf7))
- **plugin:** fix plugin updates through the api and boolean function parameters, remove the unused plugin api urls, and raise the plugin app's test coverage ([f34214e](https://github.com/smarter-sh/smarter/commit/f34214eab7b18b1548556fc14ae81021aad0765f))

## [0.17.1](https://github.com/smarter-sh/smarter/compare/v0.17.0...v0.17.1) (2026-10-04)

### Bug Fixes

- **tests:** provide EKS cluster name and region in kubeconfig tests ([436c7bd](https://github.com/smarter-sh/smarter/commit/436c7bd471932fbd18c394f60f8f9103f8f91b97))

## [0.17.0](https://github.com/smarter-sh/smarter/compare/v0.16.7...v0.17.0) (2026-10-04)

### Features

- edit, validate, save, clone and delete manifests in the web console's manifest editor ([b78b1d2](https://github.com/smarter-sh/smarter/commit/b78b1d200ac905d7a1aa3fb22ae2dd25b4e77e81))

### Bug Fixes

- color list view toolbar icons, gray out disabled toolbar buttons, and bump React package versions ([ba5d342](https://github.com/smarter-sh/smarter/commit/ba5d342acf1f1b4eb666a89b3ffb9035c7e6d301))
- fix 13 account and llmclient bugs found while raising the unit test coverage of smarter.apps.account to 91% ([e92adae](https://github.com/smarter-sh/smarter/commit/e92adae594a3942f1e8544c347cf8c284776f8da))
- fix 23 bugs found while raising the unit test coverage of smarter.common and smarter.lib to 90% ([da46f38](https://github.com/smarter-sh/smarter/commit/da46f38a96c62ae7e491e95115ed7a41fc95302f))
- fix 5 connection and plugin bugs, and add unit tests that raise the coverage of smarter.apps from 85% to 89.8% ([6240434](https://github.com/smarter-sh/smarter/commit/6240434a1651c51b6fb2d3d3df996c3cb01549e5))
- fix 9 api and cli bugs found while raising the unit test coverage of smarter.apps.api to 93% ([d118c6b](https://github.com/smarter-sh/smarter/commit/d118c6bd6f8c3da42a05669a214faadbfc8c3bf7))
- **plugin:** fix plugin updates through the api and boolean function parameters, remove the unused plugin api urls, and raise the plugin app's test coverage ([f34214e](https://github.com/smarter-sh/smarter/commit/f34214eab7b18b1548556fc14ae81021aad0765f))

## [0.17.0-alpha.6](https://github.com/smarter-sh/smarter/compare/v0.17.0-alpha.5...v0.17.0-alpha.6) (2026-10-04)

### Bug Fixes

- fix 5 connection and plugin bugs, and add unit tests that raise the coverage of smarter.apps from 85% to 89.8% ([6240434](https://github.com/smarter-sh/smarter/commit/6240434a1651c51b6fb2d3d3df996c3cb01549e5))

## [0.17.0-alpha.5](https://github.com/smarter-sh/smarter/compare/v0.17.0-alpha.4...v0.17.0-alpha.5) (2026-10-03)

### Bug Fixes

- **plugin:** fix plugin updates through the api and boolean function parameters, remove the unused plugin api urls, and raise the plugin app's test coverage ([f34214e](https://github.com/smarter-sh/smarter/commit/f34214eab7b18b1548556fc14ae81021aad0765f))

## [0.17.0-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.17.0-alpha.3...v0.17.0-alpha.4) (2026-10-03)

### Bug Fixes

- fix 9 api and cli bugs found while raising the unit test coverage of smarter.apps.api to 93% ([d118c6b](https://github.com/smarter-sh/smarter/commit/d118c6bd6f8c3da42a05669a214faadbfc8c3bf7))

## [0.17.0-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.17.0-alpha.2...v0.17.0-alpha.3) (2026-10-03)

### Bug Fixes

- fix 13 account and llmclient bugs found while raising the unit test coverage of smarter.apps.account to 91% ([e92adae](https://github.com/smarter-sh/smarter/commit/e92adae594a3942f1e8544c347cf8c284776f8da))

## [0.17.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.17.0-alpha.1...v0.17.0-alpha.2) (2026-10-03)

### Bug Fixes

- fix 23 bugs found while raising the unit test coverage of smarter.common and smarter.lib to 90% ([da46f38](https://github.com/smarter-sh/smarter/commit/da46f38a96c62ae7e491e95115ed7a41fc95302f))

## [0.17.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.16.7-alpha.2...v0.17.0-alpha.1) (2026-10-03)

### Features

- edit, validate, save, clone and delete manifests in the web console's manifest editor ([b78b1d2](https://github.com/smarter-sh/smarter/commit/b78b1d200ac905d7a1aa3fb22ae2dd25b4e77e81))
