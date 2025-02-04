# Querium Smarter

[![OpenAI](https://a11ybadges.com/badge?logo=openai)](https://platform.openai.com/)
[![LangChain](https://a11ybadges.com/badge?text=LangChain&badgeColor=0834ac)](https://www.langchain.com/)
[![Python](https://a11ybadges.com/badge?logo=python)](https://www.python.org/)
[![Django](https://a11ybadges.com/badge?logo=django)](https://www.djangoproject.com/)
[![Unit Tests](https://github.com/QueriumCorp/smarter/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/QueriumCorp/smarter/actions/workflows/releaseController.yml)
![Release Status](https://github.com/QueriumCorp/smarter/actions/workflows/release.yml/badge.svg?branch=main)
![Auto Assign](https://github.com/QueriumCorp/smarter/actions/workflows/auto-assign.yml/badge.svg)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![hack.d Lawrence McDaniel](https://img.shields.io/badge/hack.d-Lawrence%20McDaniel-orange.svg)](https://lawrencemcdaniel.com)

**Smarter is an enterprise-class platform for designing and managing chat solutions. Think of Smarter as the 'Redhat Linux' of chat.**

Smarter gives prompt engineering teams an intuitive workbench approach to designing, prototyping, testing, deploying and managing powerful chat solutions for common corporate use cases including customer sales support, vendor/supplier management, human resources, and more. Smarter is compatible with a wide variety of chatbot UI front ends for technology ecosystems such as NPM, Wordpress, Squarespace, Drupal, Office 365, Sharepoint, .Net, Netsuite, salesforce.com, and SAP. It is developed to support prompt engineering teams working in large organizations. Accordindly, Smarter provides common enterprise features such as security, accounting cost codes, and audit capabilities.

Smarter is LLM provider-agnostic, and provides seamless integrations to a continuously evolving list of value added services for security management, prompt content moderation, audit, cost accounting, and workflow management. It can be used as a pay-as-you-go, platform as a service, or, installed in your own AWS cloud account and supported by Querium's professional services team. It can also be installed on-premise in a hybrid model.

Smarter is cost effective when running at scale. It is extensible and architected on the philosophy of a compact core that does not require customization nor forking. It is horizontally scalable. It is natively multi-tenant, and can be installed alongside your existing systems. The principal technologies in the Smarter platform stack include:

- Ubuntu Linux
- Docker/Kubernetes/Helm
- MySQL
- Redis
- Terraform/awscli/Boto3
- Python/Django
- Pytest/Pluggy
- Langchain
- Pydantic
- ReactJS/Bootstrap
- Go lang
- GitHub Actions

## Designed by and for prompt engineers

Smarter provides design teams with a web console, and a convenient yaml manifest-based command-line interface for Windows, macOS, and Linux.

### LLM Providers

Smarter is currently compatible with the following LLM providers:

- Google AI: Gemini, Aqa
- Meta AI: Llama, Phi 3, Gema, Mistral, Qwen, nous-hermes
- OpenAI: chatGPT, o1
- DeepSeek R1, V3

### Plugin Architecture

Smarter features a unique Plugin architecture for extending the knowledge domain of any LLM aimed at generative AI text completions. Smarter Plugins are uncharacteristically accurate, highly cost effective, and have been designed around the needs of enterprise customers. Its unique 'selector' feature gives prompt engineers a sosphisticated strategy for managing when and how LLM's can make use of Smarter Plugin's powerful data integrations, which include the following:

- **Static**: an easy to implement scheme in which your private data is simply included in yaml Plugin manifest file.
- **Sql**: a flexible parameterized manifest scheme that exposes query parameters to the LLM, enabling it to make precise requests via proxy to your corporate databases.
- **Rest Api**: Similarly, you can also configure proxy connections to your Rest Api's, enabling the LLM to make precise requests to an unlimited range of private data sources.

### Yaml Manifest Resource Management

Smarter brings a [yaml-based manifest file](./smarter/smarter/apps/plugin/data/sample-plugins/example-configuration.yaml) approach to prompt engineering, originally inspired by the [kubectl](https://kubernetes.io/docs/reference/kubectl/) command-line interface for [Kubernetes](https://kubernetes.io/).

### Smarter ChatBot APIs

The following collection of rest api url endpoints are implemented for all Smarter chatbot, where `example` is the name of the chatbot. The chatbot sandbox React app and configuration api are available via these two url's, both of which require authentication and are only available to user associated with the Account to which the chatbot belongs.

```console
https://platform.smarter.sh/chatapp/example/
https://platform.smarter.sh/chatapp/example/config/
```

Chatbot REST api's are available at several different styles of url endpoint depending on your needs. Deployed chatbots are accessible via either of these two styles. These url's do not require authentication (ie they are publicly accessible) unless the customer chooses to add an optional api key.

```console
https://example.3141-5926-5359.api.platform.smarter.sh/chatbot/
https://custom-domain.com/chatbot/
```

Additionally, there's a sandbox url which works with Django authentication and is accessible regardless of the chatbot's deployment status.

```console
https://platform.smarter.sh/api/v0/chatbots/1/chatbot/
```

### ChatBot API

Customers can deploy personalized ChatBots with a choice of domain. The default URL format is as follows.

- api: [user-defined-subdomain].####-####-####.api.smarter.sh/chatbot/
- webapp: [user-defined-subdomain].####-####-####.api.smarter.sh/chatbot/webapp/

Customers can optionally register a custom domain which typically can be verified and activated in around 4 hours.

## Developer Quickstart

See onboarding videos:

- [Querium Smarter Developer Onboarding #1](https://youtu.be/-hZEO9sMm1s)
- [Smarter Developer Workflow Tutorial](https://youtu.be/XolFLX1u9Kg)

Works with Linux, Windows and macOS environments.

1. Verify project requirements: [Python 3.11](https://www.python.org/), [NPM](https://www.npmjs.com/) [Docker](https://www.docker.com/products/docker-desktop/), and [Docker Compose](https://docs.docker.com/compose/install/). Docker will need around 1 vCPU, 2Gib memory, and 30Gib of storage space.

2. Run `make` and add your credentials to the newly created `.env` file in the root of the repo.

3. Initialize, build and run the application locally.

```console
git clone https://github.com/QueriumCorp/smarter.git
make                # scaffold a .env file in the root of the repo
                    #
                    # ****************************
                    # STOP HERE!
                    # ****************************
                    # Add your credentials to .env located in the project root folder.
                    #
make python-init    # initialize Python virtual environment used for code auto-completion and linting
make docker-init    # initialize dev environment, build & init docker.
make docker-build   # builds and configures all docker containers
make docker-run     # runs all docker containers and starts a local web server http://127.0.0.1:8000/
```

_AWS Infrastructure Engineers: you additionally will need [AWS Account](https://aws.amazon.com/free/) and [CLI](https://aws.amazon.com/cli/) access, and [Terraform](https://www.terraform.io/). Make sure to eview and edit the master [Terraform configuration](./api/terraform/terraform.tfvars) file._

## Documentation

Detailed documentation for each endpoint is available here: [Documentation](./doc/examples/)

## Support

Please report bugs to the [GitHub Issues Page](https://github.com/QueriumCorp/smarter/issues) for this project.

## Developers

Please see:

- the [Developer Setup Guide](./doc/CONTRIBUTING.md)
- and these [commit comment guidelines](./doc/SEMANTIC_VERSIONING.md) 😬😬😬 for managing CI rules for automated semantic releases.

You can also contact [Lawrence McDaniel](https://lawrencemcdaniel.com/contact) directly.
