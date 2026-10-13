Kubernetes: Two-Week Online Course
==================================

A two-week online course on running applications at scale with Kubernetes, taught by installing
Smarter's Helm chart on a local cluster. Smarter's `Helm chart
<https://github.com/smarter-sh/smarter/tree/main/helm/charts/smarter>`__ is the one that runs it in
production: four Deployments from the same image as Docker Compose, liveness, readiness and startup
probes, `autoscalers
<https://github.com/smarter-sh/smarter/blob/main/helm/charts/smarter/templates/hpa-app.yaml>`__ that
scale the web server from 3 to 25 pods, an init Job, a backup CronJob, Bitnami subcharts for the
database, Redis and monitoring, and `values
<https://github.com/smarter-sh/smarter/blob/main/helm/charts/smarter/values.yaml>`__ validated by a
`JSON Schema
<https://github.com/smarter-sh/smarter/blob/main/helm/charts/smarter/values.schema.json>`__. Smarter
also manages Kubernetes itself, creating an ingress for each deployed LLMClient and a Deployment,
Service and GPU node group for each self-hosted model. There are six 30-minute recorded lectures and
a 90-minute live session each week. Week 1 covers Kubernetes objects and Helm, and week 2 covers
scaling, networking and operations. See :doc:`../course-formats` for the format, the grading scale
and the course policies, and :doc:`../kubernetes` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers, operations and platform engineers who know Docker.
   * - **Deployment**
     - Each student runs a local cluster (kind, minikube or Docker Desktop's) with ``kubectl`` and
       ``helm``. 16 GB of memory is recommended.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free on local clusters.

.. warning::

   Students work only on their own local clusters, and check ``kubectl config current-context``
   before every command that changes anything.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain the control plane, nodes and the main Kubernetes objects.
2. Install, configure and upgrade an application with Helm, and read a chart.
3. Map Docker Compose services to Kubernetes objects.
4. Scale applications horizontally, with requests, limits, probes and autoscalers.
5. Secure cluster networking with network policies, and operate an application on a cluster.

Technical Prerequisites
-----------------------

- **Required:** Docker and Compose (see the :doc:`Docker course <../docker>`).
- **Required:** the Linux command line, YAML, Git and a GitHub account.
- **Required:** basic networking: IP addresses, ports, DNS and HTTP.
- **Required before Live session 1:** a local cluster with ``kubectl get nodes`` and
  ``helm version`` working.
- **Helpful:** load balancers, reverse proxies, and cloud experience.

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
     - **Why Kubernetes.** What Compose cannot do, the control plane and nodes, the declarative
       model, and :doc:`ADR 003 </adr/003-kubernetes>`.
   * - 1
     - Lecture 2 (30 min)
     - **Core objects.** Pods, Deployments, ReplicaSets, Services, ConfigMaps, Secrets and Jobs.
   * - 1
     - Lecture 3 (30 min)
     - **Helm.** Charts, templates, values, releases and subcharts, through
       ``helm/charts/smarter/``.
   * - 1
     - Live session 1 (90 min)
     - Cluster triage, then a live install of the Smarter chart. Pairs map Compose services to
       Kubernetes objects. Start Assignment 1.
   * - 2
     - Lecture 4 (30 min)
     - **Scaling.** Requests, limits, probes and the Horizontal Pod Autoscaler, and the chart's
       ``hpa-app`` and ``hpa-worker`` templates.
   * - 2
     - Lecture 5 (30 min)
     - **Networking.** Services, Ingress, cluster DNS, network policies, and the metadata address.
       How Smarter :doc:`deploys an LLMClient
       </smarter-framework/smarter-on-kubernetes/llmclient-deploy>`.
   * - 2
     - Lecture 6 (30 min)
     - **Operations.** Logs, events, upgrades, backups and managed clusters
       (:doc:`/smarter-framework/smarter-on-kubernetes/operations`).
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

Assignment 1: Install and Map
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students install the Smarter chart on a local cluster, and map each Compose service to the
Kubernetes objects that replace it.

**Turn in:** a values file, ``kubectl get all`` output, and a mapping table with explanation.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Installation
     - 6
     - All pods running; login works.
     - Pods failing.
   * - Mapping
     - 8
     - Every service mapped correctly, including subcharts.
     - Errors or gaps.
   * - Differences
     - 6
     - Explains what Kubernetes adds.
     - Lists objects only.

Assignment 2: Autoscaling Report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students load test the web service and report how the autoscaler responded.

**Turn in:** a chart of load, pods and response time, and a one-page analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Test design
     - 5
     - Stepped load, held, then removed.
     - Single burst.
   * - Data
     - 6
     - Pods, CPU and response time over time.
     - One metric.
   * - Analysis
     - 6
     - Explains lag and scale-down.
     - Describes only.
   * - Recommendation
     - 3
     - Better settings proposed.
     - None.

Assignment 3: Network Policy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write network policies that stop Smarter's pods from reaching ``169.254.169.254`` while
keeping the application working, on a cluster whose network plugin enforces policies (for example
kind with Calico).

**Turn in:** the policies, and evidence of a blocked and an allowed connection.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Policies
     - 7
     - Correct selectors; only needed traffic allowed.
     - Too broad, or breaks the app.
   * - Evidence
     - 7
     - Blocked and allowed connections shown.
     - Not demonstrated.
   * - Explanation
     - 6
     - Explains SSRF and the metadata address.
     - Not explained.

Capstone Projects
-----------------

Students choose one, and present it in Live session 2.

Capstone A: A Hardened Smarter Installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Make a working Helm installation production-ready in security and
resilience, with evidence.

Students harden their installation with resource requests and limits, probes, Pod Disruption
Budgets, default-deny network policies, and non-root security contexts, and demonstrate each
control.

**What students turn in:**

- A repository with the values file, manifests and a ``README.md``.
- Evidence for each control.
- A five-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Resources and probes
     - 20
     - Every pod.
     - Some.
   * - Network policies
     - 25
     - Default deny; app works; metadata blocked.
     - Breaks the app.
   * - Resilience
     - 20
     - Disruption budgets demonstrated.
     - Not shown.
   * - Evidence
     - 20
     - Every control shown working.
     - Claims only.
   * - Documentation and presentation
     - 15
     - Reproducible; clear.
     - Missing steps.

Capstone B: Your Own Application on Kubernetes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Package a multi-process application as a Helm chart, following the patterns
of a real one.

Students write a chart for their own application with web and worker Deployments, a Service, an
Ingress, a ConfigMap, a Secret, a migration Job and an autoscaler.

**What students turn in:**

- A repository with the chart and ``README.md``.
- Proof of ``helm install``, ``helm upgrade`` and ``helm lint``.
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
     - 25
     - Installs and upgrades cleanly.
     - Manual fixes.
   * - Chart design
     - 20
     - Values, helpers, labels.
     - Hard-coded.
   * - Objects
     - 20
     - All required, configured correctly.
     - Some missing.
   * - Production readiness
     - 15
     - Probes, resources, autoscaler.
     - None.
   * - Documentation and presentation
     - 20
     - Clear.
     - Missing.

Recommended Texts
-----------------

- **Required:** Brendan Burns, Joe Beda, Kelsey Hightower and Lachlan Evenson, *Kubernetes: Up and
  Running* (3rd edition, O'Reilly, 2022). Week 1: the chapters on pods, labels, service discovery,
  ReplicaSets, Deployments and Jobs. Week 2: the chapters on Ingress, ConfigMaps and Secrets, and
  role-based access control.
- **Reference:** Matt Butcher, Matt Farina and Josh Dolitsky, *Learning Helm* (O'Reilly, 2021).
- **Smarter documentation:** :doc:`/smarter-framework/smarter-on-kubernetes`,
  :doc:`/smarter-framework/technologies/kubernetes` and :doc:`/adr/003-kubernetes`.

Further Study
-------------

.. include:: further-study.txt
