# Smarter

[![Python](https://a11ybadges.com/badge?logo=python)](https://www.python.org/)
[![Django](https://a11ybadges.com/badge?logo=django)](https://www.djangoproject.com/)<br>
![Release Status](https://github.com/smarter-sh/smarter/actions/workflows/deploy.yml/badge.svg?branch=main)
![Auto Assign](https://github.com/smarter-sh/smarter/actions/workflows/auto-assign.yml/badge.svg)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![hack.d Lawrence McDaniel](https://img.shields.io/badge/hack.d-Lawrence%20McDaniel-orange.svg)](https://lawrencemcdaniel.com)

**Smarter is a platform for managing and orchestrating AI resources.**

- declarative manifest based resource management
- command-line interface for Windows, macOS, Linux and Docker
- rest api
- web console / prompt engineer workbench
- extensible: PyPi, NPM, VS Code Extension and more
- publicly accessible online documentation and self onboarding resources
- open source UI components for jump starting projects

**Smarter** is the best way to manage the disparate resources that are required for creating and managing AI resources integrate to other enterprise resources like REST Api's and Sql databases. And it gives prompt engineering teams an intuitive workbench approach to designing, prototyping, testing, deploying and managing powerful AI resources for common corporate use cases including agentic workflows, customer facing chat solutions, and more. It is compatible with a wide variety of chatbot UI front ends for technology ecosystems including NPM, Wordpress, Squarespace, Drupal, Office 365, Sharepoint, .Net, Netsuite, salesforce.com, and SAP. It is developed to support prompt engineering teams working in large organizations. Accordingly, **Smarter** provides common enterprise features such as credentials management, team workgroup management, role-based security, accounting cost codes, and logging and audit capabilities.

**Smarter** provides seamless integration and interoperation between LLMs from DeepSeek, Google AI, Meta AI and OpenAI. It is LLM provider-agnostic, and provides seamless integrations to a continuously evolving list of value added services for security management, prompt content moderation, audit, cost accounting, and workflow management. **Smarter** is cloud native and runs on Kubernetes, on-site in your data center or in the cloud.

**Smarter** is cost effective when running at scale. It is extensible and architected on the philosophy of a compact core that does not require customization nor forking. It is horizontally scalable. It is natively multi-tenant, and can be installed alongside your existing systems. The principal technologies in the **Smarter** platform stack include:

- Amazon Web Services
- Debian, Ubuntu or Amazon Linux
- Docker/Kubernetes/Helm
- MySQL
- Redis
- Terraform/awscli/Boto3
- Python/Django
- Pytest/Pluggy
- Pydantic/Pandas/NumPy
- react.js
- Bootstrap
- Go lang
- GitHub Actions

## Quickstart

You can spin up the platform locally in Docker in around 10 minutes. Works with Linux, Windows and macOS.

1. Verify project requirements: [Python 3.12](https://www.python.org/), [Docker](https://www.docker.com/products/docker-desktop/), and [Docker Compose](https://docs.docker.com/compose/install/).

2. Run `make` and add your credentials to the newly created `.env` file in the root of the repo.

3. Initialize, build and run the application locally.

```console
git clone https://github.com/smarter-sh/smarter.git
make                # scaffold a .env file in the root of the repo
                    #
                    # ****************************
                    # STOP HERE!
                    # ****************************
                    # Add your credentials to .env located in the project root folder.
                    #
make init           # initialize Python virtual environment, build the Docker container, and seed the platform with test data
make docker-run     # runs all docker containers and starts a local web server http://127.0.0.1:8000/
```

See these onboarding videos:

- [Smarter Developer Onboarding #1](https://youtu.be/-hZEO9sMm1s)
- [Smarter Developer Workflow Tutorial](https://youtu.be/XolFLX1u9Kg)

## Local Development Minimum Requirements

- 4 cpu cores + 8Gib RAM + Internet access
- terminal access
- Docker or Docker Desktop + Docker Compose
- Python 3.12
- Node 20.x
- Any code editor

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

## Documentation

Detailed documentation for each endpoint is available here: [Documentation](./docs/examples/)

## Support

Please report bugs to the [GitHub Issues Page](https://github.com/smarter-sh/smarter/issues) for this project.

## Contributing

Please see the [project documentation](./docs/) and these tutorials:

- the [Developer Setup Guide](./CONTRIBUTING.md)
- this [Platform Architecture Summary](./docs/ARCHITECTURE.md)
- these [Good Coding Practices](./docs/GOOD_CODING_PRACTICE.md)
- this getting started guide for [12-factor Development Principals](./docs/12-FACTOR.md)
- these [git Commit Comment Guidelines](./docs/SEMANTIC_VERSIONING.md) 😬😬😬 for managing CI rules for automated semantic releases.

Contact: [Lawrence McDaniel](https://lawrencemcdaniel.com/contact)

![Lines of Code](https://cdn.platform.smarter.sh/github.com/smarter-sh/lines-of-code.png)
