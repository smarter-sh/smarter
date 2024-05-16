# Querium Smarter

[![OpenAI](https://a11ybadges.com/badge?logo=openai)](https://platform.openai.com/)
[![LangChain](https://a11ybadges.com/badge?text=LangChain&badgeColor=0834ac)](https://www.langchain.com/)
[![Amazon AWS](https://a11ybadges.com/badge?logo=amazonaws)](https://aws.amazon.com/)
[![Bootstrap](https://a11ybadges.com/badge?logo=bootstrap)](https://getbootstrap.com/)
[![ReactJS](https://a11ybadges.com/badge?logo=react)](https://react.dev/)
[![NPM](https://a11ybadges.com/badge?logo=npm)](https://www.npmjs.com/)
[![Python](https://a11ybadges.com/badge?logo=python)](https://www.python.org/)
[![Django](https://a11ybadges.com/badge?logo=django)](https://www.djangoproject.com/)
[![Terraform](https://a11ybadges.com/badge?logo=terraform)](https://www.terraform.io/)<br>
![Unit Tests](https://github.com/QueriumCorp/smarter/actions/workflows/test.yml/badge.svg?branch=main)
![Release Status](https://github.com/QueriumCorp/smarter/actions/workflows/release.yml/badge.svg?branch=main)
![Auto Assign](https://github.com/QueriumCorp/smarter/actions/workflows/auto-assign.yml/badge.svg)
[![Release Notes](https://img.shields.io/github/release/QueriumCorp/smarter)](https://github.com/QueriumCorp/smarter/releases)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![hack.d Lawrence McDaniel](https://img.shields.io/badge/hack.d-Lawrence%20McDaniel-orange.svg)](https://lawrencemcdaniel.com)

**Smarter provides highly skilled non-programmers with a means of creating uncharacteristically accurate and skilled chatbots, backed by their choice of LLM, and that are easy to manage, customizable, scalable, resilient, and secure.**

Smarter is an extensible web platform for developing knowledge domain specific generative AI text completion REST APIs. It provides users with a workbench approach to designing, prototyping, testing and deploying custom APIs in a standardized format that will be compatible with a wide variety of chatbot UIs for technology ecosystems such as NPM, Wordpress, Squarespace, Drupal, Office 365, .Net, salesforce.com, and SAP. It is developed for OEMs, and large business analyst & data science teams, and provides common enterprise features like security, accounting cost codes, and audit capabilities. Additionally It is envisioned being packaged and resold through large professional services firms and technology solutions providers.

## Smarter ChatBot APIs

The following collection of url endpoints are available to all Smarter chatbot, where `example` is the name of the chatbot. The chatbot sandbox React app and configuration api are available via these two url's, both of which require authentication and are only available to user associated with the Account to which the chatbot belongs.

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

## Logging

Logging and audit capabilities are one of Smarter's key strengths. Smarter logs every step of the chat completion workflow:

- prompt
- plugin selection
- presentation of prompt and selected plugins to the LLM
- initial response from the LLM
- function calling
- final request to the LLM
- final response from the LLM

Additionally, Smarter streams formatted text output to the console, viewable from the Smarter web console chat sandbox.

## Business Model

Smarter has a token-based costing model priced as a multiple of the "wholesale" cost of underlying LLM service providers like for example, OpenAI. Querium generates revenue by charging customers for use of the APIs that they deploy. Customers can manage multiple APIs for a broad range of use cases ranging from customer and sales support to human resources assistants.

Querium also generates revenues by offering three kinds of professional services:

1. Customer onboarding, technical training and go-live assistance.
2. Using Smarter to develop custom APIs for customers who lack in-house staff.
3. Technical support.

## Customer-facing features

- API developer workbench
- Instant toolbox-style access to a range of LLM providers
- A stand-in default web UI, which is the same React codebase that is used for the workbench
- Unlimited sets of expirable secret API keys that they can optionally add to their custom REST API's
- A yaml-based plugin feature that simplifies [LLM function calling](https://www.promptingguide.ai/applications/function_calling).
- Managed TLS/SSL certificate and DNS host records for custom API'S.
- Email and push notifications for customers' communication with their end users
- (PENDING) a context-sensitive news function. see [News API](https://newsapi.org/)
- (PENDING) function-calling for Stepwise API front end processor to preclassify math problems
- (PENDING) function-calling that processes common statistical and Newtonian functions to NumPy
- (PENDING) RAG pdf loader
- (PENDING) function calling that maps to Azure Cognitive Services [content moderation](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/)

### ChatBot API

Customers can deploy personalized ChatBots with a choice of domain. The default URL format is as follows.

- api: [user-defined-subdomain].####-####-####.api.smarter.sh/chatbot/
- webapp: [user-defined-subdomain].####-####-####.api.smarter.sh/chatbot/webapp/

Customers can optionally register a custom domain which typically can be verified and activated in around 4 hours.

## Developer Quickstart

Works with Linux, Windows and macOS environments.

1. Verify project requirements: [Python 3.11](https://www.python.org/), [NPM](https://www.npmjs.com/) [Docker](https://www.docker.com/products/docker-desktop/), and [Docker Compose](https://docs.docker.com/compose/install/). Docker will need around 1 vCPU, 2Gib memory, and 30Gib of storage space.

2. Run `make` and add your credentials to the newly created `.env` file in the root of the repo.

3. Initialize, build and run the application locally.

```console
git clone https://github.com/QueriumCorp/smarter.git
make         # scaffold a .env file in the root of the repo
             #
             # ****************************
             # STOP HERE!
             # ****************************
             # Add your credentials to .env located in the project
             # root folder.

make init    # initialize dev environment, build & init docker.
make build   # builds and configures all docker containers
make run     # runs all docker containers and starts a local web server http://127.0.0.1:8000/
```

_AWS Infrastructure Engineers: you additionally will need [AWS Account](https://aws.amazon.com/free/) and [CLI](https://aws.amazon.com/cli/) access, and [Terraform](https://www.terraform.io/). Make sure to eview and edit the master [Terraform configuration](./api/terraform/terraform.tfvars) file._

## Architecture at a glance

- Scalable serverless Kubernetes compute infrastructure that is largely self-maintaining.
- Countermeasures for common Internet and web intrusion strategies including SQL injection, cross-site request forgeries, brute force password attacks, distributed denial of service, cross-site scripting, clickjacking, host header corruptions. Additionally, Smarter goes to great pains to minimize its attack surface, primarily by only opening ports 80 and 443 to the public.
- [Python-Django](https://www.djangoproject.com/) customer web dashboard application for developing plugin-based API's deployed to custom domains.
- [LangChain](https://www.langchain.com/) managed LLM API requests. This provides a layer of abstraction between Smarter and underlying LLM vendor providers, and it also provides a simple means of standardizing Smarter customers' API format.
- React sandbox chat UI for prototyping pre-production APIs. Also works as a skinnable stand-in production UI if customers want this.
- customer api logging architecture implemented with Django models, signals and Celery tasks
- Team management features
- Configurable use-based billing features based on api calls as well as plugin usage.

### Python Django

Most of Smarter is developed using Python's Django web framework with the following noteworthy additions:

- [Django-rest-knox](https://jazzband.github.io/django-rest-knox/), used for creating secure, performant REST APIs.
- Django Celery. robust asynchronous compute layer using Celery, Redis and Kubernetes which can be leveraged for scheduled tasks like automated reports as well as real-time compute-intensive functions.
- [Pydantic](https://docs.pydantic.dev/latest/), for extending Django's settings module to facilitate CI-CD friendly [configuration](./smarter/common/README.md) data from multiple sources: environment variable, terraform, Kubernetes secrets, Github Actions secrets, etc.
- Pandas, NumPy, SciPy and Levenshtein
- OpenAI
- LangChain

### ReactJS chat application

The chat app in the dashboard sandbox is written in React. Complete source code and documentation is located [here](./smarter/smarter/apps/chatapp/reactapp/).

React app that leverages [Vite.js](https://github.com/QueriumCorp/smarter), [@chatscope/chat-ui-kit-react](https://www.npmjs.com/package/@chatscope/chat-ui-kit-react), and [react-pro-sidebar](https://www.npmjs.com/package/react-pro-sidebar).

#### Django Integration

Be aware that there are many considerations for getting React to work inside a Django project. You can read more [here](./doc/DJANGO-REACT-INTEGRATION.md).

#### Webapp design features

- robust, highly customizable chat features
- A component model for implementing your own highly personalized OpenAI apps
- Skinnable UI for each app
- Includes default assets for each app
- Small compact code base
- Robust error handling for non-200 response codes from the custom REST API
- Handles direct text input as well as file attachments
- Info link to the OpenAI API official code sample
- Build-deploy managed with Vite

### Smarter REST API

Source code is located [here](./smarter/)

Not to be confused with Smarter's flagship product, customer-implemented custom REST API's, Smarter additionally has its own REST API, which is a Python Django project implementing Querium's proprietary Plugin model, along with additional models for commercializing the service.

#### API end points

- [/v0/api-auth/](./smarter/smarter/apps/api/urls.py)
- [/v0/api-auth/logout](./smarter/smarter/apps/api/urls.py)
- [/v0/chat/](./smarter/smarter/apps/api/urls.py)
- [/v0/chat/chatgpt/](./smarter/smarter/apps/api/urls.py)
- [/v0/chat/langchain/](./smarter/smarter/apps/api/urls.py)
- [/v0/accounts](./smarter/smarter/apps/account/urls.py) - PENDING
- [/v0/accounts/<str:account_id>/payment-methods](./smarter/smarter/apps/account/urls.py)
- [/v0/account](./smarter/smarter/apps/account/urls.py)
- [/v0/accounts/users/](./smarter/smarter/apps/account/urls.py)
- [/v0/accounts/users/<str:username>/add-example-plugins](./smarter/smarter/apps/account/urls.py)
- [/v0/accounts/payment-methods/](./smarter/smarter/apps/account/urls.py)
- [/v0/plugins/](./smarter/smarter/apps/plugin/urls.py)
- [/v0/plugins/<int:plugin_id>](./smarter/smarter/apps/plugin/urls.py)
- [/v0/plugins/<int:plugin_id>/clone/<str:new_name>](./smarter/smarter/apps/plugin/urls.py)

## Requirements

- [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git). _pre-installed on Linux and macOS_
- [make](https://gnuwin32.sourceforge.net/packages/make.htm). _pre-installed on Linux and macOS._
- [Python 3.11](https://www.python.org/downloads/): for creating virtual environment used for building AWS Lambda Layer, and locally by pre-commit linters and code formatters.
- [NodeJS](https://nodejs.org/en/download): used with NPM for local ReactJS developer environment, and for configuring/testing Semantic Release.
- [Docker Compose](https://docs.docker.com/compose/install/): used by an automated Terraform process to create the AWS Lambda Layer for OpenAI and LangChain.

Cloud engineers:

- [AWS account](https://aws.amazon.com/)
- [AWS Command Line Interface](https://aws.amazon.com/cli/)
- [Terraform](https://www.terraform.io/).
  _If you're new to Terraform then see [Getting Started With AWS and Terraform](./doc/TERRAFORM_GETTING_STARTED_GUIDE.md)_

Optional requirements:

- [OpenAI platform API key](https://platform.openai.com/).
  _If you're new to OpenAI API then see [How to Get an OpenAI API Key](./doc/OPENAI_API_GETTING_STARTED_GUIDE.md)_
- [Google Maps API key](https://developers.google.com/maps/documentation/geocoding/overview). This is used the OpenAI API Function Calling coding example, "[get_current_weather()](https://platform.openai.com/docs/guides/function-calling)".
- [Pinecone API key](https://docs.pinecone.io/docs/quickstart). This is used for OpenAI API Embedding examples.

## Documentation

Detailed documentation for each endpoint is available here: [Documentation](./doc/examples/)

## Support

Please report bugs to the [GitHub Issues Page](https://github.com/QueriumCorp/smarter/issues) for this project.

## Good Coding Best Practices

This project demonstrates a wide variety of good coding best practices for managing mission-critical cloud-based micro services in a team environment, namely its adherence to [12-Factor Methodology](./doc/12-FACTOR.md). Please see this [Code Management Best Practices](./doc/GOOD_CODING_PRACTICE.md) for additional details.

We want to make this project more accessible to students and learners as an instructional tool while not adding undue code review workloads to anyone with merge authority for the project. To this end we've also added several pre-commit code linting and code style enforcement tools, as well as automated procedures for version maintenance of package dependencies, pull request evaluations, and semantic releases.

## Contributing

Please see:

- the [Developer Setup Guide](./doc/CONTRIBUTING.md)
- and these [commit comment guidelines](./doc/SEMANTIC_VERSIONING.md) 😬😬😬 for managing CI rules for automated semantic releases.

You can also contact [Lawrence McDaniel](https://lawrencemcdaniel.com/contact) directly.
