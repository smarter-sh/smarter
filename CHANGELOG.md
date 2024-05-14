# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

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
