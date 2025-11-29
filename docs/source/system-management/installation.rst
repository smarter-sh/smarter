Installation
============

Smarter is a Docker-based application that is designed to be deployed in various environments. The path of least
resistance is to deploy Smarter to `AWS Elastic Kubernetes Service <https://aws.amazon.com/eks/>`_ (EKS) using the provided Helm chart and Smarter-supported
Terraform modules and GitHub Actions workflows as further described below.

While any of these methods and technologies can be replaced with alternatives, the approach outlined here is
known to work, and is the recommended path; initially at least.

1. **Cloud infrastructure**. See `Cloud Infrastructure <cloud-infrastructure.html>`_ for details on preparing your AWS account
   with the necessary networking, IAM roles, and compute resources using Smarter-supported Terraform modules.

2. **Application software**. Smarter maintains a Docker image in DockerHub at `https://hub.docker.com/r/mcdaniel0073/smarter <https://hub.docker.com/r/mcdaniel0073/smarter>`_.
   Alternatively, see `Build <../developers/build.html>`_ in the Developer Guide for instructions on building your own Docker image and pushing to a private `AWS Elastic Container Registry <https://aws.amazon.com/ecr/>`_ (ECR) repository.

3. **Helm chart**. Helm is overwhelmingly the most popular package manager for Kubernetes applications.
   See `Helm Chart <https://artifacthub.io/packages/helm/project-smarter/smarter>`_ for details on deploying Smarter to your Kubernetes cluster using the official Smarter Helm chart.

4. **GitHub Actions workflows**. Smarter provides GitHub Actions workflows to automate both build and deployment of Smarter to your AWS EKS cluster.
   These workflows are supported and are known to work.
   See `GitHub Actions Workflows <../developers/ci-cd.html>`_ for details on how to use these workflows.

.. caution::

   While it is possible to deploy Smarter using other methods (e.g., manually applying Kubernetes manifests, using other CI/CD systems,
   or deploying to other cloud providers), you should keep in mind that there are **MANY** details involved in deploying this platform correctly and securely.
   There are multiple hosts, databases, caches, message queues, and other components that must be configured and connected properly. The Kubernetes
   infrastructure assumes the existence of certain AWS resources (e.g., S3 buckets, RDS instances, ElastiCache clusters, IAM roles, etc.) and Kubernetes services
   that must be created and configured. Ingresses, DNS, TLS/SSL certificates, and other networking components must also be configured correctly, and,
   these are handled multiple ways depending on your environment as well as the specific AI resource in question (e.g., ChatBot vs. Agent, user, Api key, etc.).

   Moreover (and not to beat on a dead horse, but ....), the AWS VPN networking layer on which Smarter runs is highly secure, requiring
   some forethought and planning to ensure that all components can communicate as expected while still maintaining a strong security posture. For example,
   Smarter natively supports providing LLM tool calls with remote access to private data sources (e.g., internal company databases, intranet web services, etc.) via AWS PrivateLink endpoints.
   This is a powerful feature, but it requires additional AWS infrastructure to be created and configured properly. **THIS IS NOT TRIVIAL TO GET RIGHT.**

   The authors have invested upwards of three years fine tuning the provided Terraform modules, the Helm chart, and the GitHub Actions workflows
   to ensure a smooth deployment experience. If you choose to reinvent the wheel, then at least do this knowingly, and be prepared to invest
   significant time and effort into getting everything working correctly.
