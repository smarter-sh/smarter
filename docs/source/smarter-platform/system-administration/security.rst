Security
========

A production Smarter platform is secured in two layers. The cloud infrastructure, which
`smarter-infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`__ builds with
Terraform on AWS, controls who and what can reach the cluster, its pods and its data. The
application and its Helm chart control what each request, user, API key and LLM tool can do. These
pages describe both, as they are configured when you install as
:doc:`../installation/production-deployment` describes, the risk that Smarter's dependencies
carry, and what Smarter leaves to you.

Smarter's security design follows :doc:`ADR-016 <../../adr/016-security>`: use Django's and Kubernetes'
well-maintained protections, and add Smarter's own only where an AI platform needs more.

Each Smarter release is a new Docker image, built with the operating system's latest security
updates, and a new Helm chart version. Update regularly, as :doc:`operations/updates` describes.

.. toctree::
   :maxdepth: 1

   security/infrastructure
   security/application
   security/supply-chain
   security/security-faq
