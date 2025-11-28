Cloud Infrastructure
====================

Running Smarter in production in the cloud requires some additional configuration and setup. Smarter
currently support AWS as its sole cloud infrastructure provider. The project maintains a set of
Terraform scripts to fully automate the deployment and management of all AWS infrastructure
resources required for normal operation of the Smarter platform.

These scripts can be found in the `https://github.com/smarter-sh/smarter-infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`_ repository.
See the README file in that repository for detailed instructions on how to use Terraform scripts
to deploy and manage Smarter infrastructure on AWS.

Smarter's Terraform scripts are designed to be used with Terragrunt, a thin wrapper for Terraform
that provides extra tools for working with multiple Terraform modules and managing remote state.
It is highly recommended to use Terragrunt when working with the Smarter infrastructure
Terraform scripts as this facilitates reuse of the Terraform modules across different environments
(e.g., alpha, beta, next, production) and simplifies management of remote state files in S3.

.. warning::

  **THERE ARE COSTS ASSOCIATED WITH RUNNING CLOUD INFRASTRUCTURE.**  Be sure to review the AWS pricing documentation
  for each of the services that will be created by the Terraform scripts to understand the potential costs involved.

  Creating and managing cloud infrastructure is MUCH MORE COMPLEX than simply deploying
  the Smarter application itself. It is assumed that the person using these Terraform scripts
  has a good understanding of AWS services, Terraform, and Terragrunt. If you are not familiar
  with these technologies, it is highly recommended to seek assistance from someone who is
  experienced in cloud infrastructure management before attempting to use these scripts.


Usage
-----------------

To use the Terraform scripts, follow these steps:

1. Install the AWS CLI on your local machine. Follow the instructions at `https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html <https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html>`_.
2. Configure the AWS CLI with your credentials by running:

.. code-block:: bash

   aws configure

3. Install Terraform on your local machine. Follow the instructions at `https://learn.hashicorp.com/tutorials/terraform/install-cli <https://learn.hashicorp.com/tutorials/terraform/install-cli>`_.
4. Install Terragrunt on your local machine. Follow the instructions at `https://terragrunt.gruntwork.io/docs/getting-started/install/ <https://terragrunt.gruntwork.io/docs/getting-started/install/>`_.
5. Clone the smarter-infrastructure repository to your local machine.

   .. code-block:: bash

      git clone https://github.com/smarter-sh/smarter-infrastructure.git
      cd smarter-infrastructure/aws/prod

6. Initialize the Terraform working directory by running:

    .. code-block:: bash

        terragrunt init

7. Review and customize the `terragrunt.hcl <https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/prod/terragrunt.hcl>`_ configuration file to match your specific requirements.
8. Apply the Terraform configuration to create the necessary AWS resources by running:

    .. code-block:: bash

        terragrunt apply
9. Follow the prompts to confirm the creation of resources.
10. Once the process is complete, Terraform will have created all the necessary AWS resources for running Smarter in production.

Resources Created
-----------------

The Terraform scripts will create the following AWS resources:

- AWS Certificate Manager (ACM) certificates for SSL/TLS encryption.
- AWS Cloudfront distribution for content delivery.
- AWS Elastic Container Registry (ECR) for storing Docker images.
- AWS Identity and Access Management (IAM) roles and policies for secure access control.
- AWS Route53 hosted zone(s) and DNS records for domain name resolution.
- AWS S3 buckets for storing static and media files.
- Kubernetes cert-manager for managing SSL/TLS certificates within the Kubernetes cluster.
- Kubernetes ingress resources for routing traffic to the Smarter application.
- Kubernetes secrets for storing environment-specific sensitive information used for deployments such as database credentials and admin login credentials.
- Kubernetes ses for creating a Secret to store AWS SES SMTP credentials.
- Kubernetes namespace for isolating Smarter resources within the Kubernetes cluster.
