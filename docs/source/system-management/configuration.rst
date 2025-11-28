Configuration
===============

Smarter is a Docker-based Django web application and REST API that is highly configurable via environment variables, configuration files, and infrastructure-as-code templates.
This document outlines the various configuration options available for Smarter. The guidelines that follow assume that you are deploying Smarter using
the `recommended approach <installation.html>`_ of AWS EKS with the provided Helm chart and Terraform modules.

AWS Infrastructure Configuration
--------------------------------

See `Cloud Infrastructure <../system-management/cloud-infrastructure.html>`_ for details on configuring the necessary AWS resources using Smarter-supported Terraform modules.
The official Smarter Terraform modules favor simplicity, paradoxically making them conducive to customization.
You should be able to fork and modify these modules to suit your specific infrastructure requirements.

Django Settings
---------------

In certain cases, Smarter uses a `superseding singleton settings module <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/common/conf.py>`_ to establish configuration values.
This module leverages Pydantic to implement enhanced validation and type checking for configuration settings. You are **STRONGLY** recommended to avoid
modifying this module directly unless you are fully aware of the implications. Many of Smarter's configuration settings are programmatically derived from environment variables
set in the Docker container or Kubernetes pod. Modifying this logic can lead to unexpected behavior.

.. note::

  The superseding singleton settings module also leverages Pydantics' `SecretStr <https://docs.pydantic.dev/latest/api/types/#pydantic.types.SecretStr>`_ type
  to securely handle sensitive configuration values such as API keys, tokens, and passwords. This ensures that sensitive information is not inadvertently exposed in logs or error messages.

Usage:

.. code-block:: python

   from smarter.apps.common.conf import settings as smarter_settings

   print(smarter_settings.environment_cdn_domain)
   smarter_settings.dump()

In all other cases, Smarter uses standard Django settings located in `smarter/settings/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/settings>`_.
Django settings that can be overridden via environment variables are discoverable in `smarter/settings/base.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/settings/base.py>`_
and generally follow the form:

.. code-block:: python

   import os

   CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "False").lower() in ("true", "1", "t")

See `Django Settings <https://docs.djangoproject.com/en/5.2/ref/settings/>`_ for a comprehensive list of Django settings that can be configured in Smarter.

To the extent that you find a given Django settings variable initialized in this manner, you'll be able to override
it by setting the corresponding environment variables in your deployment configuration.

Asynchronous Task Queue Configuration
-------------------------------------

Smarter uses Celery as its asynchronous task queue. Celery configuration settings can be found in `smarter/settings/celery.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/settings/celery.py>`_.
Celery relies on a message broker and result backend, both of which can be configured via environment variables. By default, Smarter is configured to use Redis as both the message broker and result backend.
This is known to work well for most use cases. However, you can configure Celery to use other brokers and backends as needed.

**If you are not running at scale then the default Celery configuration should suffice.**

See `Celery configuration <https://github.com/smarter-sh/smarter/blob/alpha/smarter/smarter/workers/celery.py>`_ for more details on how Celery is configured in Smarter.

Beat Scheduler Configuration
----------------------------

Smarter uses Celery Beat to schedule periodic tasks. The Beat scheduler configuration can be found in `smarter/settings/celery.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/settings/celery.py>`_.
Like asynchronous task queue configuration, the Beat scheduler relies on the same message broker and result backend as Celery.

See `Celery Beat configuration <https://github.com/smarter-sh/smarter/blob/alpha/smarter/smarter/workers/celery.py>`_ for more details on how Celery Beat is configured in Smarter.

Helm Chart Configuration
------------------------

The Smarter cloud platform is deployed using the official Helm chart. Configuration options for this Helm chart can be found
in the `values.yaml <https://github.com/smarter-sh/smarter/blob/alpha/helm/charts/smarter/values.yaml>`_ file. Additional
documentation on this Helm chart can be found in the `Helm Chart Documentation <https://artifacthub.io/packages/helm/project-smarter/smarter>`_.

Dockerfile Configuration
------------------------

The official Docker container image for Smarter (`hub.docker.com/r/mcdaniel0073/smarter <https://hub.docker.com/r/mcdaniel0073/smarter>`_) is
built using the `Dockerfile <https://github.com/smarter-sh/smarter/blob/main/Dockerfile>`_ from the main branch of Smarter's main code
repository, `https://github.com/smarter-sh/smarter <https://github.com/smarter-sh/smarter>`_.

This Docker image favors simplicity over configurability, hence, there are limited configuration options.


GitHub Actions Secrets Configuration
-------------------------------------

If you intend to use the provided GitHub Actions workflows for CI/CD, you will need to a.) fork the repository, and b.) configure several GitHub Secrets in your repository.
See `GitHub Actions CI/CD <../development/ci-cd.html>`_ for details on the required secrets and their configuration.

See `GitHub Secrets Configuration <https://github.com/smarter-sh/smarter/settings/secrets/actions>`_ for the list of currently configured GitHub Secrets in the main Smarter repository.

.. list-table:: **GitHub Actions Secrets Reference**
   :header-rows: 1

   * - Secret Name
     - Description
   * - AWS_ACCESS_KEY_ID
     - AWS access key for CI/CD and deployment automation
   * - AWS_REGION
     - AWS region for resource provisioning
   * - AWS_SECRET_ACCESS_KEY
     - AWS secret access key for CI/CD and deployment automation
   * - FERNET_ENCRYPTION_KEY
     - Key for encrypting/decrypting Pydantic Secrets data in smarter_settings
   * - GEMINI_API_KEY
     - API key for Gemini AI integrations
   * - GOOGLE_AI_STUDIO_KEY
     - API key for Google AI Studio services
   * - GOOGLE_MAPS_API_KEY
     - API key for Google Maps integrations (for getweather() LLM tool)
   * - GOOGLE_SERVICE_ACCOUNT_B64
     - Base64-encoded Google service account credentials
   * - LLAMA_API_KEY
     - API key for Llama AI integrations
   * - MAILCHIMP_API_KEY
     - (optional) API key for Mailchimp email services
   * - MAILCHIMP_LIST_ID
     - (optional) Mailchimp audience/list ID
   * - OPENAI_API_KEY
     - API key for OpenAI integrations
   * - PAT
     - Personal Access Token for GitHub or other services
   * - PINECONE_API_KEY
     - (optional) API key for Pinecone vector database
   * - PINECONE_ENVIRONMENT
     - (optional) Pinecone environment name
   * - SMARTER_MYSQL_TEST_DATABASE_PASSWORD
     - Password for MySQL test database
   * - SMTP_PASSWORD
     - SMTP server password for outgoing email
   * - SMTP_USERNAME
     - SMTP server username for outgoing email
   * - SOCIAL_AUTH_GITHUB_KEY
     - OAuth client ID for GitHub social login
   * - SOCIAL_AUTH_GITHUB_SECRET
     - OAuth client secret for GitHub social login
   * - SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
     - OAuth client ID for Google social login
   * - SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET
     - OAuth client secret for Google social login
   * - SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY
     - OAuth client ID for LinkedIn social login
   * - SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET
     - OAuth client secret for LinkedIn social login
