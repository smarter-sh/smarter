Installation
============

Choose the installation method that best suits your needs.

- **Option 1: Local Docker Quick Start**

	The quickest way to get Smarter up and running on your desktop is to use
	the `Smarter Quick Start <./installation/quick-start.html>`_.
	This is a Docker Compose-based deployment that runs all components of the
	platform in Docker containers on your local machine. This method is ideal
	for evaluating the platform, and for personal use.

- **Option 2: Local Development**

	Follow the instructions in the `Developer Guide <../smarter-framework/guides/contributing.html>`_
	to build and run the application locally from source code, using Docker Compose.
	This method is ideal for developers who want to contribute to the project,
	or who want to customize the application for their own use.

- **Option 3: Production Kubernetes Installation**

	`Deploy Smarter to a production environment <./installation/production-deployment.html>`_
	using AWS and Kubernetes. This method is ideal for organizations that
	want to use Smarter in a production setting, and who have the resources to
	manage a production deployment.

.. note::

	Hosting Smarter in production is complex and skills intensive. A production deployment involves a
	Kubernetes cluster, a database server, extensive knowledge of networking and Internet security,
	a broad range of cloud services, backups and upgrades, and someone who keeps all of it running. If you would
	rather not do this yourself, a
	`Certified Smarter Cloud Hosting Provider <https://smarter.sh/#services>`_
	can install, host and support a Kubernetes deployment of Smarter for you.


.. toctree::
   :maxdepth: 1
   :caption: Self-Service Installation Guides

   installation/quick-start
   installation/production-deployment
   ../smarter-framework/guides/developer-setup

.. toctree::
   :hidden:
   :maxdepth: 1

   prerequisites
   cloud-infrastructure
   updates
   backup-and-restore
