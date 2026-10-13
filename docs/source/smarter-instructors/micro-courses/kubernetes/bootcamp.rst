Kubernetes: Classroom Bootcamp
==============================

An eight-hour classroom bootcamp on running applications at scale with Kubernetes, taught by
installing Smarter's Helm chart on a local cluster. Students start from the Docker Compose services
they already know, and add only what Kubernetes brings: scheduling, scaling, ingress, secrets and
network policies. Smarter's `Helm chart
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
Service and GPU node group for each self-hosted model. See :doc:`../course-formats` for the standard
bootcamp day, the grading scale and the course policies, and :doc:`../kubernetes` for an overview of
the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers, operations and platform engineers who know Docker and want to learn Kubernetes.
   * - **Deployment**
     - Each student runs a local cluster (kind, minikube, or the one built into Docker Desktop)
       with the ``kubectl`` and ``helm`` command-line tools. A laptop with 16 GB of memory is
       recommended.
   * - **Cost**
     - Free on local clusters. See :doc:`../kubernetes` for the cost of a managed cluster in the
       cloud, which this bootcamp does not need.

.. warning::

   Students work only on their own local clusters. Never point the labs at a shared or production
   cluster, and check ``kubectl config current-context`` before every command that changes
   anything.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Explain the Kubernetes control plane, nodes, and the main objects: Pods, Deployments, Services,
   ConfigMaps, Secrets, Jobs and Ingresses.
2. Install an application with a Helm chart, and read the chart's templates and values.
3. Map each Kubernetes object to the Docker Compose service it replaces.
4. Scale an application horizontally, and observe the autoscaler.
5. Write a network policy, and explain why the cloud metadata address must be blocked.

Technical Prerequisites
-----------------------

- **Required:** Docker: images, containers, Compose, ``exec`` and ``logs``. The
  :doc:`Docker course <../docker>` covers this.
- **Required:** the Linux command line, YAML, and Git.
- **Required:** basic networking: IP addresses, ports, DNS and HTTP.
- **Required:** a local cluster running, with ``kubectl get nodes`` and ``helm version`` working,
  before the bootcamp.
- **Helpful:** the concepts of a load balancer and a reverse proxy, and some cloud experience.

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
     - **Lecture 1: Why Kubernetes.** What Compose cannot do: many machines, self-healing, rolling
       updates, scaling. The control plane and nodes, the declarative model, and
       :doc:`ADR 003 on Kubernetes </adr/003-kubernetes>`.
   * - 2
     - 45
     - **Lab 1: Objects by hand.** Create a Deployment and a Service for a small web image with
       ``kubectl``, scale it, delete a pod and watch it come back, and roll out a new version.
       Produces Assignment 1.
   * - 3
     - 45
     - **Lecture 2: Helm.** Charts, templates, values and releases. A tour of
       ``helm/charts/smarter/``: the app, worker, beat and infrastructure worker Deployments, the
       init Job, the Service, the autoscalers and the ConfigMaps, and the subcharts for the
       database, Redis and monitoring, with ``database.type`` to use an external database instead.
   * - 4
     - 45
     - **Lab 2: Install Smarter.** Install the chart on the local cluster with a local values file,
       watch the init Job seed the database, and log in. Produces Assignment 2.
   * - 5
     - 45
     - **Lecture 3: Configuration and secrets.** ConfigMaps, Secrets, environment variables and
       mounted files, and what a Kubernetes Secret does and does not protect.
   * - 6
     - 45
     - **Lecture 4: Scaling.** Requests and limits, the Horizontal Pod Autoscaler, readiness and
       liveness probes, and how Smarter's ``hpa-app`` and ``hpa-worker`` templates scale the web
       and worker pods.
   * - 7
     - 45
     - **Lab 3: Load test.** Install the metrics server, load test the web service, and watch the
       autoscaler add pods. Record pods, CPU and response times. Produces Assignment 3.
   * - 8
     - 45
     - **Lecture 5: Networking.** Services, Ingress, DNS inside the cluster, and network policies.
       Server-side request forgery and the cloud metadata address. How Smarter
       :doc:`deploys an LLMClient </smarter-framework/smarter-on-kubernetes/llmclient-deploy>` with
       its own ingress.
   * - 9
     - 45
     - **Lab 4: Fence it in.** Write a network policy that stops Smarter's pods from reaching
       ``169.254.169.254`` while still reaching the database, Redis and the internet, and test it
       (on a cluster whose network plugin enforces policies). Ungraded.
   * - 10
     - 45
     - **Lecture 6: Operating a cluster.** Logs, events, ``kubectl describe``, upgrades, backups
       (the chart's backup CronJob to S3), the bastion pod, managed clusters in the cloud with
       Spot node groups and the Cluster Autoscaler, and what they cost.
       :doc:`/smarter-framework/smarter-on-kubernetes/operations`.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone and plan it.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Self-Healing and Rollouts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students show a Deployment healing itself after a pod is deleted, scaling, rolling out a new image
and rolling back, with the commands and output.

**Turn in:** the manifests and a terminal log with commentary.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Manifests
     - 5
     - Valid, with labels, selectors and resource requests.
     - Created imperatively, or missing labels.
   * - Self-healing and scaling
     - 5
     - Both demonstrated.
     - One only.
   * - Rollout and rollback
     - 6
     - Both demonstrated, with ``kubectl rollout`` history.
     - Rollout only.
   * - Commentary
     - 4
     - Explains what the controller did at each step.
     - Raw output.

Assignment 2: Compose to Kubernetes Map
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students map each service in ``docker-compose.yml`` to the Kubernetes objects in the Helm chart
that replace it, and list what Kubernetes adds or handles differently.

**Turn in:** a table and a one-page explanation, with evidence that the chart is installed.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Installation
     - 4
     - Chart installed; all pods running.
     - Some pods failing.
   * - Mapping
     - 8
     - Every service mapped correctly, including the database and Redis.
     - Errors or gaps.
   * - Differences
     - 6
     - Explains scaling, Jobs, Secrets and Services versus Compose.
     - Lists objects without comparison.
   * - Clarity
     - 2
     - Clear.
     - Unclear.

Assignment 3: Autoscaling Report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students load test the web service and report how the autoscaler responded.

**Turn in:** a chart of load, pod count and response time over time, and a one-page analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Test design
     - 5
     - Load increased in steps, held, then removed.
     - A single burst.
   * - Data
     - 6
     - Pods, CPU and response times over time.
     - One metric.
   * - Analysis
     - 6
     - Explains the lag and the scale-down behavior.
     - Describes without explaining.
   * - Recommendation
     - 3
     - Proposes better requests, limits or thresholds.
     - None.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp.

Capstone A: A Hardened Smarter Installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Take a working Helm installation and make it production-ready in security
and resilience, with evidence.

Students harden their local installation with a values file and extra manifests: resource requests
and limits on every pod, probes, Pod Disruption Budgets, network policies (including the metadata
address), and a non-root security context, and demonstrate that each works.

**What students turn in:**

- A Git repository with the values file, extra manifests and a ``README.md``.
- Evidence for each control: a blocked connection, a pod restarted by a failed probe, a drain that
  respects the disruption budget.
- A one-page explanation of each choice.

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
     - Realistic requests, limits and probes on every pod.
     - Some pods only.
   * - Network policies
     - 25
     - Default deny, with the needed paths allowed; metadata address blocked.
     - A single policy, or one that breaks the app.
   * - Resilience
     - 20
     - Disruption budgets and replicas demonstrated.
     - Not demonstrated.
   * - Evidence
     - 20
     - Each control shown working.
     - Claims without evidence.
   * - Documentation
     - 15
     - Reproducible from the ``README.md``.
     - Missing steps.

Capstone B: Your Own Application on Kubernetes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Package a multi-process application as a Helm chart, following the patterns
of a real one.

Students write a Helm chart for an application of their own (or their Docker capstone) with a web
Deployment, a worker Deployment, a Service, an Ingress, a ConfigMap, a Secret, an init or migration
Job, and an autoscaler, modeled on Smarter's chart.

**What students turn in:**

- A Git repository with the chart and a ``README.md``.
- Proof that ``helm install`` and ``helm upgrade`` work on a local cluster, and that ``helm lint``
  passes.
- A one-page comparison with Smarter's chart.

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
     - Needs manual fixes.
   * - Chart design
     - 20
     - Sensible values, helpers, labels.
     - Hard-coded values.
   * - Objects
     - 20
     - All required objects, correctly configured.
     - Some missing.
   * - Production readiness
     - 15
     - Probes, resources, autoscaler.
     - None.
   * - Documentation
     - 20
     - Clear ``README.md`` and comparison.
     - Missing.

Recommended Texts
-----------------

- **Pre-reading:** the `Kubernetes Basics tutorial
  <https://kubernetes.io/docs/tutorials/kubernetes-basics/>`__.
- **Reference:** Brendan Burns, Joe Beda, Kelsey Hightower and Lachlan Evenson, *Kubernetes: Up and
  Running* (3rd edition, O'Reilly, 2022).
- **Smarter documentation:** :doc:`/smarter-framework/smarter-on-kubernetes`,
  :doc:`/smarter-framework/technologies/kubernetes`, :doc:`/smarter-platform/cloud-infrastructure`
  and :doc:`/adr/003-kubernetes`.

Further Study
-------------

.. include:: further-study.txt
