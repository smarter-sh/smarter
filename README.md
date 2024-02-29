# Querium Smarter

[![OpenAI](https://a11ybadges.com/badge?logo=openai)](https://platform.openai.com/)
[![LangChain](https://a11ybadges.com/badge?text=LangChain&badgeColor=0834ac)](https://www.langchain.com/)
[![Amazon AWS](https://a11ybadges.com/badge?logo=amazonaws)](https://aws.amazon.com/)
[![ReactJS](https://a11ybadges.com/badge?logo=react)](https://react.dev/)
[![Python](https://a11ybadges.com/badge?logo=python)](https://www.python.org/)
[![Django](https://a11ybadges.com/badge?logo=django)](https://www.djangoproject.com/)
[![Terraform](https://a11ybadges.com/badge?logo=terraform)](https://www.terraform.io/)<br>
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

The chat app in the dashboard sandbox is written in React. Complete source code and documentation is located [here](./smarter/smarter/apps/chatapp/reactapp/).

React app that leverages [Vite.js](https://github.com/QueriumCorp/smarter), [@chatscope/chat-ui-kit-react](https://www.npmjs.com/package/@chatscope/chat-ui-kit-react), and [react-pro-sidebar](https://www.npmjs.com/package/react-pro-sidebar).

### Django Integration

There are several considerations for getting React to work inside a Django project. Please note the following:

- **Django Template Configuration.** Django template engine needs to know how to find React-rendered html templates. Note that React's builds are generated in a subfolder named `dist` and that it's `index.html` entry point file contains links to auto-generated css and js bundles, meaning that the rendered index.html is specific to the resources in the build that generated it, and it therefore cannot be generalized/templated. We therefore need a way to gracefully enable Django's templating engine to 'discover' these apps in whichever Django apps they might exist, so that these files can be served by Django templates as-is. To this end we've created a custom React [template loader](./smarter/smarter/template_loader.py) and a 2nd template engine located in [base.py](./smarter/smarter/settings/base.py) that reference the custom loader. We additionally created this custom [base template](./smarter/smarter/templates//smarter/base_react.html) for React that ensures that React's `<div id="root"></div>` DOM element and it's js entry point bundle are correctly placed with the DOM.
- **React App configuration**
  - placement within folder structure. The React app was scaffolded with ViteJS and is added to the Django app [chatapp](./smarter/smarter/apps/chatapp/reactapp/).
  - vite.config.ts. Note that a.) Django's collectstatic procedure must be able to discover the existence of React builds, and that b.) The url scheme in the React-generated templates need to account for how Django serves static assets in both dev and production environments. We leverage the vite.config.ts resource to prefix all paths with whatever path we've decided in Django settings for serving static assets.
  - index.html. The original [index.html](./smarter/smarter/apps/chatapp/reactapp/index.html) created by Vite is completely replaced by a django template that a.) inherits our custom base_react.html template, b.) contains Django template blocks to ensure correct placement of React's elements within the DOM.
- **Backend integration via template context.** The React app interacts with the backend via a REST API implemented with Django REST Framework. But we have to provide the app with the correct, environment-specific url for this API during app startup, along with other similar stateful data. We therefore need a way to pass a small set of data to React via the Django template which invokes it. We created a custom [Django template context](./smarter/smarter/apps/dashboard/context_processors.py) that generates this data, and a [Django base template](./smarter/smarter/templates/smarter/base_react.html) that converts it into a javascript element placed in the DOM, which is then [consumed by the React app](./smarter/smarter/apps/chatapp/reactapp/src/config.js) at startup as a const. Note that the custom React context processor is added to the custom React template engine, described above.

#### vite.config.ts

Note the addition of `/static/`:

```javascript
export default defineConfig({
  plugins: [react()],
  base: "/static/",
  build: {
    sourcemap: true,
  },
});
```

#### React index.html template

The original index.html created by Vite is replaced with this Django template. Note that this template is first processed by React's build process, which will convert the `main.jsx` reference to an actual js bundle filename. And then afterwards, Django's collectstatic procedure will copy the dist folder contents to the staticfiles folder, to be served by Django's static asset server.

```django
{% extends "smarter/base_react.html" %}

{% block canonical %}
<link rel="canonical" href="/chatapp/" />
{% endblock %}

{% block react_javascript %}
  {{ block.super }}
  <script type="module" src="/src/main.jsx"></script>
{% endblock %}
```

#### Django context generation

```python
def react(request):
  """
  React context processor for all templates that render
  a React app.
  """
  base_url = f"{request.scheme}://{request.get_host}"
  return {
      "react": True,
      "react_config": {"BASE_URL": base_url, "API_URL": f"{base_url}/api/v0", "CHAT_ID": "SET-ME-PLEASE"},
  }
```

#### Django TEMPLATES settings

We created this second template engine that is customized for React.

```python
  {
      "NAME": "react",
      "BACKEND": "django.template.backends.django.DjangoTemplates",
      "DIRS": [
          BASE_DIR / "templates",
      ],
      "APP_DIRS": False,
      "OPTIONS": {
          "loaders": [
              "smarter.template_loader.ReactAppLoader",
              "django.template.loaders.filesystem.Loader",
          ],
          "context_processors": [
              "smarter.apps.dashboard.context_processors.react",
              "django.template.context_processors.request",
              #
              # other context processors ...
              #
          ],
      },
  },
```

### Django base template setup

The Django templating code:

```django
{% block react_javascript %}
  {{ block.super }}
  {{ react_config|json_script:'react-config' }}
{% endblock %}
```

Which will render a DOM element like the following:

```html
<script id="react-config" type="application/json">
  {
    "BASE_URL": "http://127.0.0.1:8000",
    "API_URL": "http://127.0.0.1:8000/api/v0",
    "CHAT_ID": "SET-ME-PLEASE"
  }
</script>
```

#### React app consumption

The DOM element can be consumed by JS/React like this:

```javascript
export const REACT_CONFIG = JSON.parse(
  document.getElementById("react-config").textContent,
);
```

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

### Design features

- [OpenAI API](https://pypi.org/project/openai/) library for Python. [LangChain](https://www.langchain.com/) enabled API endpoints where designated.
- [Pydantic](https://docs.pydantic.dev/latest/) based CI-CD friendly [Settings](./smarter/common/README.md) configuration class that consistently and automatically manages Python Lambda initializations from multiple sources including bash environment variables, `.env` and `terraform.tfvars` files.
- [Terraform](https://www.terraform.io/) fully automated and [parameterized](./api/terraform/terraform.tfvars) build. Usually builds your infrastructure in less than a minute.
- Secure: uses AWS role-based security and custom IAM policies. Best practice handling of secrets and sensitive data in all environments (dev, test, CI-CD, prod). Proxy-based API that hides your OpenAI API calls and credentials. Runs on https with AWS-managed SSL/TLS certificate.
- Excellent [documentation](./doc/)
- Token-based authentication using [Django-rest-knox](https://jazzband.github.io/django-rest-knox/) <-- PENDING
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
