Cloud Infrastructure as Code: Classroom Bootcamp
================================================

An eight-hour classroom bootcamp on infrastructure as code with Terraform and Terragrunt, taught on
the `smarter-infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`__ repository,
which builds Smarter's complete AWS environment: the network, the Kubernetes cluster, ingress,
certificates and the application's resources. It is a real production configuration, not a teaching
example: an EKS cluster on Spot capacity with the Cluster Autoscaler and roles for service accounts,
Calico `network policies
<https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/terraform/kubernetes/network_policy.tf>`__,
Traefik and cert-manager as Helm releases, and a `root configuration
<https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/terragrunt.hcl>`__ that refuses
to run against the wrong AWS account. Smarter itself goes on to manage infrastructure at run time,
through a `service layer
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/infrastructure/services/__init__.py>`__
that creates DNS records, certificates, ingresses and GPU node groups, with an in-memory provider in
tests. Students read a real production configuration, plan it, estimate its cost, and write a module
of their own. See :doc:`../course-formats` for the standard bootcamp day, the grading scale and the
course policies, and :doc:`../infrastructure-as-code` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Cloud, operations and platform engineers, and developers who deploy their own systems.
   * - **Deployment**
     - Each student clones ``smarter-infrastructure`` and installs Terraform (or OpenTofu) and
       Terragrunt. Labs that run ``plan`` need a sandbox AWS account with read access; no lab in
       this bootcamp runs ``apply`` against the full stack.
   * - **Cost**
     - Free if only ``plan`` is run. The optional module lab creates a few cents of resources and
       destroys them.

.. warning::

   ``terraform apply`` creates real, billable cloud resources, and the full Smarter stack costs
   hundreds of dollars a month. Use a dedicated sandbox account with a billing alert, never a
   production account, and destroy what you create at the end of each session.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Explain the benefits of infrastructure as code: repeatability, review, history and drift
   detection.
2. Read Terraform: providers, resources, data sources, variables, outputs, modules and state.
3. Explain how Terragrunt keeps several environments consistent without duplicating code.
4. Map a production AWS environment (VPC, EKS, ingress, certificates) to the modules that create it,
   and explain its security design.
5. Plan infrastructure, read a plan, and estimate its monthly cost.

Technical Prerequisites
-----------------------

- **Required:** the Linux or macOS command line, Git, and a text editor.
- **Required:** cloud fundamentals: regions, virtual networks and subnets, identity and access
  management, and managed services.
- **Required:** Docker and basic Kubernetes concepts (what a cluster, a node and an ingress are).
- **Required:** reading JSON and YAML.
- **Required:** Terraform (or OpenTofu), Terragrunt and the AWS CLI installed, and, for students
  who will run ``plan``, a sandbox AWS profile set up, before the bootcamp.
- **Helpful:** networking (CIDR blocks, routing, NAT, DNS) and some AWS console experience.

Schedule
--------

The files that the lectures refer to are listed in full under `Smarter in the Source Code`_.

.. list-table::
   :header-rows: 1
   :widths: 8 8 84

   * - Block
     - Min
     - Content
   * - 1
     - 45
     - **Lecture 1: Why infrastructure as code.** Click-ops versus code, declarative versus
       imperative, and the lifecycle of ``init``, ``plan``, ``apply`` and ``destroy``. State, and
       why it must be stored remotely and locked.
   * - 2
     - 45
     - **Lab 1: A first module.** Write a tiny Terraform configuration that creates an S3 bucket
       with versioning and encryption in a sandbox account, plan it, apply it and destroy it.
       Produces Assignment 1.
   * - 3
     - 45
     - **Lecture 2: Reading real Terraform.** A tour of ``smarter-infrastructure``: the
       ``aws/terraform`` modules (``vpc``, ``kubernetes``, ``kubernetes_ingress``,
       ``kubernetes_cert_manager``, ``kubernetes_descheduler`` and ``smarter``), their variables
       and outputs, and how they depend on each other.
   * - 4
     - 45
     - **Lab 2: Map the stack.** For each module, list the AWS and Kubernetes resources that it
       creates, and draw the dependency graph between modules. Produces Assignment 2.
   * - 5
     - 45
     - **Lecture 3: Terragrunt and environments.** ``aws/terragrunt.hcl``, ``global.hcl``, the
       ``stack`` folder, and the ``alpha``, ``local`` and ``prod`` environments. Keeping
       environments the same where it matters and different where it must be.
   * - 6
     - 45
     - **Lecture 4: Security by design.** Why the cluster sits on a private network, public and
       private subnets, NAT, security groups, Calico network policies with default-deny ingress, IAM
       roles for service accounts, ``allowed_account_ids``, least privilege, and the repository's
       own unencrypted remote state as a finding to fix.
       :doc:`/smarter-platform/cloud-infrastructure`.
   * - 7
     - 45
     - **Lab 3: Plan and price.** Run ``terraform plan`` (or ``terragrunt plan``) for the ``vpc``
       and ``kubernetes`` modules against a sandbox account, read the plan, and estimate the monthly
       cost with Infracost or the AWS pricing calculator. Produces Assignment 3.
   * - 8
     - 45
     - **Lecture 5: Infrastructure inside the application.** How Smarter manages DNS records,
       certificates and Kubernetes objects at run time through its infrastructure service layer
       (``smarter/smarter/apps/infrastructure/``), with an AWS provider in production and an
       in-memory provider in tests. :doc:`/smarter-framework/technologies/infrastructure`.
       Pre-reading: "One deploy, end to end" and "Waiting without blocking" in the case study
       `What Happens When You Click Deploy <https://smarter.sh/case-studies/deploy>`__.
   * - 9
     - 45
     - **Lab 4: Static analysis.** Run ``tflint`` and Checkov on the repository, and triage the
       findings. Ungraded.
   * - 10
     - 45
     - **Lecture 6: Working as a team.** Code review of plans, CI for infrastructure, drift,
       importing existing resources, and the ``terraform apply`` safety rules. The six guards
       of the daily DNS sweep, from "Only the exact shape" to "A dry run first", in "Cleaning up"
       in `the deploy case study <https://smarter.sh/case-studies/deploy>`__, as a worked example
       of automation that deletes cloud resources safely.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone and plan it.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: A First Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write a small Terraform configuration for an encrypted, versioned S3 bucket with a
lifecycle rule, with variables and outputs, then plan, apply and destroy it.

**Turn in:** the configuration in a Git repository, and the plan, apply and destroy output.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Correctness
     - 6
     - Applies cleanly; bucket has encryption, versioning and the lifecycle rule.
     - Missing a requirement.
   * - Structure
     - 5
     - Variables, outputs and pinned provider versions.
     - Hard-coded values.
   * - Hygiene
     - 5
     - State and credentials not committed; resources destroyed.
     - State file committed, or resources left running.
   * - Explanation
     - 4
     - Explains the plan output.
     - Raw output only.

Assignment 2: Stack Map
~~~~~~~~~~~~~~~~~~~~~~~

Students map each module in ``aws/terraform`` to the resources that it creates, and draw the
dependency graph between modules.

**Turn in:** a table and a diagram.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Resource mapping
     - 8
     - Every module's main resources correctly identified.
     - Modules skipped or misread.
   * - Dependencies
     - 6
     - Graph shows which outputs feed which inputs.
     - Boxes without edges.
   * - Security observations
     - 4
     - Notes private subnets, network policies and roles.
     - None.
   * - Clarity
     - 2
     - Clear.
     - Cluttered.

Assignment 3: Plan and Price
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students run a plan for the ``vpc`` and ``kubernetes`` modules against a sandbox account, and
estimate the monthly cost of the result, comparing it with the figures in :doc:`../kubernetes`.

**Turn in:** the plan summary, a cost table by resource, and a half-page comparison.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Plan
     - 5
     - Runs, and the summary is explained.
     - Does not run, or unexplained.
   * - Cost estimate
     - 7
     - Every billable resource priced, with assumptions.
     - Major items missing (NAT gateways, nodes, load balancer).
   * - Comparison
     - 5
     - Explains differences from the published figures.
     - No comparison.
   * - Savings
     - 3
     - Suggests one realistic saving and its trade-off.
     - None.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp.

Capstone A: A Reusable Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Write a reusable, documented, tested Terraform module in the style of a real
infrastructure repository.

Students write a module that a team like Smarter's could use, for example an S3 bucket for database
backups with encryption, lifecycle rules and a least-privilege IAM policy for a Kubernetes service
account, or a CloudWatch billing alarm with email notification. It includes examples and
automated checks.

**What students turn in:**

- A Git repository with the module, an ``examples/`` folder, a ``README.md`` generated with
  terraform-docs, and a CI workflow that runs ``terraform fmt``, ``validate``, ``tflint`` and
  Checkov.
- Evidence of a plan, apply and destroy in a sandbox account.

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
     - Applies and destroys cleanly.
     - Errors.
   * - Interface
     - 20
     - Clear variables with types, descriptions and validation; useful outputs.
     - Untyped, undocumented variables.
   * - Security
     - 20
     - Encryption, least privilege, no public access unless intended.
     - Wide permissions.
   * - Automated checks
     - 20
     - CI runs all four checks and passes.
     - Some checks, or failing.
   * - Documentation
     - 20
     - Generated docs and a working example.
     - Missing.

Capstone B: An Architecture and Cost Review
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Review a real production infrastructure against a recognized framework, and
make evidence-based recommendations.

Students review ``smarter-infrastructure`` against the security, reliability and cost optimization
pillars of the AWS Well-Architected Framework, using the code, plans, static analysis and cost
estimates as evidence.

**What students turn in:**

- A review document (four to six pages): findings by pillar, each with evidence and a severity.
- A cost model of the stack with at least two cost reduction options and their trade-offs.
- Prioritized recommendations, at least one written as a code change (a diff).

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Framework use
     - 20
     - Findings organized by pillar and question.
     - Framework named only.
   * - Evidence
     - 25
     - Each finding cites code, plan output or tool results.
     - Opinions.
   * - Cost model
     - 20
     - Complete, with options and trade-offs.
     - Partial.
   * - Recommendations
     - 20
     - Prioritized, realistic, one as a diff.
     - Unprioritized.
   * - Writing
     - 15
     - Clear and concise.
     - Disorganized.

Recommended Texts
-----------------

- **Pre-reading:** HashiCorp's `Get Started with AWS
  <https://developer.hashicorp.com/terraform/tutorials/aws-get-started>`__ tutorial.
- **Reference:** Yevgeniy Brikman, *Terraform: Up & Running* (3rd edition, O'Reilly, 2022).
- **Smarter documentation:** :doc:`/smarter-platform/cloud-infrastructure`,
  :doc:`/smarter-framework/technologies/aws` and
  :doc:`/smarter-framework/technologies/infrastructure`.

Further Study
-------------

.. include:: further-study.txt
