# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

## [0.16.7-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.16.7-alpha.1...v0.16.7-alpha.2) (2026-10-03)

### Bug Fixes

- color list view toolbar icons, gray out disabled toolbar buttons, and bump React package versions ([ba5d342](https://github.com/smarter-sh/smarter/commit/ba5d342acf1f1b4eb666a89b3ffb9035c7e6d301))

## [0.16.7-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.16.6...v0.16.7-alpha.1) (2026-10-03)

## [0.16.7](https://github.com/smarter-sh/smarter/compare/v0.16.6...v0.16.7) (2026-10-03)

### Bug Fixes

- disable the delete button in list views when a resource cannot be deleted ([f8baeaa](https://github.com/smarter-sh/smarter/commit/f8baeaab40141be9617f732294ba13c004226ed6))

## [0.16.7](https://github.com/smarter-sh/smarter/compare/v0.16.6...v0.16.7) (2026-10-03)

### Bug Fixes

- disable the delete button in list views when a resource cannot be deleted ([f8baeaa](https://github.com/smarter-sh/smarter/commit/f8baeaab40141be9617f732294ba13c004226ed6))

## [0.16.6](https://github.com/smarter-sh/smarter/compare/v0.16.5...v0.16.6) (2026-10-03)

### Bug Fixes

- refuse to delete resources that other resources depend on ([c8e8b1d](https://github.com/smarter-sh/smarter/commit/c8e8b1d3659d384909f8d917d9a4b18f18b69dc6))

## [0.16.5](https://github.com/smarter-sh/smarter/compare/v0.16.4...v0.16.5) (2026-10-03)

### Bug Fixes

- use utf8mb4 for MariaDB databases and decouple init job from backup flag ([1d4fe11](https://github.com/smarter-sh/smarter/commit/1d4fe1159803a3621c50354362fc9946abda6475))

## [0.16.4](https://github.com/smarter-sh/smarter/compare/v0.16.3...v0.16.4) (2026-10-03)

### Bug Fixes

- revert sql service name change back to smarter-mariadb ([cf569bb](https://github.com/smarter-sh/smarter/commit/cf569bbf9cdb1adaefb71e0ce72cc7cce2f177a8))

## [0.16.3](https://github.com/smarter-sh/smarter/compare/v0.16.2...v0.16.3) (2026-10-02)

### Bug Fixes

- **tests:** run create_prompt_history inline in test_handler_gobstoppers ([be4974d](https://github.com/smarter-sh/smarter/commit/be4974ded1dc62b212fa097d09f4e81950fb0f60))

## [0.16.2](https://github.com/smarter-sh/smarter/compare/v0.16.1...v0.16.2) (2026-10-02)

### Bug Fixes

- **conf:** accept the default-enabled AWS regions when AWS is not reachable ([6ba1f38](https://github.com/smarter-sh/smarter/commit/6ba1f383476751c888792fa1c2b498ecb5612351))

## [0.16.1](https://github.com/smarter-sh/smarter/compare/v0.16.0...v0.16.1) (2026-10-02)

### Bug Fixes

- **tests:** make four CI-only test failures deterministic ([b26fadd](https://github.com/smarter-sh/smarter/commit/b26fadd39476ce8ff324290f911c1f578aebf99b))

## [0.16.0](https://github.com/smarter-sh/smarter/compare/v0.15.1...v0.16.0) (2026-10-02)

### Features

- **account:** enforce budgets on any resource, with Budget manifests and budget vs actual charts ([ab24142](https://github.com/smarter-sh/smarter/commit/ab24142d299c37a0b0719c9fe80b04d4b5fdda28))
- **console:** list LLMHostCompute in the web console, and fix the list pages' clone, rename and delete ([aaacc81](https://github.com/smarter-sh/smarter/commit/aaacc8194281851b593ca299b019e2217b062a27))
- **llmhost:** run open-weight LLMs on our own Kubernetes cluster ([e77b3f4](https://github.com/smarter-sh/smarter/commit/e77b3f484af6a145637e52cb07fbe754664b2398))
- **proxy:** pass requests through to LLM provider APIs, with API keys kept as Smarter Secrets ([07a4220](https://github.com/smarter-sh/smarter/commit/07a42204cdfb8e48f51cdaa92b873f6a7efcb619))
- **vectorstore:** manage RAG vector databases: self-hosted Qdrant, Qdrant Cloud and Pinecone ([b904c24](https://github.com/smarter-sh/smarter/commit/b904c24c4590f7e493e23b8ef57b45966afddaed))

### Bug Fixes

- annotation keys, scaffolded api viewsets, secret api, and remaining tests ([de2f3f7](https://github.com/smarter-sh/smarter/commit/de2f3f70b0bccf7e37603e1ca6e9c8f041200734))
- **react:** replace \_\_dirname in Vite configs, and fix the manifest.json path ([ef8929c](https://github.com/smarter-sh/smarter/commit/ef8929c6f62235ba46577d784d54d98b967546f6))

## [0.16.0-alpha.6](https://github.com/smarter-sh/smarter/compare/v0.16.0-alpha.5...v0.16.0-alpha.6) (2026-10-02)

### Bug Fixes

- annotation keys, scaffolded api viewsets, secret api, and remaining tests ([de2f3f7](https://github.com/smarter-sh/smarter/commit/de2f3f70b0bccf7e37603e1ca6e9c8f041200734))

## [0.16.0-alpha.5](https://github.com/smarter-sh/smarter/compare/v0.16.0-alpha.4...v0.16.0-alpha.5) (2026-10-02)

### Features

- **vectorstore:** manage RAG vector databases: self-hosted Qdrant, Qdrant Cloud and Pinecone ([b904c24](https://github.com/smarter-sh/smarter/commit/b904c24c4590f7e493e23b8ef57b45966afddaed))

## [0.16.0-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.16.0-alpha.3...v0.16.0-alpha.4) (2026-10-02)

### Bug Fixes

- **react:** replace \_\_dirname in Vite configs, and fix the manifest.json path ([ef8929c](https://github.com/smarter-sh/smarter/commit/ef8929c6f62235ba46577d784d54d98b967546f6))

## [0.16.0-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.16.0-alpha.2...v0.16.0-alpha.3) (2026-10-02)

### Features

- **account:** enforce budgets on any resource, with Budget manifests and budget vs actual charts ([ab24142](https://github.com/smarter-sh/smarter/commit/ab24142d299c37a0b0719c9fe80b04d4b5fdda28))

## [0.16.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.16.0-alpha.1...v0.16.0-alpha.2) (2026-10-01)

### Features

- **proxy:** pass requests through to LLM provider APIs, with API keys kept as Smarter Secrets ([07a4220](https://github.com/smarter-sh/smarter/commit/07a42204cdfb8e48f51cdaa92b873f6a7efcb619))

## [0.16.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.15.1...v0.16.0-alpha.1) (2026-10-01)

### Features

- **console:** list LLMHostCompute in the web console, and fix the list pages' clone, rename and delete ([aaacc81](https://github.com/smarter-sh/smarter/commit/aaacc8194281851b593ca299b019e2217b062a27))
- **llmhost:** run open-weight LLMs on our own Kubernetes cluster ([e77b3f4](https://github.com/smarter-sh/smarter/commit/e77b3f484af6a145637e52cb07fbe754664b2398))
