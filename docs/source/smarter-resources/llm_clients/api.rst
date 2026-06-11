API Reference
===================

.. toctree::
   :maxdepth: 1

   api/views

LLMClient’s are accessible via REST API. End points to deployed LLMClients
are publicly accessible unless the customer has chosen to attach a
Smarter API key. Http requests should substantially conform this command
structure:

.. code:: console

   curl --location 'https://example.3141-5926-5359.api.example.com/llm-client/' \
   --header 'x-api-key: api-key-string-of-around-64-hashed-characters' \
   --header 'Content-Type: application/json' \
   --data '{
       "messages": [
           {
               "role": "user",
               "content": "what is FMLA?"
           }
       ],
       "prompt_history": [
           {
               "message": "Hello, How can I help you?",
               "direction": "incoming",
               "sentTime": "11/16/2023, 5:53:32 PM",
               "sender": "system"
           }
       ]
   }'

LLMClients can also run in pre-production ‘sandbox’ mode from inside the
Smarter web console.

Management
----------

There are Django ``manage.py`` commands for the complete LLMClient
lifecycle, namely, for deploying the LLMClient so that it can begin
receiving and responding to http requests. To access ``manage.py``
you’ll need ssh access to the Smarter Bastion server, a managed Ubuntu
Linux AWS EC2 instance that is pre-configured connect to the Kubernetes
cluster via an ASCII gui application named `k9s <https://k9scli.io/>`__.
From k9s you can navigate to any running ‘smarter’ application pod,
whereupon you access a bash shell.

Contact Lawrence McDaniel (lpm0073@gmail.com) if you need Smarter
Bastion server access.

Features are continuously added to the Smarter web console, with the
mid-term goal of deploying a minimal UX that gives customers autonomy to
manage all aspects of a LLMClient. Meanwhile, there’s Django Admin to
cover any functionality gaps.

Domain Name Resolution
----------------------

The Smarter application stack provides consistent behavior for either of
three different domain name styles

- Default LLMClient domain names:
  [subdomain].[####-####-####].[environment].smarter.sh/llm-client/
- Customer’s custom domain names: [subdomain].example.com/llm-client/
- The Smarter API: /api/v0/llm-clients/[int]/[LLMClient.name]

Secondarily, it also gracefully adapts to alternatives like
``localhost``, ``127.0.0.1`` and any host names that are conjured up in
unit tests.

URL Parsing and Routing
~~~~~~~~~~~~~~~~~~~~~~~

In light of the multiple naming schemes, mapping hosts and urls to a
LLMClient is not trivial. Note the following code resources for working
with llm_client urls:

- ``smarter.apps.llm_client.models.LLMClientHelper``: Maps a url to its
  LLMClient, Plugin list, Account and User objects.
- ``smarter.lib.django.validators.SmarterValidator``: Low-level url
  parsing features.
- ``smarter.common.conf.settings``: A singleton that provides settings
  values for the environment and base customer API domains.

Default Domain
~~~~~~~~~~~~~~

The default domain for each LLMClient is accessible regardless of whether
the customer has also implemented a custom domain.

example: https://example.3141-5926-5359.beta.api.example.com/llm-client/

where

- ``'example' == LLMClient.name``
- ``'3141-5926-5359' == LLMClient.account.account_number``
- ``'beta.api.example.com' == smarter_settings.customer_api_domain``
- ``/llm-client/`` is a URL endpoint defined in smarter/urls.py and
  resolves to a Django View that invokes Chat with an Account object and
  a List of Smarter Plugin objects.

Custom Domain
~~~~~~~~~~~~~

Customers can optionally configure a custom domain for their account,
mapping individual llm_clients to DNS subdomain records aliased to the
master Kubernetes ingress controller for the platform. Smarter provides
``manage.py`` admin commands for managing the complete lifecycle of
customer custom domain resources.

example: https://sales.api.example.com/llm-client/ where

- ``'api.example.com == llm_client.custom_domain'`` is a LLMClientCustomDomain
  object
- ``'sales'`` is a verified A record (ie a subdomain) in the AWS Hosted
  zone for the customer domain
- ``LLMClientCustomDomain.is_verified == True``. An asynchronous task
  verifies the domain NS records.
- ``/llm-client/`` is the same URL endpoint used by default domains.

When using a custom domain,
``LLMClient.hostname == LLMClient.custom_domain`` once the following
conditions are satisfied:

- ``LLMClientCustomDomain.is_verified == True``. An asynchronous task
  verifies the domain NS records.
- ``LLMClient.deployed==True``. This is a customer-managed setting.

Django Application Configuration
--------------------------------

There are multiple Django configuration implications to the API domain
naming conventions outlined in this document. These require
customizations to url routing within Django, as well as customizing
management of ``ALLOWED_HOSTS``, CORS, CSRF, ssl-certificates, and
multiple kinds of Kubernetes resources.

ALLOWED_HOSTS
~~~~~~~~~~~~~

For Django to accept http requests from a domain, it must be included in
Django’s ``ALLOWED_HOSTS`` setting which is managed by Django middleware
that we’ve subclassed as
``smarter.apps.llm_client.middleware.security.SmarterSecurityMiddleware`` in order
to append API domain names to ``ALLOWED_HOSTS`` at run time.

CORS
~~~~

We subclassed the standard ``corsheaders`` as
``smarter.apps.llm_client.middleware.cors.SmarterCorsMiddleware`` in order to
performantly append API domain names to ``CORS_ALLOWED_ORIGINS`` at run
time..

Cross-Site Request Forgery
~~~~~~~~~~~~~~~~~~~~~~~~~~

We subclassed Django’s csrf library as
``smarter.apps.llm_client.middleware.csrf.SmarterCsrfViewMiddleware`` in order to
append API domain names to ``CSRF_TRUSTED_ORIGINS`` at run time.

TLS/SSL Certificates
~~~~~~~~~~~~~~~~~~~~

The certificates issued and managed by ``cert-manager`` in Kubernetes
for each environment only support the first level of subdomain,
implemented as a wildcard. For example, ``*.beta.api.example.com``.
Therefore, API domains like for example,
``example.3141-5926-5359.api.example.com``, fall outside of this scheme.
Smarter therefore implements asynchronous tasks for creating
per-customer and per-llm_client certificates and the requisite DNS TXT
challenge records.

Kubernetes Ingresses
~~~~~~~~~~~~~~~~~~~~

Similarly, we also have to create an individual Ingress resource for
each API domain.

AWS Hosted Zones
~~~~~~~~~~~~~~~~

Custom API domain names require a dedicated AWS Hosted Zone in order to
generate the NS records. Note that customers are responsible for adding
the NS records to the DNS host for their root domain name.
