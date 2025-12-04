Architecture at a Glance
========================

- Docker-based Api and web console application that is designed to run
  both locally as well as natively on Kubernetes.
- YAML-first interface for managing AI resources that leverages a
  separately managed command-line interface that is similar in design to
  Kubernetes’ kubectl.
- Robust LLM tool call / function call extensibility mobile that
  facilitates no-code integrations to remote data sources like Sql
  databases and remote Api’s.
- Independent drop-in Chat UI written in React that works on any html
  web page via a simple 2-step DOM manipulation.
- Proprietary chat/agent REST Api to manage sessions between the Smarter
  Api backend and the Smarter Chat UI.
- A robust “batteries included” backend, with industrial strength
  security countermeasures for common Internet and web intrusion
  strategies including SQL injection, LLM prompt injection, cross-site
  request forgeries, brute force password attacks, distributed denial of
  service, cross-site scripting, clickjacking, host header corruptions.
- `Python-Django <https://www.djangoproject.com/>`__ web console
  **Prompt Engineer’s Workbench** for developing advanced LLM tool
  call-based extensions that leverage remote data sources and can be
  deployed to independent, custom domains.
- Sophsticated logging, content moderation.
- Team management features for granular control of AI resource
  ownership, api key access, and internal budgeting
- Configurable use-based internal billing features based on api calls as
  well as plugin usage.

The principal technologies in the **Smarter** platform stack include:

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

Running Locally
---------------

You can stand up a fully functional instance of the Smarter platform
using this 1-click approach,
`smarter-sh/smarter-deploy <https://github.com/smarter-sh/smarter-deploy>`__.
Review the README before you begin to ensure that your local development
environment meets all minimum requirements.

Running In Production
---------------------

Smarter is a cloud native platform written to run production workloads
in AWS Elastic Kubernetes Service, and optionally, any remote Sql
service and db engine that Django supports. Be aware that preparing the
AWS infrastructure is a non-trivial exercise that assumes you have
advanced knowledge of working with all of AWS’ basic low level services,
including

You are strongly recommended to use the following Smarter pre-configured
cloud deployment resources:

- Smarter Terraform scripts for AWS, located at
  `smarter-sh/smarter-infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`__
- `Smarter Helm
  Chart <https://artifacthub.io/packages/helm/project-smarter/smarter>`__
- `Smarter Docker
  Container <https://hub.docker.com/r/mcdaniel0073/smarter>`__
- The example `build <../.github/workflows/build.yml>`__ and
  `deploy <../.github/workflows/deploy.yml>`__ GitHub Actions workflows
  that manage the actual Smarter cloud platform,
  `platform.smarter.sh <https://platform.smarter.sh/dashboard/>`__

Command-Line Interface
----------------------

You need to install the Smarter CLI regardless of whether you’ve
installed Smarter locally or to a production environment. Smarter is a
yaml-first platform that works similarly to Kubernetes + Kubectl. You
manage Smarter AI resources with yaml manifests, and you’ll need Smarter
cli in order to ``apply`` these manifests. Downloads for all common
operating systems are available at
`smarter.sh/cli <https://smarter.sh/cli>`__. The source for the cli
(which you absolutely should never need under any circumstances, unless
you’re simply curious) is located at
`smarter-sh/smarter-cli <https://github.com/smarter-sh/smarter-cli>`__.

Python-Django
-------------

Most of Smarter is developed using Python’s Django web framework with
the following noteworthy additions:

- `Django-rest-knox <https://jazzband.github.io/django-rest-knox/>`__,
  used for creating secure, performant REST APIs.
- Django Celery. robust asynchronous compute layer using Celery, Redis
  and Kubernetes which can be leveraged for scheduled tasks like
  automated reports as well as real-time compute-intensive functions.
- `Pydantic <https://docs.pydantic.dev/latest/>`__, for extending
  Django’s settings module to facilitate CI-CD friendly
  `configuration <./smarter/common/README.md>`__ data from multiple
  sources: environment variable, terraform, Kubernetes secrets, Github
  Actions secrets, etc.
- `Pandas <https://pandas.pydata.org/>`__,
  `NumPy <https://numpy.org/>`__, `SciPy <https://scipy.org/>`__ and
  `Levenshtein <https://github.com/rapidfuzz/Levenshtein>`__
- OpenAI, GoogleAI, MetaAi, Anthropic and other compatible LLMs

ReactJS chat application
------------------------

The chat app in the dashboard sandbox is an independently managed NPM
React component, located here
`smarter-sh/smarter-chat <https://github.com/smarter-sh/smarter-chat>`__.

This React component is built substantially with
`Vite.js <https://github.com/smarter-sh/smarter>`__,
`@chatscope/chat-ui-kit-react <https://www.npmjs.com/package/@chatscope/chat-ui-kit-react>`__,
and
`react-pro-sidebar <https://www.npmjs.com/package/react-pro-sidebar>`__.

Django Integration
~~~~~~~~~~~~~~~~~~

Be aware that there are many considerations for getting React to work
inside a Django project. You are strongly recommended to review this
simple 2-step integration methodology that is used in the Smarter web
console,
`smarter-sh/web-integration-example <https://github.com/smarter-sh/web-integration-example>`__

Webapp design features
~~~~~~~~~~~~~~~~~~~~~~

- robust, highly customizable chat features
- A component model for implementing your own personalized OpenAI apps
- Skinnable UI for each app
- Includes default assets for each app
- Small compact code base
- Robust error handling for non-200 response codes from the custom REST
  API
- Handles direct text input as well as file attachments
- Info link to the OpenAI API official code sample
- Build-deploy managed with Vite

Smarter REST API
----------------

Api document is located here, `Smarter Docs -
Api <https://platform.smarter.sh/docs/api/>`__ and source code is
located here, `smarter/apps/api/ <../smarter/smarter/apps/api/>`__

Not to be confused with Smarter’s flagship product, customer-implemented
custom REST API’s, Smarter additionally has its own REST API, which is a
Python Django project implementing it’s proprietary Plugin model, along
with additional models for commercializing the service.

Minimum Developer Requirements
------------------------------

- 20Gib of available drive space
- MacOS: Version 12 (Monterey), Apple Silicon (M1 or newer) or Intel CPU
  with support for virtualization
- Windows: Windows 10 64-bit, 64-bit processor with Second Level Address
  Translation (SLAT), 8Gib of RAM, Windows Subsystem for Linux 2 if
  running Windows Home Editions.
- `git <https://git-scm.com/book/en/v2/Getting-Started-Installing-Git>`__.
  *pre-installed on Linux and macOS*
- `make <https://gnuwin32.sourceforge.net/packages/make.htm>`__.
  *pre-installed on Linux and macOS.*
- `Python 3.12 <https://www.python.org/downloads/>`__: for creating
  virtual environment used for building AWS Lambda Layer, and locally by
  pre-commit linters and code formatters.
- `Docker Desktop <https://docs.docker.com/desktop/>`__: for local
  development as well as the run-time environment. This also installs
  Docker Compose.

Cloud engineers:

- `AWS account <https://aws.amazon.com/>`__
- `AWS Command Line Interface <https://aws.amazon.com/cli/>`__
- `Terraform <https://www.terraform.io/>`__. *If you’re new to Terraform
  then see* `Getting Started With AWS and
  Terraform <https://github.com/smarter-sh/smarter-infrastructure/blob/main/doc/TERRAFORM_GETTING_STARTED_GUIDE.md>`__

Optional requirements:

- `OpenAI platform API key <https://platform.openai.com/>`__. *If you’re
  new to OpenAI API then see* `How to Get an OpenAI API
  Key <https://docs.smarter.sh/en/latest/integrations/openai-api-getting-started-guide.html>`__
- `Google Maps API
  key <https://developers.google.com/maps/documentation/geocoding/overview>`__.
  This is used the OpenAI API Function Calling coding example,
  “`get_weather() <https://platform.openai.com/docs/guides/function-calling>`__”.
- `Pinecone API key <https://docs.pinecone.io/docs/quickstart>`__. This
  is used for OpenAI API Embedding examples.
