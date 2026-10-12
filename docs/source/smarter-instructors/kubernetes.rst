Kubernetes for Running Applications at Scale
============================================

**Why Smarter.** The Helm chart deploys the same images that students ran in Docker Compose, so the
course can start from something familiar and add only what Kubernetes brings: horizontal scaling,
ingress, secrets and network policies. Smarter also *manages* Kubernetes itself, deploying
LLMClients and self-hosted models as workloads, which is a good example of an application that
talks to the cluster's API.

**Look at.** ``helm/charts/smarter/``, and the Kubernetes service layer in
``smarter/smarter/apps/infrastructure/``.

**Read.** :doc:`/smarter-framework/smarter-on-kubernetes`,
:doc:`/smarter-framework/technologies/kubernetes`, :doc:`/smarter-platform/cloud-infrastructure`,
:doc:`ADR 003 on Kubernetes </adr/003-kubernetes>`.

**Exercises.**

- Install Smarter with the Helm chart on a local cluster, such as kind, minikube or the one built
  into Docker Desktop, and compare each Kubernetes object with its Docker Compose service.
- Load test a deployed LLMClient, and watch the autoscaler add pods.
- Write a network policy that stops a pod from reaching the cloud provider's metadata address.

**What it costs.** A class that runs Smarter on a managed Kubernetes cluster in the cloud should
expect a baseline infrastructure cost of around $350 USD a month, for the cluster, its nodes, the
load balancer, the database and the other services that Smarter needs. This grows very slightly
with each student: the variable cloud infrastructure cost per student is significantly less than
a dollar a month. Model provider charges are separate, and are controlled with
:doc:`Budgets </smarter-resources/smarter-budget>`. A local cluster, such as kind or minikube,
costs nothing and is enough for most of the exercises above.

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
