# OpenAI Code Samples

[![OpenAI](https://a11ybadges.com/badge?logo=openai)](https://platform.openai.com/)
[![LangChain](https://a11ybadges.com/badge?text=LangChain&badgeColor=0834ac)](https://www.langchain.com/)
[![Amazon AWS](https://a11ybadges.com/badge?logo=amazonaws)](https://aws.amazon.com/)
[![ReactJS](https://a11ybadges.com/badge?logo=react)](https://react.dev/)
[![Python](https://a11ybadges.com/badge?logo=python)](https://www.python.org/)
[![Terraform](https://a11ybadges.com/badge?logo=terraform)](https://www.terraform.io/)<br>
[![12-Factor](https://img.shields.io/badge/12--Factor-Compliant-green.svg)](./doc/Twelve_Factor_Methodology.md)
![Unit Tests](https://github.com/QueriumCorp/smarter/actions/workflows/testsPython.yml/badge.svg?branch=main)
![GHA pushMain Status](https://img.shields.io/github/actions/workflow/status/QueriumCorp/smarter/pushMain.yml?branch=main)
![Auto Assign](https://github.com/QueriumCorp/smarter/actions/workflows/auto-assign.yml/badge.svg)
[![Release Notes](https://img.shields.io/github/release/QueriumCorp/smarter)](https://github.com/QueriumCorp/smarter/releases)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![hack.d Lawrence McDaniel](https://img.shields.io/badge/hack.d-Lawrence%20McDaniel-orange.svg)](https://lawrencemcdaniel.com)

A [React](https://react.dev/) + [Python-Django](https://www.djangoproject.com/) implementation of Querium's proprietary Plugin technology for [LLM function calling](https://www.promptingguide.ai/applications/function_calling).

## Quickstart

Works with Linux, Windows and macOS environments.

1. Verify project requirements: [AWS Account](https://aws.amazon.com/free/) and [CLI](https://aws.amazon.com/cli/) access, [Terraform](https://www.terraform.io/), [Python 3.11](https://www.python.org/), [NPM](https://www.npmjs.com/) and [Docker Compose](https://docs.docker.com/compose/install/).

2. Review and edit the master [Terraform configuration](./api/terraform/terraform.tfvars) file.

3. Run `make` and add your credentials to the newly created `.env` file in the root of the repo.

4. Initialize, build and run the application.

```console
git clone https://github.com/QueriumCorp/smarter.git
make        # scaffold a .env file in the root of the repo
            #
            # ****************************
            # STOP HERE!
            # ****************************
            # Add your credentials to .env
            #
make init   # initialize Terraform, Python virtual environment and NPM
make build  # deploy AWS cloud infrastructure, build ReactJS web app
make run    # run the web app locally in your dev environment
```

## ReactJS chat application

Complete source code and documentation is located [here](./client/).

React app that leverages [Vite.js](https://github.com/QueriumCorp/smarter), [@chatscope/chat-ui-kit-react](https://www.npmjs.com/package/@chatscope/chat-ui-kit-react), and [react-pro-sidebar](https://www.npmjs.com/package/react-pro-sidebar).

### Webapp Key features

- robust, highly customizable chat features
- A component model for implementing your own highly personalized OpenAI apps
- Skinnable UI for each app
- Includes default assets for each app
- Small compact code base
- Robust error handling for non-200 response codes from the custom REST API
- Handles direct text input as well as file attachments
- Info link to the OpenAI API official code sample
- Build-deploy managed with Vite

## Custom OpenAI REST API Backend

Source code is located [here](./smarter/)

A Python Django project implementing Querium's proprietary Plugin model, along with additional models for commercializing the service.

### API end points

- [/v0/chat/](./smarter/smarter/apps/api/urls.py)
- [/v0/chat/chatgpt/](./smarter/smarter/apps/api/urls.py)
- [/v0/chat/langchain/](./smarter/smarter/apps/api/urls.py)
- [/v0/account](./smarter/smarter/apps/account/urls.py)
- [/v0/account/users/](./smarter/smarter/apps/account/urls.py)
- [/v0/account/payment-methods/](./smarter/smarter/apps/account/urls.py)
- [/v0/plugins/](./smarter/smarter/apps/plugin/urls.py)
- [/v0/plugins/create](./smarter/smarter/apps/plugin/urls.py)
- [/v0/plugins/](./smarter/smarter/apps/plugin/urls.py)
- [/v0/api-auth/](./smarter/smarter/apps/api/urls.py)
- [/v0/api-auth/logout](./smarter/smarter/apps/api/urls.py)

### Design features

- [OpenAI API](https://pypi.org/project/openai/) library for Python. [LangChain](https://www.langchain.com/) enabled API endpoints where designated.
- [Pydantic](https://docs.pydantic.dev/latest/) based CI-CD friendly [Settings](./smarter/common/README.md) configuration class that consistently and automatically manages Python Lambda initializations from multiple sources including bash environment variables, `.env` and `terraform.tfvars` files.
- [Terraform](https://www.terraform.io/) fully automated and [parameterized](./api/terraform/terraform.tfvars) build. Usually builds your infrastructure in less than a minute.
- Secure: uses AWS role-based security and custom IAM policies. Best practice handling of secrets and sensitive data in all environments (dev, test, CI-CD, prod). Proxy-based API that hides your OpenAI API calls and credentials. Runs on https with AWS-managed SSL/TLS certificate.
- Excellent [documentation](./doc/)
- Runs on Kubernetes.

## Requirements

- [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git). _pre-installed on Linux and macOS_
- [make](https://gnuwin32.sourceforge.net/packages/make.htm). _pre-installed on Linux and macOS._
- [AWS account](https://aws.amazon.com/)
- [AWS Command Line Interface](https://aws.amazon.com/cli/)
- [Terraform](https://www.terraform.io/).
  _If you're new to Terraform then see [Getting Started With AWS and Terraform](./doc/TERRAFORM_GETTING_STARTED_GUIDE.md)_
- [OpenAI platform API key](https://platform.openai.com/).
  _If you're new to OpenAI API then see [How to Get an OpenAI API Key](./doc/OPENAI_API_GETTING_STARTED_GUIDE.md)_
- [Python 3.11](https://www.python.org/downloads/): for creating virtual environment used for building AWS Lambda Layer, and locally by pre-commit linters and code formatters.
- [NodeJS](https://nodejs.org/en/download): used with NPM for local ReactJS developer environment, and for configuring/testing Semantic Release.
- [Docker Compose](https://docs.docker.com/compose/install/): used by an automated Terraform process to create the AWS Lambda Layer for OpenAI and LangChain.

Optional requirements:

- [Google Maps API key](https://developers.google.com/maps/documentation/geocoding/overview). This is used the OpenAI API Function Calling coding example, "[get_current_weather()](https://platform.openai.com/docs/guides/function-calling)".
- [Pinecone API key](https://docs.pinecone.io/docs/quickstart). This is used for OpenAI API Embedding examples.

## Documentation

Detailed documentation for each endpoint is available here: [Documentation](./doc/examples/)

## Support

To get community support, go to the official [Issues Page](https://github.com/QueriumCorp/smarter/issues) for this project.

## Good Coding Best Practices

This project demonstrates a wide variety of good coding best practices for managing mission-critical cloud-based micro services in a team environment, namely its adherence to [12-Factor Methodology](./doc/Twelve_Factor_Methodology.md). Please see this [Code Management Best Practices](./doc/GOOD_CODING_PRACTICE.md) for additional details.

We want to make this project more accessible to students and learners as an instructional tool while not adding undue code review workloads to anyone with merge authority for the project. To this end we've also added several pre-commit code linting and code style enforcement tools, as well as automated procedures for version maintenance of package dependencies, pull request evaluations, and semantic releases.

## Contributing

Please see:

- the [Developer Setup Guide](./doc/CONTRIBUTING.md)
- and these [commit comment guidelines](./doc/SEMANTIC_VERSIONING.md) 😬😬😬 for managing CI rules for automated semantic releases.

You can also contact [Lawrence McDaniel](https://lawrencemcdaniel.com/contact) directly.
