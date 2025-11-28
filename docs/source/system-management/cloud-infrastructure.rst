Cloud Infrastructure
====================

Running Smarter in production in the cloud requires some additional configuration and setup. Smarter
currently support AWS as its sole cloud infrastructure provider. The project maintains a set of
Terraform scripts to fully automate the deployment and management of all AWS infrastructure
resources required for normal operation of the Smarter platform.

These scripts can be found in the `https://github.com/smarter-sh/smarter-infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`_ repository.
See the README file in that repository for detailed instructions on how to use Terraform scripts
to deploy and manage Smarter infrastructure on AWS. This set of Terraform scripts will store its
state remotely in an S3 bucket, and it will also enable state locking using DynamoDB
to prevent concurrent modifications to the infrastructure. See `smarter-infrastructure/aws/terragrunt.hcl <https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/terragrunt.hcl>`_ for more details.

Smarter's Terraform scripts are designed to be used with Terragrunt, a thin wrapper for Terraform
that provides extra tools for working with multiple Terraform modules and managing remote state.
It is highly recommended to use Terragrunt when working with the Smarter infrastructure
Terraform scripts as this facilitates reuse of the Terraform modules across different environments
(e.g., alpha, beta, next, production) and simplifies management of remote state files in S3.

.. warning::

  **THERE ARE COSTS ASSOCIATED WITH RUNNING CLOUD INFRASTRUCTURE.**  Be sure to review the AWS pricing documentation
  for each of the services that will be created by the Terraform scripts to understand the potential costs involved.

  **CREATING AND MANAGING CLOUD INFRASTRUCTURE IS MUCH MORE COMPLEX THAN SIMPLY DEPLOYING THE SMARTER APPLICATION ITSELF**. It is assumed that the person using these Terraform scripts
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
8. Review the Terraform plan by running:

    .. code-block:: bash

        terragrunt plan

9. Apply the Terraform configuration to create the necessary AWS resources by running:

    .. code-block:: bash

        terragrunt apply
10. Follow the prompts to confirm the creation of resources.
11. Once the process is complete, Terraform will have created all the necessary AWS resources for running Smarter in production.

Resources Created
-----------------

The Terraform scripts will create the following AWS resources:

- `AWS Certificate Manager <https://aws.amazon.com/certificate-manager/>`_ (ACM) certificates for SSL/TLS encryption.
- `AWS Cloudfront <https://aws.amazon.com/cloudfront/>`_ distribution for content delivery.
- `AWS Elastic Container Registry <https://aws.amazon.com/ecr/>`_ (ECR) for storing Docker images.
- `AWS Identity and Access Management <https://aws.amazon.com/iam/>`_  (IAM) roles and policies for secure access control.
- `AWS Route53 <https://aws.amazon.com/route53/>`_ hosted zone(s) and DNS records for domain name resolution.
- `AWS Simple Email Service <https://aws.amazon.com/ses/>`_ (SES) for sending transactional emails.
- `AWS Simple Storage Service <https://aws.amazon.com/s3/>`_ (S3) buckets for storing static and media files.
- Kubernetes `cert-manager <https://cert-manager.io/docs/>`_ for managing SSL/TLS certificates within the Kubernetes cluster.
- Kubernetes `ingress resources <https://kubernetes.io/docs/concepts/services-networking/ingress/>`_ for routing traffic to the Smarter application.
- Kubernetes `secrets <https://kubernetes.io/docs/concepts/configuration/secret/>`_ for storing environment-specific sensitive information used for deployments such as database credentials, smtp credentials, and admin login credentials.
- Kubernetes `namespace <https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/>`_ for isolating Smarter resources within the Kubernetes cluster.
