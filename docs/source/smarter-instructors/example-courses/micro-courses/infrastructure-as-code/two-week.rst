Cloud Infrastructure as Code: Two-Week Online Course
====================================================

A two-week online course on infrastructure as code with Terraform and Terragrunt, taught on the
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
tests. There are six 30-minute recorded lectures and a 90-minute live session each week. Week 1
covers Terraform and reading a real stack, and week 2 covers environments, security, cost and
teamwork. See :doc:`../course-formats` for the format, the grading scale and the course policies,
and :doc:`../infrastructure-as-code` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Cloud, operations and platform engineers, and developers who deploy their own systems.
   * - **Deployment**
     - Each student clones ``smarter-infrastructure`` and installs Terraform (or OpenTofu),
       Terragrunt and the AWS CLI, with a sandbox AWS account for plans and small exercises.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - A few dollars at most, if students destroy what they create.

.. warning::

   ``terraform apply`` creates real, billable cloud resources. Use a dedicated sandbox account with
   a billing alert, never apply the full Smarter stack, and destroy what you create at the end of
   each session.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain infrastructure as code and the Terraform lifecycle, including state.
2. Read and write Terraform modules with variables, outputs and pinned providers.
3. Use Terragrunt to manage several environments from one code base.
4. Explain the security design of a production AWS and Kubernetes environment.
5. Plan, review and price infrastructure changes, and check them with static analysis.

Technical Prerequisites
-----------------------

- **Required:** the Linux or macOS command line, Git and GitHub.
- **Required:** cloud fundamentals: regions, networks, subnets, IAM and managed services.
- **Required:** Docker and basic Kubernetes concepts.
- **Required:** reading JSON and YAML.
- **Required before Live session 1:** Terraform or OpenTofu, Terragrunt and the AWS CLI installed,
  with a sandbox AWS profile.
- **Helpful:** networking (CIDR, routing, NAT, DNS), and some AWS console experience.

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
     - Lecture 1 (30 min)
     - **Why infrastructure as code.** Declarative configuration, the lifecycle, and state.
   * - 1
     - Lecture 2 (30 min)
     - **Terraform language.** Providers, resources, data sources, variables, outputs, modules
       and expressions.
   * - 1
     - Lecture 3 (30 min)
     - **Reading a real stack.** The ``aws/terraform`` modules in ``smarter-infrastructure`` and how
       they depend on each other.
   * - 1
     - Live session 1 (90 min)
     - Tooling triage, then a live plan, apply and destroy of a small module. Start Assignment 1.
   * - 2
     - Lecture 4 (30 min)
     - **Terragrunt and environments.** ``terragrunt.hcl``, ``global.hcl``, the ``stack`` folder,
       and the ``alpha``, ``local`` and ``prod`` environments.
   * - 2
     - Lecture 5 (30 min)
     - **Security and cost.** Private networks, security groups, IAM roles for service accounts,
       network policies, and pricing a plan. :doc:`/smarter-platform/cloud-infrastructure`.
   * - 2
     - Lecture 6 (30 min)
     - **Infrastructure in the application, and teamwork.** Smarter's infrastructure service
       layer and its in-memory test provider; reviewing plans, CI, drift and imports.
       Pre-reading: "One deploy, end to end" and "Waiting without blocking" in the case study
       `What Happens When You Click Deploy <https://smarter.sh/case-studies/deploy>`__.
   * - 2
     - Live session 2 (90 min)
     - Capstone presentations (about 5 minutes each, with 2 minutes of questions).

Assignment 1 is due at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
and the capstone at the start of Live session 2.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: A First Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write a Terraform configuration for an encrypted, versioned S3 bucket with a lifecycle
rule and remote state, then plan, apply and destroy it.

**Turn in:** a Git repository and the command output.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Correctness
     - 6
     - All requirements met; applies cleanly.
     - A requirement missing.
   * - Structure
     - 5
     - Variables, outputs, pinned versions, remote state.
     - Hard-coded; local state.
   * - Hygiene
     - 5
     - Nothing secret or stateful committed; destroyed afterwards.
     - State committed, or resources left.
   * - Explanation
     - 4
     - Plan explained.
     - Raw output.

Assignment 2: Stack Map and Environment Diff
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students map each module to its resources and dependencies, then compare the ``alpha`` and
``prod`` environments and explain each difference.

**Turn in:** a table, a dependency diagram, and a one-page environment comparison.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Resource map
     - 6
     - Correct for every module.
     - Gaps.
   * - Dependencies
     - 5
     - Outputs feeding inputs shown.
     - No edges.
   * - Environment comparison
     - 6
     - Every difference found and justified.
     - Some differences missed.
   * - Clarity
     - 3
     - Clear.
     - Unclear.

Assignment 3: Plan, Price and Scan
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students plan the ``vpc`` and ``kubernetes`` modules against a sandbox account, estimate the
monthly cost, and run ``tflint`` and Checkov on the repository, triaging the findings.

**Turn in:** the plan summary, a cost table, and a triage table.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Plan
     - 4
     - Runs and is explained.
     - Does not run.
   * - Cost
     - 6
     - Every billable resource priced, with assumptions.
     - Major items missing.
   * - Static analysis triage
     - 6
     - Each finding classified with reasons.
     - Output pasted only.
   * - Recommendations
     - 4
     - One saving and one fix, with trade-offs.
     - None.

Capstone Projects
-----------------

Students choose one, and present it in Live session 2.

Capstone A: A Reusable Module with CI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Write a reusable, documented and automatically checked Terraform module.

Students write a module such as a backup bucket with a least-privilege IAM role for a Kubernetes
service account, or a billing alarm with notification, with examples, generated documentation, and
CI that runs ``fmt``, ``validate``, ``tflint`` and Checkov.

**What students turn in:**

- A Git repository with the module, examples, ``README.md`` and CI.
- Evidence of a plan, apply and destroy.
- A five-minute presentation.

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
     - Typed, documented, validated variables.
     - Untyped.
   * - Security
     - 20
     - Encryption and least privilege.
     - Wide permissions.
   * - Automated checks
     - 20
     - All four in CI, passing.
     - Partial.
   * - Documentation and presentation
     - 20
     - Generated docs, working example, clear presentation.
     - Missing.

Capstone B: An Architecture and Cost Review
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Review a real production infrastructure against the AWS Well-Architected
Framework, with evidence.

Students review ``smarter-infrastructure`` for security, reliability and cost, using code, plans,
static analysis and cost estimates, and propose prioritized changes, at least one as a diff.

**What students turn in:**

- A four- to six-page review.
- A cost model with two reduction options.
- A five-minute presentation.

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
     - Organized by pillar and question.
     - Named only.
   * - Evidence
     - 25
     - Every finding cited.
     - Opinions.
   * - Cost model
     - 20
     - Complete, with trade-offs.
     - Partial.
   * - Recommendations
     - 20
     - Prioritized; one as a diff.
     - Unprioritized.
   * - Presentation
     - 15
     - Clear and on time.
     - Overruns.

Recommended Texts
-----------------

- **Required:** Yevgeniy Brikman, *Terraform: Up & Running* (3rd edition, O'Reilly, 2022). Week 1:
  chapters 1 to 4 (state and modules). Week 2: chapters 5 to 10 (tips, secrets, multiple
  providers, production-grade code, testing and teamwork).
- **Required:** the security and cost optimization pillars of the `AWS Well-Architected Framework
  <https://aws.amazon.com/architecture/well-architected/>`__, in week 2.
- **Smarter documentation:** :doc:`/smarter-platform/cloud-infrastructure`,
  :doc:`/smarter-framework/technologies/aws` and
  :doc:`/smarter-framework/technologies/infrastructure`.

Further Study
-------------

.. include:: further-study.txt
