Cloud Infrastructure as Code
============================

**Why Smarter.** Infrastructure as code is hard to teach well, because a realistic configuration
is expensive to run and nobody publishes their production one. The
`smarter-infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`__ repository is
exactly that: the Terraform and Terragrunt that build Smarter's AWS environment, in public.
Students can read a complete, real production configuration without having to pay for one:

- **Six modules with real dependencies.** The
  `vpc <https://github.com/smarter-sh/smarter-infrastructure/tree/main/aws/terraform/vpc>`__
  network; an EKS cluster in the
  `kubernetes <https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/terraform/kubernetes/main.tf>`__
  module, with roles for service accounts, managed node groups on Spot capacity that scale from 0
  to 15 nodes, and the Cluster Autoscaler; Traefik and cert-manager as Helm releases; the
  descheduler; and the
  `smarter <https://github.com/smarter-sh/smarter-infrastructure/tree/main/aws/terraform/smarter>`__
  module's certificates, CloudFront, ECR, IAM, S3, SES, Route53 records and bastion host.
- **Security built in.** A private network for the cluster, Calico
  `network policies <https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/terraform/kubernetes/network_policy.tf>`__
  with default-deny ingress for the database, the cache and the application, and a
  `root configuration <https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/terragrunt.hcl>`__
  whose ``allowed_account_ids`` refuses to run against any other AWS account.
- **Environments without copy and paste.** A shared
  `stack <https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/stack/stack.hcl>`__
  of cluster versions and instance types, and ``alpha``, ``local`` and ``prod``
  `environments <https://github.com/smarter-sh/smarter-infrastructure/tree/main/aws/environments>`__
  that are a few lines each.
- **Real debts to find.** The remote state is stored with ``encrypt = false``, and a comment marks
  a known naming problem as a ``FIX NOTE``. Students learn to review infrastructure code as
  critically as application code.

Smarter's own infrastructure `service layer
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/infrastructure/services/__init__.py>`__
then shows how an application manages cloud resources at run time. Deploying an LLMClient creates
its DNS record, certificate and Kubernetes `ingress
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmclient/k8s/ingress.yaml.tpl>`__,
and serving a self-hosted model creates an EKS `node group
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmhost/services/nodegroups.py>`__
of GPU nodes. All of it goes through one facade, with Route53 and Certificate Manager in
production and an `in-memory provider
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/infrastructure/providers/memory.py>`__
in tests, so the same code runs in both.

**What the course covers.** Why infrastructure as code, declarative configuration, and the
Terraform lifecycle; the Terraform language; state, remote state and locking; modules, their
interfaces and composition; reading a real stack and mapping its dependencies; Terragrunt and
environments; networking with VPCs, subnets, NAT and security groups; Kubernetes on AWS, with node
groups, add-ons, storage and network policies; identity, roles for service accounts and least
privilege; testing and CI with ``fmt``, ``validate``, ``tflint``, Checkov and ``terraform test``;
pricing a plan; and infrastructure managed by the application itself.

**Look at.**

- The `smarter-infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`__
  repository, starting with
  `aws/terragrunt.hcl <https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/terragrunt.hcl>`__
  and `aws/terraform/ <https://github.com/smarter-sh/smarter-infrastructure/tree/main/aws/terraform>`__.
- `smarter/smarter/apps/infrastructure/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/infrastructure>`__,
  the application's service layer.

Each course plan lists every file that it uses, in both repositories, under *Smarter in the Source
Code*.

**Read.** :doc:`/smarter-platform/cloud-infrastructure`, :doc:`/smarter-framework/technologies/aws`,
:doc:`/smarter-framework/technologies/infrastructure`, `cert-manager and Route 53: DNS-01
Certificates, One Issuer per Delegated Zone
<https://blog.smarter.sh/2026/10/01/cert-manager-dns01-route53/>`__, `Amazon SES, DKIM and DMARC:
Email Authentication for Every Smarter Environment
<https://blog.smarter.sh/2026/08/09/amazon-ses-dkim-dmarc/>`__, and the case study `What Happens
When You Click Deploy <https://smarter.sh/case-studies/deploy>`__.

**Exercises.**

- Map each Terraform module to the AWS resources that it creates, and explain why the cluster sits
  on a private network.
- Run ``terraform plan`` against a sandbox AWS account, and estimate the monthly cost of the
  result. Compare it with the figures in :doc:`kubernetes`.
- Run ``tflint`` and Checkov on the repository, triage the findings, and fix one, such as the
  unencrypted remote state.
- Study how Smarter's infrastructure service layer lets the same code use AWS in production and a
  fake, in-memory provider in tests, and why that matters.

.. warning::

   ``terraform apply`` creates real, billable cloud resources. Use a dedicated sandbox account
   with a billing alert, and destroy what you create at the end of each session.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <infrastructure-as-code/bootcamp>
   Two-week online course: 6 hours <infrastructure-as-code/two-week>
   Four-week online course: 12 hours <infrastructure-as-code/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
