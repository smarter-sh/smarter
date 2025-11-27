Deploy
======

Since Smarter is a Docker-based web application and REST API, deployment is
typically handled via container orchestration platforms such as Kubernetes,
Docker Swarm, or cloud-based services like AWS ECS or Azure Container Instances.

Local
-----

To deploy Smarter locally for development or testing purposes, you can use this `docker-compose.yml <https://github.com/smarter-sh/smarter/blob/main/docker-compose.yml>`__
file located in the root of the Smarter repository with Docker Compose. Ensure you have Docker and Docker Compose installed on your machine.
Note that Docker Desktop installs both Docker and Docker Compose for you.

.. code-block:: console

   make run

See `Makefile <https://github.com/smarter-sh/smarter/blob/main/Makefile#L44>`__ for additional deployment options.


Production
-----------

For production deployments, you can utilize cloud platforms such as AWS, Google Cloud Platform, or Microsoft Azure.
You can use this `reference GitHub Actions workflow <https://github.com/smarter-sh/smarter/blob/main/.github/workflows/deploy.yml>`__
as a starting point for your own CI/CD pipeline. This workflow deploys the Smarter cloud platform to an AWS Elastic Kubernetes Service (EKS) cluster.

Kubernetes
-----------

The Smarter project maintains a Helm chart located in the `./helm/charts/smarter <https://github.com/smarter-sh/smarter/tree/main/helm/charts/smarter>`__
directory of the smarter repository. This chart is published to `https://artifacthub.io/packages/helm/project-smarter/smarter <https://artifacthub.io/packages/helm/project-smarter/smarter>`__
and is regularly updated with each new release. You can use this Helm chart to deploy Smarter to any Kubernetes cluster.

You should also familiarize yourself with the Smarter Terraform modules located in `https://github.com/smarter-sh/smarter-infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`__
for provisioning the necessary AWS cloud infrastructure to run Smarter in production.
