Amazon Web Services (AWS)
=========================================

`AWS <https://aws.amazon.com/>`_ is a comprehensive and widely adopted cloud platform,
offering over 200 fully featured cloud infrastructure services from data centers globally.
It provides a variety of infrastructure services such as computing power,
storage options, and networking capabilities, enabling businesses to scale and grow efficiently.

The Smarter Framework natively deploys to AWS using various services such as
EKS, Route 53, Certificate Manager and Simple Email Service to create a scalable and secure environment for applications.

Terraform
-----------------------------------------

See :doc:`../../smarter-platform/cloud-infrastructure` for details on using Terraform scripts
to deploy and manage Smarter infrastructure on AWS.


AWS Provider
-----------------------------------------

The platform reaches AWS only through the :doc:`infrastructure services <infrastructure>`,
which the AWS provider implements with Route53, AWS Certificate Manager and EKS.

.. toctree::
   :maxdepth: 1

   aws/overview
   aws/base
   aws/route53
   aws/acm
   aws/eks
