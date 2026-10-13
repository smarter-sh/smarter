Cloud Infrastructure as Code: Four-Week Online Course
=====================================================

A four-week online course on infrastructure as code with Terraform and Terragrunt, taught on the
`smarter-infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`__ repository, which
builds Smarter's complete AWS environment. It is a real production configuration, not a teaching
example: an EKS cluster on Spot capacity with the Cluster Autoscaler and roles for service accounts,
Calico `network policies
<https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/terraform/kubernetes/network_policy.tf>`__,
Traefik and cert-manager as Helm releases, and a `root configuration
<https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/terragrunt.hcl>`__ that refuses
to run against the wrong AWS account. Smarter itself goes on to manage infrastructure at run time,
through a `service layer
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/infrastructure/services/__init__.py>`__
that creates DNS records, certificates, ingresses and GPU node groups, with an in-memory provider in
tests. There are twelve 30-minute recorded lectures and a 90-minute live session each week. Week 1
covers Terraform fundamentals, week 2 modules and environments, week 3 networking, Kubernetes and
security, and week 4 testing, CI, cost and infrastructure managed by the application itself. See
:doc:`../course-formats` for the format, the grading scale and the course policies, and
:doc:`../infrastructure-as-code` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Cloud, operations and platform engineers, and developers who deploy their own systems.
   * - **Deployment**
     - Each student clones ``smarter-infrastructure`` and installs Terraform (or OpenTofu),
       Terragrunt and the AWS CLI, with a sandbox AWS account. An optional week 3 exercise applies
       the ``vpc`` and ``kubernetes`` modules for one session, if the instructor's budget allows.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - A few dollars for small exercises. The optional cluster exercise costs roughly a dollar an
       hour while it runs; destroy it the same day.

.. warning::

   ``terraform apply`` creates real, billable cloud resources. Use a dedicated sandbox account with
   a billing alert, and destroy what you create at the end of each session. Check the account
   and region before every apply.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain infrastructure as code, the Terraform lifecycle, and state management.
2. Write reusable modules with typed, validated interfaces.
3. Manage several environments with Terragrunt, and explain the trade-offs.
4. Design and explain a secure network and Kubernetes environment on AWS.
5. Test, lint, scan and price infrastructure in CI, and review plans as a team.
6. Explain how an application manages cloud resources at run time, and how to test that code
   without touching the cloud.

Technical Prerequisites
-----------------------

- **Required:** the Linux or macOS command line, Git and GitHub, including pull requests.
- **Required:** cloud fundamentals: regions, networks, subnets, IAM and managed services.
- **Required:** Docker and basic Kubernetes concepts.
- **Required:** reading JSON and YAML.
- **Required by the end of week 1:** Terraform or OpenTofu, Terragrunt and the AWS CLI, with a
  sandbox AWS profile.
- **Helpful:** networking (CIDR, routing, NAT, DNS), reading Python (for week 4), and GitHub
  Actions.

Schedule
--------

The files that the lectures refer to are listed in full under `Smarter in the Source Code`_.

.. list-table::
   :header-rows: 1
   :widths: 10 18 72

   * - Week
     - Item
     - Content
   * - 1
     - Lecture 1
     - **Why infrastructure as code.** Declarative configuration and the Terraform lifecycle.
   * - 1
     - Lecture 2
     - **Terraform language.** Providers, resources, data sources, variables, outputs and
       expressions.
   * - 1
     - Lecture 3
     - **State.** Remote state, locking, ``terraform state`` commands, and recovering from mistakes.
   * - 1
     - Live session 1
     - Tooling triage, then a live plan, apply and destroy. Start Assignment 1.
   * - 2
     - Lecture 4
     - **Modules.** Interfaces, composition, versioning, and the registry.
   * - 2
     - Lecture 5
     - **Reading a real stack.** The ``aws/terraform`` modules in ``smarter-infrastructure``.
   * - 2
     - Lecture 6
     - **Terragrunt and environments.** ``terragrunt.hcl``, ``global.hcl``, ``stack``, and the
       ``alpha``, ``local`` and ``prod`` environments.
   * - 2
     - Live session 2
     - Review of Assignment 1. Groups map the stack's dependencies. Start Assignment 2.
   * - 3
     - Lecture 7
     - **Networking.** VPCs, public and private subnets, NAT, routing and security groups, in the
       ``vpc`` module.
   * - 3
     - Lecture 8
     - **Kubernetes on AWS.** EKS, Spot node groups that scale from zero, the Cluster
       Autoscaler, add-ons, persistent storage and Calico network policies, in the ``kubernetes``
       module; ingress and certificates in ``kubernetes_ingress`` and
       ``kubernetes_cert_manager``.
   * - 3
     - Lecture 9
     - **Identity and secrets.** IAM roles, roles for service accounts, least privilege, and
       secrets in Terraform.
   * - 3
     - Live session 3
     - Review of Assignment 2. Optional live apply of the ``vpc`` module in a sandbox account,
       then destroy. Capstone proposals discussed. Start Assignment 3.
   * - 4
     - Lecture 10
     - **Testing and CI.** ``fmt``, ``validate``, ``tflint``, Checkov, ``terraform test``, and plan
       review in pull requests.
   * - 4
     - Lecture 11
     - **Cost.** Pricing a plan with Infracost, the main cost drivers of a Kubernetes platform, and
       the figures in :doc:`../kubernetes`.
   * - 4
     - Lecture 12
     - **Infrastructure inside the application.** Smarter's infrastructure service layer
       (``smarter/smarter/apps/infrastructure/``): DNS, certificates, Kubernetes ingresses and EKS
       node groups for self-hosted models managed at run time, an AWS provider in production and
       an in-memory provider in tests.
   * - 4
     - Live session 4
     - Capstone presentations (about 6 minutes each, with 2 minutes of questions), and a course
       retrospective.

Assignments 1 to 3 are due before the next live session. Assignment 4 is due in the middle of week
4. The capstone proposal is due before Live session 3, and the capstone at the start of Live
session 4.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: State in Practice
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write a small configuration with remote state and locking, apply it, then rename a
resource with ``moved`` (or ``terraform state mv``) without destroying it, and import a resource
created by hand.

**Turn in:** a Git repository and the command output, with explanations.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Remote state
     - 5
     - Remote backend with locking.
     - Local state.
   * - Refactor without destroy
     - 6
     - Resource renamed with no replacement in the plan.
     - Resource destroyed and recreated.
   * - Import
     - 5
     - Hand-made resource imported; plan shows no changes.
     - Import incomplete.
   * - Hygiene
     - 4
     - No state or secrets committed; destroyed afterwards.
     - State committed.

Assignment 2: Stack Map and Environment Diff
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students map every module to its resources and dependencies, and compare the ``alpha`` and
``prod`` environments.

**Turn in:** a table, a diagram and a one-page comparison.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Resource map
     - 6
     - Correct and complete.
     - Gaps.
   * - Dependencies
     - 5
     - Outputs and inputs shown.
     - No edges.
   * - Environment comparison
     - 6
     - Every difference found and justified.
     - Some missed.
   * - Clarity
     - 3
     - Clear.
     - Unclear.

Assignment 3: Security Review of the Network and Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students review the ``vpc`` and ``kubernetes`` modules: which resources are reachable from the
internet, how traffic flows, which IAM permissions exist and who has them, and what Checkov
reports.

**Turn in:** a network diagram, an IAM table, and a two-page review.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Network
     - 6
     - Correct diagram with exposure marked.
     - Errors.
   * - IAM
     - 6
     - Roles, policies and trust relationships correct.
     - Partial.
   * - Findings
     - 5
     - Triaged and justified.
     - Pasted output.
   * - Recommendations
     - 3
     - Realistic and prioritized.
     - None.

Assignment 4: Infrastructure in Code, Tested Without the Cloud
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students read Smarter's infrastructure service layer, explain how a DNS record is created for a
deployed LLMClient, and explain how the in-memory provider lets the tests run without AWS. They
compare this run-time management with Terraform's.

**Turn in:** a two-page explanation with code references and a diagram.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Flow
     - 6
     - From the application call to the provider, with references.
     - Partial.
   * - Test design
     - 6
     - Explains the fake provider and its value.
     - Not addressed.
   * - Comparison
     - 5
     - When run-time management is right, and when Terraform is.
     - Superficial.
   * - Clarity
     - 3
     - Clear.
     - Unclear.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and present it in Live session 4.

Capstone A: A Module for the Smarter Stack
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design, test and document a production-quality module that fits an existing
infrastructure repository and its environments.

Students add a module to their fork of ``smarter-infrastructure``, wired into the Terragrunt stack
for each environment. Suitable examples: an encrypted backup bucket with lifecycle rules and an IAM
role for a Kubernetes service account; budget alarms per environment; or VPC flow logs with a
retention policy.

**What students turn in:**

- A pull request against their fork with the module, Terragrunt configuration for each
  environment, ``terraform test`` tests, generated documentation, and CI checks.
- Evidence of a plan for each environment, and of an apply and destroy in a sandbox account.
- A cost estimate, and a six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Fits the repository
     - 20
     - Follows its structure, naming and Terragrunt patterns.
     - Stands apart.
   * - Interface and security
     - 20
     - Typed, validated, least privilege.
     - Loose and permissive.
   * - Tests and CI
     - 25
     - ``terraform test`` and static checks in CI.
     - None.
   * - Environments
     - 15
     - Plans for every environment, differences justified.
     - One environment.
   * - Documentation, cost and presentation
     - 20
     - Generated docs, estimate, clear presentation.
     - Missing.

Capstone B: A Multi-Environment Platform for Your Own Application
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design infrastructure for a real application across environments, with
security, cost and automation, following the patterns of a production repository.

Students write Terraform and Terragrunt for a small application of their own, for example a
container on a managed service with a database, DNS and a certificate, with ``dev`` and ``prod``
environments, CI that plans on pull requests, and a cost estimate. They apply ``dev`` once and
destroy it.

**What students turn in:**

- A repository with modules, Terragrunt configuration, CI and a ``README.md``.
- Evidence of the plan in CI, and of an apply and destroy of ``dev``.
- An architecture diagram, a security note and a cost estimate for both environments.
- A six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Works
     - 20
     - ``dev`` applies and the application responds.
     - Errors.
   * - Design
     - 20
     - Modules and environments cleanly separated.
     - Duplicated code.
   * - Security
     - 20
     - Private networking, least privilege, encrypted data.
     - Public by default.
   * - Automation
     - 20
     - Plans in CI, with checks.
     - Manual only.
   * - Documentation, cost and presentation
     - 20
     - Diagram, estimates, clear presentation.
     - Missing.

Recommended Texts
-----------------

- **Required:** Yevgeniy Brikman, *Terraform: Up & Running* (3rd edition, O'Reilly, 2022), across
  weeks 1 to 4.
- **Required:** Kief Morris, *Infrastructure as Code* (2nd edition, O'Reilly, 2020), part 1 and the
  chapters on environments and testing, in weeks 2 and 4.
- **Required:** the security, reliability and cost optimization pillars of the `AWS
  Well-Architected Framework <https://aws.amazon.com/architecture/well-architected/>`__, in week 3.
- **Reference:** the `Amazon EKS Best Practices Guide
  <https://docs.aws.amazon.com/eks/latest/best-practices/introduction.html>`__.
- **Smarter documentation:** :doc:`/smarter-platform/cloud-infrastructure`,
  :doc:`/smarter-framework/technologies/aws`, :doc:`/smarter-framework/technologies/infrastructure`
  and :doc:`/smarter-framework/smarter-on-kubernetes`.

Further Study
-------------

.. include:: further-study.txt
