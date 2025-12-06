Kubernetes
==================

`Kubernetes <https://kubernetes.io/>`__ is an open-source platform designed to automate deploying, scaling,
and operating containerized applications. It provides a robust framework for
running distributed systems resiliently, handling scaling and failover, and
managing application updates seamlessly. Kubernetes has gained popularity
because it enables organizations to efficiently manage complex applications at scale.
It improves resource utilization, and supports cloud-native development practices.

Kubernetes Helper Classes
---------------------------

The Smarter Framework provides helper classes to facilitate interaction with Kubernetes clusters, primarily via
the Kubernetes API vis a vis `kubectl <https://kubernetes.io/docs/reference/kubectl/>`__, the command-line tool for Kubernetes.

.. code-block:: python

  from smarter.common.helpers.k8s_helpers import kubernetes_helper

  with open("k8s/ingress.yaml.tpl", encoding="utf-8") as ingress_template:
      template = Template(ingress_template.read())
      manifest = template.substitute(ingress_values)
  kubernetes_helper.apply_manifest(manifest)


.. toctree::
   :maxdepth: 1
   :caption: Kubernetes Helper Class Technical Reference

   kubernetes/helper.rst

Helm Chart
----------

The Smarter Framework includes a Helm chart for deploying Smarter on Kubernetes. The chart is located in ``helm/charts/smarter``.

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

- `Helm Chart Source <https://github.com/smarter-sh/smarter/tree/main/helm/charts/smarter>`_
- `Published Chart on Artifact Hub <https://artifacthub.io/packages/helm/project-smarter/smarter>`_
- `DockerHub Repository <https://hub.docker.com/r/mcdaniel0073/smarter>`_

Configuration
~~~~~~~~~~~~~~~~~~

The chart can be configured using the following values:

.. literalinclude:: ../../../helm/charts/smarter/values.yaml
   :language: yaml
