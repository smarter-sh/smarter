Docker Reference
================

What is Docker?
---------------

Docker is an open-source platform that enables you to automate the deployment, scaling, and management of applications using lightweight, portable containers. Containers package your application code together with all dependencies, ensuring consistency across development, testing, and production environments.

Why Use Docker?
---------------

- **Consistency:** Run the same application across different environments without "it works on my machine" issues.
- **Isolation:** Each container runs independently, reducing conflicts between applications.
- **Portability:** Containers can run anywhere Docker is supported (Windows, macOS, Linux, cloud).
- **Efficiency:** Containers are lightweight and start quickly.

Getting Started with Docker
---------------------------

If you are new to Docker, we recommend the following trusted resources:

**Official Docker Documentation**

- [Get Started with Docker](https://docs.docker.com/get-started/) – The official step-by-step guide for beginners.
- [Docker Overview](https://docs.docker.com/engine/docker-overview/) – High-level introduction to Docker concepts.

**Video Tutorials**

- [Docker for Beginners – Full Course (YouTube, freeCodeCamp)](https://www.youtube.com/watch?v=fqMOX6JJhGo) – A comprehensive, beginner-friendly video tutorial.
- [Docker in 100 Seconds (YouTube, Fireship)](https://www.youtube.com/watch?v=Gjnup-PuquQ) – A fast-paced, visual introduction to Docker basics.

**Interactive Learning**

- [Play with Docker](https://labs.play-with-docker.com/) – Try Docker in your browser, no installation required.

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
