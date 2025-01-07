# Smarter Architecture at a glance

- Scalable serverless Kubernetes compute infrastructure that is largely self-maintaining.
- Countermeasures for common Internet and web intrusion strategies including SQL injection, cross-site request forgeries, brute force password attacks, distributed denial of service, cross-site scripting, clickjacking, host header corruptions. Additionally, Smarter goes to great pains to minimize its attack surface, primarily by only opening ports 80 and 443 to the public.
- [Python-Django](https://www.djangoproject.com/) customer web dashboard application for developing plugin-based API's deployed to custom domains.
- [LangChain](https://www.langchain.com/) managed LLM API requests. This provides a layer of abstraction between Smarter and underlying LLM vendor providers, and it also provides a simple means of standardizing Smarter customers' API format.
- React sandbox chat UI for prototyping pre-production APIs. Also works as a skinnable stand-in production UI if customers want this.
- customer api logging architecture implemented with Django models, signals and Celery tasks
- Team management features
- Configurable use-based billing features based on api calls as well as plugin usage.

## Python Django

Most of Smarter is developed using Python's Django web framework with the following noteworthy additions:

- [Django-rest-knox](https://jazzband.github.io/django-rest-knox/), used for creating secure, performant REST APIs.
- Django Celery. robust asynchronous compute layer using Celery, Redis and Kubernetes which can be leveraged for scheduled tasks like automated reports as well as real-time compute-intensive functions.
- [Pydantic](https://docs.pydantic.dev/latest/), for extending Django's settings module to facilitate CI-CD friendly [configuration](./smarter/common/README.md) data from multiple sources: environment variable, terraform, Kubernetes secrets, Github Actions secrets, etc.
- Pandas, NumPy, SciPy and Levenshtein
- OpenAI
- LangChain

## ReactJS chat application

The chat app in the dashboard sandbox is written in React. Complete source code and documentation is located [here](./smarter/smarter/apps/chatapp/reactapp/).

React app that leverages [Vite.js](https://github.com/QueriumCorp/smarter), [@chatscope/chat-ui-kit-react](https://www.npmjs.com/package/@chatscope/chat-ui-kit-react), and [react-pro-sidebar](https://www.npmjs.com/package/react-pro-sidebar).

### Django Integration

Be aware that there are many considerations for getting React to work inside a Django project. You can read more [here](./doc/DJANGO-REACT-INTEGRATION.md).

### Webapp design features

- robust, highly customizable chat features
- A component model for implementing your own highly personalized OpenAI apps
- Skinnable UI for each app
- Includes default assets for each app
- Small compact code base
- Robust error handling for non-200 response codes from the custom REST API
- Handles direct text input as well as file attachments
- Info link to the OpenAI API official code sample
- Build-deploy managed with Vite

## Smarter REST API

Source code is located [here](./smarter/)

Not to be confused with Smarter's flagship product, customer-implemented custom REST API's, Smarter additionally has its own REST API, which is a Python Django project implementing Querium's proprietary Plugin model, along with additional models for commercializing the service.

### API end points

- [/v1/api-auth/](./smarter/smarter/apps/api/urls.py)
- [/v1/api-auth/logout](./smarter/smarter/apps/api/urls.py)
- [/v1/chats/](./smarter/smarter/apps/api/urls.py)
- [/v1/chats/chatgpt/](./smarter/smarter/apps/api/urls.py)
- [/v1/chats/langchain/](./smarter/smarter/apps/api/urls.py)
- [/v1/accounts](./smarter/smarter/apps/account/urls.py) - PENDING
- [/v1/accounts/<str:account_id>/payment-methods](./smarter/smarter/apps/account/urls.py)
- [/v1/account](./smarter/smarter/apps/account/urls.py)
- [/v1/accounts/users/](./smarter/smarter/apps/account/urls.py)
- [/v1/accounts/users/<str:username>/add-example-plugins](./smarter/smarter/apps/account/urls.py)
- [/v1/accounts/payment-methods/](./smarter/smarter/apps/account/urls.py)
- [/v1/plugins/](./smarter/smarter/apps/plugin/urls.py)
- [/v1/plugins/<int:plugin_id>](./smarter/smarter/apps/plugin/urls.py)
- [/v1/plugins/<int:plugin_id>/clone/<str:new_name>](./smarter/smarter/apps/plugin/urls.py)

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
