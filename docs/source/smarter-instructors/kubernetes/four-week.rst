Kubernetes: Four-Week Online Course
===================================

A four-week online course on running applications at scale with Kubernetes, taught on Smarter's
Helm chart and on Smarter's own use of the Kubernetes API, with twelve 30-minute recorded lectures
and a 90-minute live session each week. Week 1 covers core objects, week 2 Helm and configuration,
week 3 scaling and networking, and week 4 operations and applications that manage the cluster
themselves. See :doc:`../course-formats` for the format, the grading scale and the course policies,
and :doc:`../kubernetes` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers, operations and platform engineers who know Docker.
   * - **Deployment**
     - Each student runs a local cluster with ``kubectl`` and ``helm``. An optional week 4 exercise
       uses a managed cluster in a sandbox cloud account, if the instructor provides one.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free on local clusters. A managed cluster for a few hours in week 4 costs a few dollars;
       destroy it after use.

.. warning::

   Students work only on their own clusters, and check ``kubectl config current-context`` before
   every command that changes anything.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain Kubernetes architecture and its main objects, and use them declaratively.
2. Write, install and upgrade Helm charts.
3. Configure applications with ConfigMaps and Secrets, and manage access with RBAC.
4. Scale applications with requests, limits, probes and autoscalers.
5. Secure cluster networking with network policies and ingress.
6. Operate applications on a cluster, and explain how an application can manage Kubernetes
   resources through its API.

Technical Prerequisites
-----------------------

- **Required:** Docker and Compose.
- **Required:** the Linux command line, YAML, Git and a GitHub account.
- **Required:** basic networking: IP addresses, ports, DNS and HTTP.
- **Required by the end of week 1:** a local cluster with ``kubectl`` and ``helm`` working.
- **Helpful:** reading Python (for week 4), and cloud experience.

Schedule
--------

.. list-table::
   :header-rows: 1
   :widths: 10 18 72

   * - Week
     - Item
     - Content
   * - 1
     - Lecture 1
     - **Why Kubernetes.** What Compose cannot do, and :doc:`ADR 003 </adr/003-kubernetes>`.
   * - 1
     - Lecture 2
     - **Architecture.** The API server, etcd, the scheduler, controllers, kubelets and the
       reconciliation loop.
   * - 1
     - Lecture 3
     - **Core objects.** Pods, Deployments, ReplicaSets, Services and Jobs.
   * - 1
     - Live session 1
     - Cluster triage, then self-healing and rollouts, live. Start Assignment 1.
   * - 2
     - Lecture 4
     - **Helm.** Charts, templates, values, releases and subcharts.
   * - 2
     - Lecture 5
     - **Smarter's chart.** A tour of ``helm/charts/smarter/``: Deployments, the init and backup
       Jobs, the autoscalers, the database options and the ConfigMaps.
   * - 2
     - Lecture 6
     - **Configuration and access.** ConfigMaps, Secrets, service accounts and RBAC.
   * - 2
     - Live session 2
     - Review of Assignment 1. A live install of Smarter's chart. Start Assignment 2.
   * - 3
     - Lecture 7
     - **Scaling.** Requests, limits, probes and the Horizontal Pod Autoscaler.
   * - 3
     - Lecture 8
     - **Networking.** Services, Ingress, cluster DNS, and certificates.
   * - 3
     - Lecture 9
     - **Network policies.** Default deny, allow rules, and blocking the metadata address.
   * - 3
     - Live session 3
     - Review of Assignment 2. Load testing and autoscaling, live. Capstone proposals discussed.
       Start Assignment 3.
   * - 4
     - Lecture 10
     - **Operations.** Logs, events, upgrades, backups, monitoring with the chart's Grafana and
       Loki subcharts, and :doc:`/smarter-framework/smarter-on-kubernetes/operations`.
   * - 4
     - Lecture 11
     - **Applications that manage Kubernetes.** How Smarter
       :doc:`deploys LLMClients </smarter-framework/smarter-on-kubernetes/llmclient-deploy>` with
       their own ingress, and serves models with :doc:`LLMHost </smarter-resources/smarter-llmhost>`,
       through the Kubernetes service layer in ``smarter/smarter/apps/infrastructure/``.
   * - 4
     - Lecture 12
     - **Managed clusters and cost.** EKS and its peers, node groups, autoscaling nodes, and the
       cost figures in :doc:`../kubernetes`.
   * - 4
     - Live session 4
     - Capstone presentations (about 6 minutes each, with 2 minutes of questions), and a course
       retrospective.

Assignments 1 to 3 are due before the next live session. Assignment 4 is due in the middle of week
4. The capstone proposal is due before Live session 3, and the capstone at the start of Live
session 4.

Graded Assignments
------------------

Assignment 1: Self-Healing and Rollouts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students deploy a small web application declaratively, and show self-healing, scaling, a rolling
update, a failed update caught by a readiness probe, and a rollback.

**Turn in:** manifests and a commented terminal log.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Manifests
     - 4
     - Declarative, labeled, with resources.
     - Imperative.
   * - Healing and scaling
     - 4
     - Both shown.
     - One.
   * - Rollouts
     - 8
     - Success, probe-blocked failure, and rollback.
     - Success only.
   * - Commentary
     - 4
     - Explains the controllers' actions.
     - Raw output.

Assignment 2: Install, Configure and Map
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students install Smarter's chart with their own values file, choosing the database option
deliberately, map Compose services to Kubernetes objects, and explain how configuration and
secrets reach the pods.

**Turn in:** the values file, cluster output, and a two-page explanation.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Installation
     - 5
     - All pods running; login works.
     - Failures.
   * - Values
     - 4
     - Deliberate choices, explained; no real secrets committed.
     - Defaults copied, or secrets committed.
   * - Mapping
     - 6
     - Complete and correct.
     - Gaps.
   * - Configuration path
     - 5
     - Traces values to ConfigMaps, Secrets and environment variables.
     - Vague.

Assignment 3: Scaling and Policies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students load test the web service and report on the autoscaler, then write network policies that
block the metadata address and anything else the application does not need.

**Turn in:** a chart and analysis, the policies, and evidence.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Load test
     - 6
     - Stepped load; pods, CPU and latency recorded.
     - Single burst.
   * - Analysis
     - 4
     - Explains lag and scale-down.
     - Describes.
   * - Policies
     - 6
     - Default deny, needed paths allowed.
     - Too broad, or breaks the app.
   * - Evidence
     - 4
     - Blocked and allowed connections shown.
     - None.

Assignment 4: How Smarter Drives Kubernetes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students read the Kubernetes parts of ``smarter/smarter/apps/infrastructure/`` and the LLMClient
deployment code, and explain which objects Smarter creates when an LLMClient is deployed, what
permissions it needs, and how its tests avoid touching a real cluster.

**Turn in:** a two-page explanation with a diagram and code references.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Objects
     - 6
     - Every object identified, with its purpose.
     - Some.
   * - Permissions
     - 5
     - Minimum RBAC needed, reasoned.
     - Not addressed.
   * - Testing
     - 5
     - Explains the fake provider and why it matters.
     - Not addressed.
   * - Clarity
     - 4
     - Clear diagram and references.
     - Unclear.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and present it in Live session 4.

Capstone A: A Production-Ready Smarter Platform
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design and demonstrate a production-ready installation of a real
application on Kubernetes, covering security, resilience, observability and upgrades.

Students build a complete installation of Smarter on a local cluster (or a sandbox managed cluster):
hardened values, network policies, disruption budgets, monitoring with Grafana and Loki, a tested
backup and restore, and a zero-downtime upgrade.

**What students turn in:**

- A repository with values files, manifests and a runbook.
- Evidence of each control, a restore, and an upgrade under load with no failed requests.
- A six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Security
     - 20
     - Network policies, non-root, RBAC, secrets handled well.
     - Partial.
   * - Resilience
     - 20
     - Disruption budgets, replicas, probes, restore tested.
     - Untested backup.
   * - Observability
     - 15
     - Dashboards and logs that answer real questions.
     - Installed but unused.
   * - Zero-downtime upgrade
     - 20
     - Demonstrated under load.
     - Not demonstrated.
   * - Runbook and presentation
     - 25
     - Another engineer could operate it.
     - Missing steps.

Capstone B: A Helm Chart and Operations Guide for Your Own Application
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Package and operate a multi-process application on Kubernetes, following
the patterns of a real chart.

Students write a Helm chart for their own application, with web and worker Deployments, a
migration Job, a Service, an Ingress, ConfigMaps, Secrets, autoscalers, network policies and a
database subchart or external database option, and write an operations guide.

**What students turn in:**

- A repository with the chart, CI that runs ``helm lint`` and a test install on kind, and a
  ``README.md``.
- An operations guide: install, upgrade, scale, back up, restore and troubleshoot.
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
     - Installs and upgrades cleanly, in CI.
     - Manual fixes.
   * - Chart design
     - 20
     - Values, helpers, subcharts, labels.
     - Hard-coded.
   * - Production readiness
     - 20
     - Probes, resources, autoscalers, policies.
     - Missing.
   * - Operations guide
     - 25
     - Complete and tested.
     - Untested.
   * - Presentation
     - 15
     - Clear and on time.
     - Overruns.

Recommended Texts
-----------------

- **Required:** Brendan Burns, Joe Beda, Kelsey Hightower and Lachlan Evenson, *Kubernetes: Up and
  Running* (3rd edition, O'Reilly, 2022), across weeks 1 to 3.
- **Required:** Matt Butcher, Matt Farina and Josh Dolitsky, *Learning Helm* (O'Reilly, 2021), in
  week 2.
- **Required:** Bilgin Ibryam and Roland Huß, *Kubernetes Patterns* (2nd edition, O'Reilly,
  2023), selected patterns (health probe, managed lifecycle, declarative deployment, controller),
  in weeks 3 and 4.
- **Reference:** Josh Rosso, Rich Lander, Alex Brand and John Harris, *Production Kubernetes*
  (O'Reilly, 2021).
- **Smarter documentation:** :doc:`/smarter-framework/smarter-on-kubernetes`,
  :doc:`/smarter-framework/technologies/kubernetes`, :doc:`/smarter-platform/cloud-infrastructure`,
  :doc:`/smarter-resources/smarter-llmhost` and :doc:`/adr/003-kubernetes`.

Further Study
-------------

.. include:: further-study.txt
