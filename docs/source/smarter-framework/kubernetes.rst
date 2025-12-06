Kubernetes
==================

`Kubernetes <https://kubernetes.io/>`__ is an open-source platform designed to automate deploying, scaling,
and operating containerized applications. It provides a robust framework for
running distributed systems resiliently, handling scaling and failover, and
managing application updates seamlessly. Kubernetes has gained popularity
because it enables organizations to efficiently manage complex applications at scale.
It improves resource utilization, and supports cloud-native development practices.

The Smarter Framework includes a Helm chart for deploying Smarter on Kubernetes. The chart is located in ``helm/charts/smarter``.

Installation
------------

.. code-block:: bash

   helm repo add project-smarter https://project-smarter.github.io/helm-charts/
   helm install my-release project-smarter/smarter -f my-values.yaml

Examples
--------

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
-----

- `Helm Chart Source <https://github.com/smarter-sh/smarter/tree/main/helm/charts/smarter>`_
- `Published Chart on Artifact Hub <https://artifacthub.io/packages/helm/project-smarter/smarter>`_
- `DockerHub Repository <https://hub.docker.com/r/mcdaniel0073/smarter>`_

Configuration
-------------

The chart can be configured using the following values:

.. literalinclude:: ../../../helm/charts/smarter/values.yaml
   :language: yaml
