Production Deployment
===================================

.. attention::

   This is a complex deployment process that requires advanced knowledge of [Linux](https://www.linux.org/), [Docker](https://www.docker.com/), [Kubernetes](https://kubernetes.io/),
   [Helm](https://helm.sh/), [Terraform](https://developer.hashicorp.com/terraform), [AWS cloud infrastructure](https://docs.aws.amazon.com/), [Python](https://www.python.org/)-[Django](https://www.djangoproject.com/) applications, and [GitHub Actions](https://github.com/features/actions).
   Consider using one of our recommended [hosting partners](https://smarter.sh/), or a certified installation expert.


Smarter runs natively on Kubernetes using [spot-priced](https://aws.amazon.com/ec2/spot/pricing/) compute instances. This is a cost-effective, resilient, and
scalable architecture that requires minimal maintenance once deployed. It natively handles multiple environments
(alpha, beta, next, prod) for the same installation, maintaining clean separation of resources and
data between environments. It also natively handles multiple deployments of Smarter within the same AWS account.


Production deployment involves the following steps:

1. Build AWS Infrastructure using the `Smarter Official Terraform Modules <https://github.com/smarter-sh/smarter-infrastructure>`__.
2. Build and deploy the Smarter Chat ReactJS component to the CDN using `Smarter Chat <https://github.com/smarter-sh/smarter-chat>`__.
3. Deploy the Smarter Platform to your Kubernetes cluster using the `Official Smarter Helm chart <https://artifacthub.io/packages/helm/project-smarter/smarter>`__.


A modest amount of advance planning and an understanding of some basic organizational principles within Smarter will save you time and heartache.
Smarter's fundamental identification and organizational units are as follows:

.. list-table::
   :widths: 20 80

   * - **root_domain**
     - This is the root domain that you will use for your Smarter deployment. For example,
       if you want to access your Smarter instance at "platform.example.com", then your root domain
       would be "example.com". This value is used in both Terraform and Helm configurations,
       and it affects the naming of various resources such as DNS records and Hosted Zones.
   * - **platform_name**
     - Default is "smarter". Ensure that this matches in both Terraform and Helm configurations.
       Within the Smarter Platform application, the platform_name is derived from the root_domain by taking the first segment.
       For example, if your root domain is "example.com", then the platform_name will be "example".
   * - **shared_resource_identifier**
     - Default is "platform". Ensure that this matches in both Terraform and Helm configurations.
       Consider using a unique identifier such as your organization's domain name or abbreviation
       to avoid naming ambiguities with other Smarter deployments in your AWS account.
   * - **Environment**
     - One of "alpha", "beta", "next", or "prod". This is managed entirely inside the application, but affects the
       names of cloud resources including but not limited to DNS records and Hosted Zones that are created
       as part of normal platform operation.
   * - **platform_region**
     - Default is "us". Used exclusively inside of Terraform as part of naming high-level resources such
       as the EKS cluster, S3 buckets, SES resources, and more. Several environment variables in Helm are based on this value.

These four organizational units are combined in various ways to create higher-level naming conventions for both cloud resources as
well as application-level resources. Some examples:

- Kubernetes namespaces are named using the convention

  ``{platform_name}-{shared_resource_identifier}-{environment}``

  which by default would be 'smarter-platform-prod'.
- S3 buckets are named using the convention

  ``{environment}.{shared_resource_identifier}.{root_domain}``

  which by default would be 'alpha.platform.example.com'.
- EKS clusters are named using the convention

  ``{platform_name}-{shared_resource_identifier}-{platform_region}-{{unique_id}}``

  which by default would be 'smarter-platform-us-{{unique_id}}'.
- k8s namespaces are named using the convention

  ``{platform_name}-{shared_resource_identifier}-{environment}``

  which by default would be 'smarter-platform-prod'.
- IAM roles are prefixed with

  ``{platform_name}-{shared_resource_identifier}-{platform_region}``

  which by default would be 'smarter-platform-us'.

Within the Smarter application itself, these organizational units are combined to create higher-level organizational units. Examples:

- environment_namespaces are named using the convention

  ``{platform_name}-{shared_resource_identifier}-{environment}``

  which by default would be 'smarter-platform-prod'.
- environment_platform_domain is named using the convention

  ``{environment}.{shared_resource_identifier}.{root_domain}``

  which by default would be 'alpha.platform.example.com'.
- CDN domains are named using the convention

  ``cdn.{environment}.{shared_resource_identifier}.{root_domain}``

  which by default would be 'cdn.alpha.platform.example.com'.
- API domains are named using the convention

  ``{environment}.api.{shared_resource_identifier}.{root_domain}``

  which by default would be 'alpha.api.platform.example.com'.

**Example Kubernetes Deployment**

.. figure:: https://cdn.smarter.sh/images/example-kubernetes-deployment.png
  :alt: Example Kubernetes Deployment
  :align: center
  :width: 100%
  :class: img-bottom-margin


I. Infrastructure
-------------------

The entire AWS infrastructure build is fully automated using Terraform and Terragrunt
scripts. You should begin by reviewing the following documentation:

- README at `Smarter Infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`__.
- `Makefile <https://github.com/smarter-sh/smarter-infrastructure/blob/main/Makefile>`__. This
  Makefile provides working shortcuts for all major operations. You should at least cursorily review
  these in order to ensure that you understand the basic intention of the Terraform scripts.
- `.env.example <https://github.com/smarter-sh/smarter-infrastructure/blob/main/.env.example>`__.
  The Terraform scripts in this repo use environment variables for all configuration values.
  You should not need to fork nor modify the code in this repo. The Makefile provides a shortcut
  for getting this setup correctly.

Note that this repo uses Terragrunt, a higher level wrapper around Terraform that provides
an ability to manage multiple environments and multiple deployments with the same codebase.
Make sure that you understand the basic principles of how Terragrunt works, and how it is
being used in this repo, before proceeding.

.. warning::

    Do not attempt to circumvent the official Terraform scripts. The
    cloud infrastructure is complex and has many interdependencies that would
    be difficult if not impossible to manage manually. Additionally, the
    Terraform scripts create a detailed set of resource tags that are the
    sole means of effectively tracking these resources inside your AWS account
    once they've been created.


II. ReactJS Component
----------------------

The Chat functionality in the Smarter Prompt Engineer Workbench is delivered as a deployed ReactJS component
served from a CDN at runtime. You will need to build and deploy this component separately from the main
Smarter Platform application. The source code of this component is mature and stable, and generally
only changes in response to regular version bumps of a minimal set of dependencies. This component
can safely run for months (or even years) without needing to be updated.

Begin by reviewing the following documentation:

- README at `Smarter Chat <https://github.com/smarter-sh/smarter-chat>`__.
- `Makefile <https://github.com/smarter-sh/smarter-chat/blob/main/Makefile>`__.
  This Makefile provides working shortcuts for all major operations. Importantly,
  The deployment process is fully automated and can be completed with a single command.
- `.env.example <https://github.com/smarter-sh/smarter-chat/blob/main/.env.example>`__.
  FIX NOTE: This .env file is not yet implemented.

.. raw:: html

   <div style="text-align: center;">
     <video src="https://cdn.smarter.sh/videos/read-the-docs2.mp4"
            autoplay loop muted playsinline
            style="width: 100%; height: auto; display: block; margin: 0; border-radius: 0;">
       Sorry, your browser doesn't support embedded videos.
     </video>
     <div style="font-size: 0.95em; color: #666; margin-top: 0.5em;">
       <em>Smarter Prompt Engineering Workbench Demo</em>
     </div>
   </div>
   <br/>


III. Smarter Platform Application
-----------------------------------

The Smarter Platform application consists of a Python-Django backend that supports an
API and a Web Console frontend. This single code base is deployed to Kubernetes as
an application server and also as a Celery worker and a Celery Beat worker.
The application follows 12-factor app principles and is designed to be horizontally
scalable and resilient to failure.

In most cases, you can deploy the Smarter Platform application using the official Helm
chart with minimal configuration. However, you can optionally build and deploy
from source, though this is out of the scope of this documentation.

Begin by reviewing the following documentation:

- README at `Official Smarter Helm chart <https://artifacthub.io/packages/helm/project-smarter/smarter>`__.
- `Values.yaml <https://artifacthub.io/packages/helm/project-smarter/smarter?modal=values>`__.
  This file contains the comprehensive set of configuration values for the Helm chart. These
  cover not only configuration of the application itself, but also all backing services and
  deployment options. Note that there are multiple options for the Database backend, including
  pod-based Mysql and MariaDB, and remote AWS RDS.
- (Optional) `Source code <https://github.com/smarter-sh/smarter>`__. You might find some
  of the source code helpful for understanding how to configure the application. Of interest
  are the `Django settings files <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/settings>`__,
  the `Smarter Settings module <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/common/conf.py>`__,
  the `Smarter Settings documentation <../smarter-framework/smarter-settings.html>`__,
  the `Python requirements <https://github.com/smarter-sh/smarter/tree/main/smarter/requirements>`__, and the
  `Dockerfile <https://github.com/smarter-sh/smarter/blob/main/Dockerfile>`__.

.. important::

    1. You will need to create your own Deployment workflow. You can use the `Smarter GitHub Actions Deployment workflow <https://github.com/smarter-sh/smarter/blob/main/.github/workflows/deploy.yml>`__
    and `Smarter GitHub Deployment Action <https://github.com/smarter-sh/smarter/blob/main/.github/actions/deploy/action.yml>`__
    in the official Smarter repo as a reference, but you should not attempt to use it directly unless you have forked
    the Smarter repo. The deployment workflow depends on a number GitHub Secrets that you must configure in your own GitHub repository.
    If possible, see `Smarter Settings - Secrets <https://github.com/smarter-sh/smarter/settings/secrets/actions>`__.

    2. You will need an AWS IAM key-pair with sufficient permissions to deploy the application to your Kubernetes cluster.
    At a minimum, this key-pair will need complete control of the EKS service, in addition to permissions to create and
    manage the various resources that the application depends on such as EC2 instances, EBS volumes, S3 buckets,
    SES resources, and more.


Trouble Shooting
------------------

Permissions and naming are the two most common sources of deployment-related problems. Consider the example
Kubernetes Ingress manifest below. It contains eleven references, created by either of Terraform or
the Smarter Platform application itself. These names have to agree, and must be able to "hand shake" as necessary
between Kubernetes and the Smarter Platform application.



.. figure:: https://cdn.smarter.sh/images/naming-example.png
  :alt: Example Kubernetes Ingress Manifest
  :align: center
  :width: 100%
  :class: img-bottom-margin
