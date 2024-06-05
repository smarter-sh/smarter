## [0.3.8](https://github.com/smarter-sh/smarter/compare/v0.3.7...v0.3.8) (2024-06-05)


### Bug Fixes

* force a new release ([37ee46f](https://github.com/smarter-sh/smarter/commit/37ee46f0a4ce4c557eda5ba30ffd8c6574bb7efd))

## [0.3.7](https://github.com/smarter-sh/smarter/compare/v0.3.6...v0.3.7) (2024-06-01)

### Bug Fixes

- force a new release ([71cf331](https://github.com/smarter-sh/smarter/commit/71cf3315f75190e0e909609da93a22e552fa6abe))

# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

## [0.3.2](https://github.com/smarter-sh/smarter/compare/v0.3.1...v0.3.2) (2024-05-31)

### Bug Fixes

- set url_chatbot() to urljoin(self.url, /api/v1/chatbot/smarter/) ([ad8036b](https://github.com/smarter-sh/smarter/commit/ad8036b1b487fc0619a5523bec52ab894c205184))
- set url_chatbot() to urljoin(self.url, /api/v1/chatbot/smarter/) ([7d2eb0c](https://github.com/smarter-sh/smarter/commit/7d2eb0c57d65e0d3d13a088490bd7ce3f6c411e4))

## [0.3.1](https://github.com/smarter-sh/smarter/compare/v0.3.0...v0.3.1) (2024-05-31)

### Bug Fixes

- url_chatbot should be urljoin(self.hostname, /api/v1/chatbot/smarter/) ([a794fdf](https://github.com/smarter-sh/smarter/commit/a794fdf7e4ea6525797247d790303e62e099bfcb))

## [0.3.6](https://github.com/smarter-sh/smarter/compare/v0.3.5...v0.3.6) (2024-06-01)

### Bug Fixes

- ensure that we fail gracefully ([3d4ab45](https://github.com/smarter-sh/smarter/commit/3d4ab4587a935575f5e32f8db66eb67e93cbcbef))
- make the error response match api/v1/cli error format ([c7f9f72](https://github.com/smarter-sh/smarter/commit/c7f9f72ec6b3ef42d115e4a4125689c6fa21ac01))

## [0.3.5](https://github.com/smarter-sh/smarter/compare/v0.3.4...v0.3.5) (2024-06-01)

### Bug Fixes

- RecursionError cause by self.user ([4362f84](https://github.com/smarter-sh/smarter/commit/4362f84068e4d828c1d8badc36424fcdb67b073a))

## [0.3.4](https://github.com/smarter-sh/smarter/compare/v0.3.3...v0.3.4) (2024-06-01)

### Bug Fixes

- add protocol to ChatBot.url_chatbot() ([4c146aa](https://github.com/smarter-sh/smarter/commit/4c146aa5f86dec432311b600015786111e4191a3))

## [0.3.3](https://github.com/smarter-sh/smarter/compare/v0.3.2...v0.3.3) (2024-06-01)

### Bug Fixes

- force a new release ([e66cbce](https://github.com/smarter-sh/smarter/commit/e66cbcef78f7af12c7d34e5ebcf9bc4d38715f9e))

## [0.3.2](https://github.com/smarter-sh/smarter/compare/v0.3.1...v0.3.2) (2024-05-31)

### Bug Fixes

- set url_chatbot() to urljoin(self.url, /api/v1/chatbot/smarter/) ([ad8036b](https://github.com/smarter-sh/smarter/commit/ad8036b1b487fc0619a5523bec52ab894c205184))
- set url_chatbot() to urljoin(self.url, /api/v1/chatbot/smarter/) ([7d2eb0c](https://github.com/smarter-sh/smarter/commit/7d2eb0c57d65e0d3d13a088490bd7ce3f6c411e4))

## [0.3.1](https://github.com/smarter-sh/smarter/compare/v0.3.0...v0.3.1) (2024-05-31)

### Bug Fixes

- url_chatbot should be urljoin(self.hostname, /api/v1/chatbot/smarter/) ([a794fdf](https://github.com/smarter-sh/smarter/commit/a794fdf7e4ea6525797247d790303e62e099bfcb))

## [0.3.0](https://github.com/smarter-sh/smarter/compare/v0.2.2...v0.3.0) (2024-05-31)

### Features

- create a universal journal to log all api request/response pairs ([2d2fbaa](https://github.com/smarter-sh/smarter/commit/2d2fbaae18fba5c56e93c7c06fe0cb4c132fc6f2))
- create SmarterJournaledJsonErrorResponse() ([bb1ab3b](https://github.com/smarter-sh/smarter/commit/bb1ab3b28c73722f33ca2cb98f82a94472e09695))
- pass prompt to broker via kwargs ([e4efb09](https://github.com/smarter-sh/smarter/commit/e4efb092ede55fe9f1a7befea9ca8d31934cee4f))
- code ApiV1CliChatApiView and refactor chatapp to make it work with journaled json responses ([8e500a7](https://github.com/smarter-sh/smarter/commit/8e500a71b348e81306bf414fb410b6004759113b))
- scaffold ApiV1CliChatApiView() ([31cfd1d](https://github.com/smarter-sh/smarter/commit/31cfd1d32a82f76646b5740436b5ef4ff4a405b1))
- scaffold ApiV1CliChatApiView() ([6f127bb](https://github.com/smarter-sh/smarter/commit/6f127bbc53ae1ad2164ad89cba3852a442011ac8))
- create SmarterTokenAuthenticationMiddleware to automate api key authentication

## [0.2.1](https://github.com/QueriumCorp/smarter/compare/v0.2.0...v0.2.1) (2024-05-19)

A refactor of the Django chatbot app.

### Feature

- add ChatBot.dns_verification_status
- add Django signals:
  - chatbot_dns_verification_initiated
  - chatbot_dns_verified
  - chatbot_dns_failed
  - chatbot_dns_verification_status_changed
- refactor aws route53 processes for asynchronous request handling
- add task to Undeploy a ChatBot
- add unit tests for tasks and manage.py commands
- refactor Dockerfile to improve layer caching
- refactor docker-compose.yaml and Helm chart to enable multiple worker threads

## [0.2.0](https://github.com/QueriumCorp/smarter/compare/v0.1.2...v0.2.0) (2024-05-16)

Introduces remote Sql server integration to the Plugin class. New Django ORMs PluginDataSql and PluginDataSqlConnection have been added for persinsting remote sql server connections, and parameterized sql queries. SAMPluginDataSqlConnectionBroker is added to fully integrate these models to /api/v1/cli.

### Features

- add SAMPluginDataSqlConnectionBroker to api/v1/cli ([f120cfd](https://github.com/QueriumCorp/smarter/commit/f120cfd3600a8e865e9dd43f9cde41a0312591df))
- add SAMPluginDataSqlConnectionBroker to api/v1/cli ([54fa4da](https://github.com/QueriumCorp/smarter/commit/54fa4da9f91d010adef4b737d0f7887e154767ac))
- add unit tests ([2c9e355](https://github.com/QueriumCorp/smarter/commit/2c9e35501d1824da521eb51cb937567627ab0dcb))
- scaffold PluginSql and Pydantic model ([e1bb076](https://github.com/QueriumCorp/smarter/commit/e1bb076ad428853c97505203cf35b476fc6dd30d))
- scaffold PluginSql models ([17daf61](https://github.com/QueriumCorp/smarter/commit/17daf615e74ed3f826fbf21db97d10d5174879bd))

## [0.1.2](https://github.com/QueriumCorp/smarter/compare/v0.1.1...v0.1.2) (2024-05-14)

Introduces a powerful new architecture for processing Kubernetes-style manifests for managing Smarter resources. The new Broker class architecture facilitates lightweight implementations of the smarter command-line implementation and the REST API that backs it.

### New features

- add /api/v1/cli rest api backing services for Go lang command-line interface
- add Pydantic to formally model cli manifests. Enforces manifest structural integrity as well as data and business rule validations.
- add SAMLoader, a generic yaml manifest loader for Pydantic
- add Broker class to abstract cli services implementations
- implement all Plugin cli services
- add a Controller class to Plugin, facilitating the future introduction of new data classes to support remote SQl databases and REST API data sources.

## [0.1.1](https://github.com/QueriumCorp/smarter/compare/v0.1.0...v0.1.1) (2024-04-02)

### New features

- add Helm charts
- add GitHub Actions CI/CD workflows
- add Makefile commands to automate local developer setup
- implement final chat REST API, referenced as http://{host}/admin/chat/chathistory/config/ which returns a context dict for a chat session. Enables a single authenticated Smarter user to manage multiple chat sessions in the sandbox.

## [0.1.0](https://github.com/QueriumCorp/smarter/compare/v0.0.1...v0.1.0) (2024-04-01)

### New features

- add FQDM's to CSRF_TRUSTED_ORIGINS ([6d6bd92](https://github.com/QueriumCorp/smarter/commit/6d6bd92dc8e9c5d162d3bd4359afbd58ef1a72ee))
- pass user to function_calling_plugin() ([0e6b1fa](https://github.com/QueriumCorp/smarter/commit/0e6b1fa94d853f1d4295ede704a3204adb53d24a))
- remove custom login.html ([b4f091f](https://github.com/QueriumCorp/smarter/commit/b4f091fd0a271cb1e12950e6ca4e5a1cdb8c038e))
- set CSRF_TRUSTED_ORIGINS = ALLOWED_HOSTS ([62a8ca3](https://github.com/QueriumCorp/smarter/commit/62a8ca38cd4d46207392c5839718abb981808da2))
- STATIC_URL = '/static/' ([277fff3](https://github.com/QueriumCorp/smarter/commit/277fff3aa2fe2aa32faf8699d3128398c36024a4))
- STATIC_URL = '/static/' ([89a2e0c](https://github.com/QueriumCorp/smarter/commit/89a2e0c5705064b878b254e83ac874d5c7fd6699))
- values in the CSRF_TRUSTED_ORIGINS setting must start with a scheme ([dc9ca5e](https://github.com/QueriumCorp/smarter/commit/dc9ca5e09d289bd33d15723a0b4352bbc08478b2))
- add api-key authentication ([491927f](https://github.com/QueriumCorp/smarter/commit/491927fe9d51594905ad1a1542e8e9b00de22871))
- add chat history models and signals ([07e5f82](https://github.com/QueriumCorp/smarter/commit/07e5f8223f96c886a35f1344a52d3ca748231310))
- automate build/deploy by environment ([f808ed5](https://github.com/QueriumCorp/smarter/commit/f808ed50d6148d193c73088696407db219cff008))
- restore most recent chat history when app starts up ([118d884](https://github.com/QueriumCorp/smarter/commit/118d88450a63bcf0ee1649fece7db0fbbac1c50d))

## [0.0.1](https://github.com/QueriumCorp/smarter/releases/tag/v0.0.1) (2024-02-21)

Django based REST API and ReactJS web app hosting an MVP plugin platform for OpenAI API Function Calling. This release implements the following features:

### New features

- Docker-based local development environment with MySQL and Redis
- Celery worker and beat support
- an integrated ReactJS web app for interacting with LLM chatbots.
- a multi-environment conf module based on Pydantic, that resolves automated parameter initializations using any combination of command line assignments, environment variables, .env and/or terraform.tfvars files.
- Django REST Framework driven API for accounts and Plugins
- Django backed Plugin class that can be initialized from either yaml or json files
- Django Account class that facilitate a team approach to managing Plugins
- Python unit tests for all modules
- Github Action CI/CD for automated unit testing on merges to staging and main, and automated Docker build/push to AWS ECR
- Terraform based AWS cloud infrastructure management of Kubernetes resources
- Pain-free onboarding of new developers, including a complete Makefile and pre-commit code formatting, code linting and misc security validation checks.
