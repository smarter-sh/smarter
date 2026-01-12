12-Factor App
=============

This project conforms to `12-factor methodology <https://12factor.net/>`_.
The 12-Factor methodology is a
set of best practices for building modern, scalable, maintainable
software-as-a-service apps. These principles were first presented by
engineers at Heroku, a cloud platform as a service (PaaS) company.
Following are the salient points of how this project adopts these best
practices.

1. **Codebase**: [✅] One codebase tracked in revision control, many deploys.
   This project is hosted in `https://github.com/smarter-sh/smarter <https://github.com/smarter-sh/smarter`_.

2. **Dependencies**: [✅] Explicitly declare and isolate dependencies.
   We’re using Python’s requirements files, Helm’s Chart.yaml,
   and NPM’s package.json to declare dependencies. You'll find these files in

   - `./smarter/requirements <https://github.com/smarter-sh/smarter/tree/main/smarter/requirements>`_
   - `./package.json <https://github.com/smarter-sh/smarter/tree/main/package.json>`_
   - `./helm/charts/smarter <https://github.com/smarter-sh/smarter/tree/main/helm/charts/smarter>`_


3. **Config**: [✅] Store config in the environment. This project
   is based on the Django web framework which has its own
   form of configuration management that you'll find in `./smarter/smarter/settings <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/settings>`_. But in addition, Smarter
    implements a special
   `Settings <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/common/conf.py>`_ class,
   which is designed to read environment variables as source data, and then both
   validate and derive all related configuration information for the entire platform.

4. **Backing services**: [✅] Treat backing services as attached
   resources. We’re using MySql, Redis, and AWS SES in this project,
   all of which are configurable using Django settings. You'll find
   these in the Django settings files, in  `./smarter/smarter/settings <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/settings>`_.

5. **Build, release, run**: [✅] Strictly separate build and run
   stages. When running locally, ``Build`` is implemented in `./Makefile <https://github.com/smarter-sh/smarter/blob/main/Makefile>`_.
   When deployed to AWS, ``build`` and ``release`` are implemented as GitHub Actions
   which you'll find in `./.github/workflows <https://github.com/smarter-sh/smarter/tree/main/.github/workflows>`_

6. **Processes**: [✅] Execute the app as one or more stateless
   processes. This REST API is stateless. When running locally, this
   runs as a collection of three Docker containers for the app, worker and scheduler.
   When deployed to AWS, this is implemented using AWS Elastic Kubernetes Service (EKS)
   where the same Docker containers are scheduled and run as pods, which
   you can see in Smarter's Helm chart, `https://artifacthub.io/packages/helm/project-smarter/smarter <https://artifacthub.io/packages/helm/project-smarter/smarter>`_

7. **Port binding**: [✅] Export services via port binding. This
   service listens on ports 80 and 443.

8. **Concurrency**: [✅] Scale out via the process model. We achieve
   this “for free” since we’re using AWS serverless infrastructure,
   which is inherently and infinitely scalable.

9. **Disposability**: [✅] Maximize robustness with fast startup and
   graceful shutdown. Docker, Kubernetes, and Terraform take care of this for us.

   - Docker containers are designed to start up quickly and shut down gracefully, and
     can be easily replaced, restarted or deleted entirely.
   - Kubernetes manages the lifecycle of containers running in the cloud, ensuring that they are
     started and stopped in a controlled manner, and can automatically restart
     failed containers.
   - Running ``terraform destroy`` in `github.com/smarter-sh/smarter-infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`_
     will remove this project's aws resources and any residual data from your AWS account.
     If you are running locally then simply deleting all
     Smarter Docker containers and images will achieve the same effect.

10. **Dev/prod parity**: [✅] Keep development, staging, and
    production as similar as possible. The GitHub Action
    `pushMain.yml <.github/workflows/pushMain.yml>`_ executes a
    forced merge from main to dev branches. This ensures that all dev
    branches are synced to main immediately after pull requests are
    merged to main.

11. **Logs**: [✅] Treat logs as event streams. Smarter takes
    logging pretty seriously. Logs not only functions as event
    streams, Smarter takes things to a whole new level by implementing
    a comprehensive set of logging style guidelines that make logs
    entries information-rich, consistent, and easy to read.

12. **Admin processes**: [✅] Run admin/management tasks as one-off
    processes. Django provides us with ``manage.py``, which is a great
    environment for running one-off ad hoc tasks from the command line.
    But additionally, we have GitHub Actions for operations that supersede
    the code base itself, such as managing build, test, releases, issues,
    and other GitHub management features.
