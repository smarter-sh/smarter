Smarter Custom Domain
=====================

Overview
--------

A Smarter **CustomDomain** serves :doc:`LLMClients <smarter-llmclient>` from a domain name of your
own, such as ``customer-service-bot.example.com``, rather than from the platform's default domain. Like every
other Smarter resource, a CustomDomain is declared in a manifest, is owned by the user who applies
it, and is shared with the user's account.

Smarter hosts a CustomDomain in an AWS Route53 hosted zone, with a TLS certificate. Once you add
the hosted zone's NS records to your root domain's DNS settings, Smarter verifies the domain, and
the LLMClients that use it are reachable at ``https://<llmclient-name>.<domain-name>``.

How It Works
------------

A CustomDomain is managed with the ``smarter`` CLI, and in the web console's Custom Domains page:

.. code-block:: console

    smarter apply -f custom-domain.yaml
    smarter deploy customdomain example_custom_domain
    smarter describe customdomain example_custom_domain
    smarter get customdomains
    smarter delete customdomain example_custom_domain

- ``apply`` creates, or updates, the CustomDomain. Its ``domainName`` can be changed until the
  domain is registered.
- ``deploy`` registers the domain with AWS: Smarter creates its Route53 hosted zone and its TLS
  certificate, in the background. ``describe`` then reports the hosted zone, and the DNS records to
  add to your root domain's DNS settings, in ``status``.
- ``delete`` deletes the Smarter resource, but not its Route53 hosted zone. A CustomDomain that an
  LLMClient uses cannot be deleted: deleting it would delete the LLMClient.

The web console's Custom Domains page lists your own CustomDomains, and those shared with you, and
clones, renames and deletes them.

The Manifest
------------

.. code-block:: yaml

    apiVersion: smarter.sh/v1
    kind: CustomDomain
    metadata:
      name: example_custom_domain
      description: Serves the company's LLMClients from llmclients.example.com.
      version: 1.0.0
    spec:
      config:
        domainName: llmclients.example.com

``status`` is read only. Besides the owner, it reports ``awsHostedZoneId``, ``dnsRecords``, the
verification fields below, and, in ``dependencies``, the LLMClient that uses the CustomDomain.

Verification
------------

After ``deploy``, Smarter checks the domain every 30 minutes, for up to 24 hours, and emails the
owner the result. ``status.verificationStatus`` is ``Not Verified``, ``Verifying``, ``Verified`` or
``Failed``, and the web console's Custom Domains page shows it as a badge. A CustomDomain is
**Verified**, at ``status.verifiedAt``, when:

1. its NS records are delegated to its Route53 hosted zone, i.e. your root domain's DNS settings
   include the NS records that ``describe`` reports, and
2. its AWS Certificate Manager TLS certificate is issued. ACM validates the certificate with a DNS
   record in the hosted zone, so it is issued once the domain is delegated.

While it is not verified, ``status.verificationMessage`` says which step is not complete, and why.
https itself is served by each LLMClient that uses the domain, on its own subdomain,
``<llmclient>.<domain>``, with its own certificate, which the LLMClient's deployment manages.
