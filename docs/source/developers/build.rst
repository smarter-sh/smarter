Build
=====

Smarter is a native Docker application. Regardless of your operating system and environment,
all builds utilize this `Dockerfile <https://github.com/smarter-sh/smarter/blob/main/Dockerfile>`__,
which is known to work for AMD64 and ARM64 architectures.

Local
-----

To build Smarter locally, run the following command in your terminal:

.. code-block:: console

  make build

See `Makefile <https://github.com/smarter-sh/smarter/blob/main/Makefile#L39>`__ for additional build targets and options.

Production
-----------

You can use this `reference GitHub Actions workflow <https://github.com/smarter-sh/smarter/blob/main/.github/workflows/build.yml>`__ to build and push Smarter images to
a private AWS Elastic Container Registry (ECR) repository. This workflow manages the Smarter production cloud platform builds and is known to work for both AMD64 and ARM64 architectures.
Initial Builds take approximately 30 minutes to complete due to the multi-architecture build process. Subsequent builds are
significantly faster due to caching, and usually take less than 5 minutes. Builds are approximately 850MB in size, but are split
into multiple layers for more efficient distribution, none which exceed 225MB.

Docker Hub
-----------

The Smarter project also maintains a public Docker Hub repository at `dockerhub.smarter.sh <https://hub.docker.com/r/mcdaniel0073/smarter>`__
which contains the latest stable release builds for both AMD64 and ARM64 architectures. This is the recommended way to obtain Smarter for most users.
You can pull the latest image with the following command:

.. code-block:: console

  docker pull mcdaniel0073/smarter:latest
