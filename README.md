# Smarter

[![Python](https://a11ybadges.com/badge?logo=python)](https://www.python.org/)
[![Django](https://a11ybadges.com/badge?logo=django)](https://www.djangoproject.com/)<br>
[![Artifact Hub](https://img.shields.io/endpoint?url=https://artifacthub.io/badge/repository/project-smarter)](https://artifacthub.io/packages/search?repo=project-smarter)
[![Docker Pulls](https://img.shields.io/docker/pulls/mcdaniel0073/smarter.svg?logo=docker&label=DockerHub)](https://hub.docker.com/r/mcdaniel0073/smarter)
[![License: GNU AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)<br>
![Build Status](https://github.com/smarter-sh/smarter/actions/workflows/build.yml/badge.svg?branch=main)
![Release Status](https://github.com/smarter-sh/smarter/actions/workflows/deploy.yml/badge.svg?branch=main)
[![hack.d Lawrence McDaniel](https://img.shields.io/badge/hack.d-Lawrence%20McDaniel-orange.svg)](https://lawrencemcdaniel.com)

**Smarter is a platform for managing and orchestrating AI resources. This repo contains source code for the REST Api and the web console.**

- declarative manifest based resource management
- command-line interface for Windows, macOS, Linux and Docker
- rest api
- web console / prompt engineer workbench
- extensible: PyPi, NPM, VS Code Extension and more
- publicly accessible online documentation and self onboarding resources
- open source UI components for jump starting projects

**Smarter** is a yaml manifest-based approach to managing the disparate resources that are required for creating and managing AI resources that integrate to other enterprise resources like REST Api's and Sql databases. And it gives prompt engineering teams an intuitive workbench approach to designing, prototyping, testing, deploying and managing powerful AI resources for common corporate use cases including agentic workflows, customer facing chat solutions, and more. It includes a separately managed [React-based chat UI](https://github.com/smarter-sh/smarter-chat) that is compatible with a wide variety of front end ecosystems including NPM, Wordpress, Squarespace, Drupal, Office 365, Sharepoint, .Net, Netsuite, salesforce.com, and SAP. There is a [Golang command-line interface](https://github.com/smarter-sh/smarter-cli), and a [PyPi package](https://github.com/smarter-sh/smarter-python) for integrating the Api functions into your own Python projects. It is developed to support prompt engineering teams working in large organizations. Accordingly, **Smarter** provides common enterprise features such as credentials management, team workgroup management, role-based security, accounting cost codes, and logging and audit capabilities.

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

You can spin up the platform locally in Docker in around 10 minutes. Runs on Linux, Windows and macOS.

1. Verify project requirements: [Python 3.12](https://www.python.org/), [Docker](https://www.docker.com/products/docker-desktop/), and [Docker Compose](https://docs.docker.com/compose/install/).

2. Add your credentials to [.env](./docs/example-dot-env) in the root of this repo.

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

4. Login at http://localhost:8000/admin/login/ with user `admin` and password `smarter`.

See these onboarding videos:

- [Smarter Developer Onboarding #1](https://youtu.be/-hZEO9sMm1s)
- [Smarter Developer Workflow Tutorial](https://youtu.be/XolFLX1u9Kg)

## Smarter Helm Chart

Deploy Smarter API and web console to Kubernetes using the public Helm chart, available at [ghcr.io/smarter-sh/charts/smarter](https://ghcr.io/smarter-sh/charts/smarter) or [Artifact Hub](https://artifacthub.io/packages/helm/project-smarter/smarter).

### Quick Install

Pull the chart:

```console
helm pull oci://ghcr.io/smarter-sh/charts/smarter --version 0.7.6
```

Install to Kubernetes:

```console
helm upgrade --install smarter oci://ghcr.io/smarter-sh/charts/smarter \
  --namespace smarter \
  --create-namespace \
  --timeout 900s \
  --values values.yaml
```

### Configuration

See the [chart values.yaml](./helm/charts/smarter/values.yaml) for all available parameters, or view the [chart README](./helm/charts/smarter/README.md) for detailed configuration examples.

Minimum required configuration in your `values.yaml`:

```yaml
env:
  MYSQL_HOST: "your-mysql-host"
  MYSQL_DATABASE: "smarter"
  MYSQL_USER: "smarter_user"
  MYSQL_PASSWORD: "your-secure-password"
  OPENAI_API_KEY: "sk-..."
  SECRET_KEY: "your-django-secret-key"

  # Deployment
  DJANGO_SETTINGS_MODULE: "${{ env.DJANGO_SETTINGS_MODULE }}"
  ENVIRONMENT: "${{ inputs.environment }}"
  NAMESPACE: "${{ env.NAMESPACE }}"
  SMARTER_DOCKER_IMAGE: "${{ env.SMARTER_DOCKER_IMAGE }}"

  # AWS
  AWS_REGION: "${{ inputs.aws-region }}"
  AWS_ACCESS_KEY_ID: "${{ inputs.aws-access-key-id }}"
  AWS_SECRET_ACCESS_KEY: "${{ inputs.aws-secret-access-key }}"

  # Security
  FERNET_ENCRYPTION_KEY: "${{ inputs.fernet-encryption-key }}"
  SECRET_KEY: "${{ env.SECRET_KEY }}"

  # AI APIs
  OPENAI_API_KEY: "${{ inputs.openai-api-key }}"
  GOOGLE_MAPS_API_KEY: "${{ inputs.google-maps-api-key }}"
  GEMINI_API_KEY: "${{ inputs.gemini-api-key }}"
  LLAMA_API_KEY: "${{ inputs.llama-api-key }}"

  # Database
  MYSQL_HOST: "${{ env.MYSQL_HOST }}"
  MYSQL_PORT: "${{ env.MYSQL_PORT }}"
  MYSQL_DATABASE: "${{ env.SMARTER_MYSQL_DATABASE }}"
  MYSQL_USER: "${{ env.SMARTER_MYSQL_USERNAME }}"
  MYSQL_PASSWORD: "${{ env.SMARTER_MYSQL_PASSWORD }}"
  MYSQL_ROOT_USERNAME: "${{ env.MYSQL_ROOT_USERNAME }}"
  MYSQL_ROOT_PASSWORD: "${{ env.MYSQL_ROOT_PASSWORD }}"
  SMARTER_MYSQL_TEST_DATABASE_PASSWORD: "${{ inputs.smarter-mysql-test_database_password }}"

  # Admin
  SMARTER_LOGIN_URL: "${{ env.SMARTER_LOGIN_URL }}"
  SMARTER_ADMIN_PASSWORD: "${{ env.SMARTER_ADMIN_PASSWORD }}"
  SMARTER_ADMIN_USERNAME: "${{ env.SMARTER_ADMIN_USERNAME }}"
  SMARTER_ADMIN_EMAIL: "${{ env.SMARTER_ADMIN_EMAIL }}"

  # SMTP
  SMTP_HOST: "${{ env.SMTP_HOST }}"
  SMTP_PORT: "${{ env.SMTP_PORT }}"
  SMTP_USE_SSL: "${{ env.SMTP_USE_SSL }}"
  SMTP_USE_TLS: "${{ env.SMTP_USE_TLS }}"
  SMTP_USERNAME: "${{ env.SMTP_USERNAME }}"
  SMTP_PASSWORD: "${{ env.SMTP_PASSWORD }}"
```

## Documentation

Detailed documentation for this repo is available here: [Documentation](./docs/) and for the [overall platform here](https://platform.smarter.sh/docs/)

## Support

Please report bugs to the [GitHub Issues Page](https://github.com/smarter-sh/smarter/issues) for this project.

## Contributing

Please see the [CONTRIBUTING](./.github/CONTRIBUTING.md) page, the [project documentation](./docs/) and these tutorials:

- the [Developer Setup Guide](./CONTRIBUTING.md)
- this [Platform Architecture Summary](./docs/ARCHITECTURE.md)
- these [Good Coding Practices](./docs/GOOD_CODING_PRACTICE.md)
- this getting started guide for [12-factor Development Principals](./docs/12-FACTOR.md)
- these [git Commit Comment Guidelines](./docs/SEMANTIC_VERSIONING.md) 😬😬😬 for managing CI rules for automated semantic releases.

Contact: [Lawrence McDaniel](https://lawrencemcdaniel.com/contact)

![Lines of Code](https://cdn.platform.smarter.sh/github.com/smarter-sh/lines-of-code.png)
