Installation
============

There are three ways to install Smarter. Choose the one that best suits your needs.

1. **Quick Start: Docker on your computer**

   The quickest way to get Smarter up and running on your desktop. A Docker
   Compose-based deployment runs all components of the platform in Docker
   containers on your local machine. This method is ideal for evaluating the
   platform, and for personal use. Follow the :doc:`Quick Start Guide <installation/quick-start>`.

2. **Local Development: from source code**

   Build and run the application locally from source code, using Docker Compose.
   This method is ideal for developers who want to contribute to the project,
   or who want to customize the application for their own use. Follow the
   :doc:`Developer Installation Guide <installation/developer-installation>`.

3. **Production: Kubernetes on AWS**

   Deploy Smarter to a production environment using AWS and Kubernetes. This
   method is ideal for organizations that want to use Smarter in a production
   setting, and who have the resources to manage a production deployment.
   Follow the :doc:`Production Deployment guide <installation/production-deployment>`.

   .. note::

      Hosting Smarter in production is complex and skills intensive. A production
      deployment involves a Kubernetes cluster, a database server, extensive knowledge
      of networking and Internet security, a broad range of cloud services, backups and
      upgrades, and someone who keeps all of it running. If you would rather not do this
      yourself, a `Certified Smarter Cloud Hosting Provider <https://smarter.sh/#services>`_
      can install, host and support a Kubernetes deployment of Smarter for you.
