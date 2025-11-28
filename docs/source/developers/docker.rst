Docker Reference
================

What is Docker?
---------------

Docker is an open-source platform that enables you to automate the deployment, scaling, and management of applications using lightweight, portable containers.
Containers package your application code together with all dependencies, including for example the runtime operating system, libraries, and system tools,
ensuring consistency across development, testing, and production environments.

Why Use Docker?
---------------

- **Consistency:** Run the same application across different environments without "it works on my machine" issues.
- **Isolation:** Each container runs independently, reducing conflicts between applications.
- **Portability:** Containers can run anywhere Docker is supported (Windows, macOS, Linux, cloud).
- **Efficiency:** Containers are lightweight and start quickly.

Smarter and Docker
-------------------

Optimized Builds
~~~~~~~~~~~~~~~~~~

The Smarter Dockerfile begins with a novel base image declaration that helps to minimize image size while ensuring compatibility and performance.

.. code-block:: docker

   FROM python:3.12-slim-trixie AS linux_base

python:3.12-slim-trixie includes the latest Python 3.12, installed on a minimal Debian 13 ("Trixie") operating system base
which is optimized for size and performance. The Dockerfile is laid out in stages (eg, layers),
ordered to optimize build caching and minimize final image size.

Other Key Elements
~~~~~~~~~~~~~~~~~~
While the full Dockerfile may include additional instructions, typical elements are:

- **Dependency Installation**: Installs system and Python dependencies required for the application.
- **Copying Source Code**: Copies project files into the image.
- **Setting Work Directory**: Uses ``WORKDIR`` to define the working directory for subsequent commands.
- **Environment Variables**: Sets environment variables for configuration.
- **Entrypoint or CMD**: Specifies how the container should start the application.
- **Multi-Stage Build**: Uses the named stage (``linux_base``) to optimize the final image by copying only necessary files and dependencies.



Getting Started with Docker
---------------------------

If you are new to Docker, we recommend the following trusted resources:

**Official Docker Documentation**

- `Get Started with Docker <https://docs.docker.com/get-started/>`__ – The official step-by-step guide for beginners.
- `Docker Overview <https://docs.docker.com/engine/docker-overview/>`__ – High-level introduction to Docker concepts.

**Video Tutorials**

- `Docker for Beginners – Full Course (YouTube, freeCodeCamp) <https://www.youtube.com/watch?v=fqMOX6JJhGo>`__ – A comprehensive, beginner-friendly video tutorial.
- `Docker in 100 Seconds (YouTube, Fireship) <https://www.youtube.com/watch?v=Gjnup-PuquQ>`__ – A fast-paced, visual introduction to Docker basics.

**Interactive Learning**

- `Play with Docker <https://labs.play-with-docker.com/>`__ – Try Docker in your browser, no installation required.

Key Docker Concepts
-------------------

- **Image:** A snapshot of your application and its dependencies.
- **Container:** A running instance of an image.
- **Dockerfile:** A text file with instructions to build a Docker image.
- **Docker Compose:** A tool for defining and running multi-container Docker applications.

Basic Commands
--------------

.. code-block:: bash

   # Check Docker version
   docker --version

   # List running containers
   docker ps

   # Build an image from a Dockerfile
   docker build -t my-image .

   # Run a container from an image
   docker run -p 8000:8000 my-image

   # Stop all running containers
   docker stop $(docker ps -q)

   # Remove all stopped containers
   docker container prune

Next Steps
----------

- Review the `Smarter Dockerfile <https://github.com/smarter-sh/smarter/blob/main/Dockerfile>`__ and `docker-compose.yml <https://github.com/smarter-sh/smarter/blob/main/docker-compose.yml>`__ for project-specific usage.
- See the `Quickstart <../index.html#quickstart>`__ section for how Docker is used in this project.

For more advanced topics, refer to the `Docker Documentation <https://docs.docker.com/>`__ or the `Docker YouTube Channel <https://www.youtube.com/@Docker>`__.
