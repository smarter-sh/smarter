Kubernetes for Running Applications at Scale
============================================

**Why Smarter.** Kubernetes courses usually deploy a sample app that has none of the parts that
make Kubernetes worth learning: background workers, a database, a cache, secrets, autoscaling and
network isolation. Smarter has all of them, and its
`Helm chart <https://github.com/smarter-sh/smarter/tree/main/helm/charts/smarter>`__ is the one
that runs it in production. The chart deploys the same images that students ran in
:doc:`Docker Compose <docker>`, so the course can start from something familiar and add only what
Kubernetes brings:

- **The same image, as four Deployments:** the
  `web server <https://github.com/smarter-sh/smarter/blob/main/helm/charts/smarter/templates/deployment-app.yaml>`__,
  the worker, the infrastructure worker and the scheduler, with liveness, readiness and startup
  probes on ``/healthz/`` and ``/readiness/``.
- **Horizontal scaling:** `autoscalers <https://github.com/smarter-sh/smarter/blob/main/helm/charts/smarter/templates/hpa-app.yaml>`__
  that scale the web server from 3 to 25 pods at 75% CPU, and the worker on its own.
- **Lifecycle Jobs:** a post-install `init Job
  <https://github.com/smarter-sh/smarter/blob/main/helm/charts/smarter/templates/job-init.yaml>`__
  that creates the database, migrates and initializes the platform, and a CronJob that backs the
  database up to S3.
- **Configuration that is checked:** `values <https://github.com/smarter-sh/smarter/blob/main/helm/charts/smarter/values.yaml>`__
  validated by a `JSON Schema <https://github.com/smarter-sh/smarter/blob/main/helm/charts/smarter/values.schema.json>`__,
  and Bitnami subcharts for MySQL or MariaDB, Redis, Grafana, Prometheus and Loki, each switched on
  or off.
- **A production cluster to compare with:** in
  `smarter-infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`__, an EKS
  cluster on Spot node groups with the Cluster Autoscaler, Traefik and cert-manager for ingress,
  and Calico `network policies
  <https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/terraform/kubernetes/network_policy.tf>`__
  with default-deny ingress.

Smarter also *manages* Kubernetes itself, which is a good example of an application that talks to
the cluster's API. Deploying an LLMClient creates its own `ingress
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmclient/k8s/ingress.yaml.tpl>`__,
host name and certificate, and serving a self-hosted model with
:doc:`LLMHost </smarter-resources/smarter-llmhost>` `renders
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmhost/services/renderer.py>`__
a PersistentVolumeClaim, a Deployment, a Service and an Ingress, and creates an EKS node group of
GPU nodes on demand.

**What the course covers.** Why Kubernetes, and what Compose cannot do; the control plane, the
nodes and the reconciliation loop; Pods, Deployments, ReplicaSets, Services and Jobs; Helm charts,
templates, values, releases and subcharts, through Smarter's chart; ConfigMaps, Secrets, service
accounts and RBAC; requests, limits, probes and the Horizontal Pod Autoscaler; Services, Ingress,
cluster DNS and certificates; network policies, and blocking the cloud metadata address;
operations: logs, events, upgrades, backups and monitoring; applications that manage the cluster
themselves; and managed clusters, node groups and their cost.

**Look at.**

- `helm/charts/smarter/ <https://github.com/smarter-sh/smarter/tree/main/helm/charts/smarter>`__,
  the chart, its templates and its values schema.
- The `smarter-infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`__
  repository's ``kubernetes`` module, the production cluster.
- `smarter/smarter/apps/infrastructure/services/kubernetes.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/infrastructure/services/kubernetes.py>`__
  and `smarter/smarter/apps/llmhost/services/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/llmhost/services>`__,
  where the application manages the cluster.

Each course plan lists every file that it uses under *Smarter in the Source Code*.

**Read.** :doc:`/smarter-framework/smarter-on-kubernetes`,
:doc:`/smarter-framework/technologies/kubernetes`, :doc:`/smarter-platform/cloud-infrastructure`,
:doc:`ADR 003 on Kubernetes </adr/003-kubernetes>`, `One Image, Laptop to Production: The Case for
Smarter on Docker and Kubernetes <https://blog.smarter.sh/2026/04/11/smarter-docker-kubernetes/>`__,
`Route 53 and cert-manager: One DNS Record and One TLS Certificate per Deployed LLM
<https://blog.smarter.sh/2026/03/24/smarter-per-host-dns-tls/>`__, and the case study `What
Happens When You Click Deploy <https://smarter.sh/case-studies/deploy>`__.

**Exercises.**

- Install Smarter with the Helm chart on a local cluster, such as kind, minikube or the one built
  into Docker Desktop, and compare each Kubernetes object with its Docker Compose service.
- Load test the web service, and watch the autoscaler add pods.
- Write a network policy that stops a pod from reaching the cloud provider's metadata address,
  and compare it with the Calico policies in ``smarter-infrastructure``.
- Read the LLMHost renderer, and list every Kubernetes object that a self-hosted model would
  create, and why each one is needed.

**What it costs.** A class that runs Smarter on a managed Kubernetes cluster in the cloud should
expect a baseline infrastructure cost of around $350 USD a month, for the cluster, its nodes, the
load balancer, the database and the other services that Smarter needs. This grows very slightly
with each student: the variable cloud infrastructure cost per student is significantly less than
a dollar a month. Model provider charges are separate, and are controlled with
:doc:`Budgets </smarter-resources/smarter-budget>`. A local cluster, such as kind or minikube,
costs nothing and is enough for most of the exercises above.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <kubernetes/bootcamp>
   Two-week online course: 6 hours <kubernetes/two-week>
   Four-week online course: 12 hours <kubernetes/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
