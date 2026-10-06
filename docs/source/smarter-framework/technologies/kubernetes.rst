Kubernetes
==================

`Kubernetes <https://kubernetes.io/>`__ is an open-source platform designed to automate deploying, scaling,
and operating containerized applications. It provides a robust framework for
running distributed systems resiliently, handling scaling and failover, and
managing application updates seamlessly. Kubernetes has gained popularity
because it enables organizations to efficiently manage complex applications at scale.
It improves resource utilization, and supports cloud-native development practices.

The Kubernetes Service
----------------------

Smarter manages the resources of its Kubernetes cluster, for example the Ingress of each
LLMClient, and the StatefulSet of each self-hosted vectorstore, with the Kubernetes service of
the :doc:`infrastructure services <infrastructure>`. It uses
`kubectl <https://kubernetes.io/docs/reference/kubectl/>`__, the command-line tool for
Kubernetes, with the kubeconfig that the cloud provider writes, for example with
``aws eks update-kubeconfig`` for AWS EKS. kubectl works the same with any cluster, so the
service does not depend on the cloud.

.. code-block:: python

  from string import Template
  from smarter.apps.infrastructure.services import infrastructure

  with open("k8s/ingress.yaml.tpl", encoding="utf-8") as ingress_template:
      template = Template(ingress_template.read())
      manifest = template.substitute(ingress_values)
  infrastructure.kubernetes.apply_manifest(manifest)

Applying a manifest that provisions billable cloud resources, for example a
PersistentVolumeClaim, which provisions a block storage volume, or a Service of type
LoadBalancer, sends the infrastructure's billable resource signals, and records the resources
in the infrastructure resource ledger.

.. toctree::
   :maxdepth: 1
   :caption: Kubernetes Service Technical Reference

   kubernetes/helper.rst

Helm Chart
----------

The Smarter Framework includes a Helm chart for deploying Smarter on Kubernetes. The chart is published at `ArtifactHUB - Smarter <https://artifacthub.io/packages/helm/project-smarter/smarter>`__.

Installation
~~~~~~~~~~~~~~~

.. code-block:: bash

   helm repo add project-smarter https://project-smarter.github.io/helm-charts/
   helm install my-release project-smarter/smarter -f my-values.yaml

Examples
~~~~~~~~~~~~~~~

.. code-block:: yaml

  # Example values.yaml
  app:
    replicaCount: 2
    resources:
      requests:
        cpu: "500m"
        memory: "1Gi"
      limits:
        cpu: "2"
        memory: "4Gi"

Links
~~~~~~~~~~~~

- `Helm Chart Source <https://github.com/smarter-sh/smarter-helm>`_
- `Published Chart on Artifact Hub <https://artifacthub.io/packages/helm/project-smarter/smarter>`_
- `DockerHub Repository <https://hub.docker.com/r/mcdaniel0073/smarter>`_

Configuration
~~~~~~~~~~~~~~~~~~

The chart can be configured using the following values:

.. literalinclude:: ../../../../helm/charts/smarter/values.yaml
   :language: yaml
