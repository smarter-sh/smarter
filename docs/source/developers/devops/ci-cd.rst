CI/CD
=====

GitHub Actions for Smarter
--------------------------

GitHub Actions is a powerful automation platform integrated directly into GitHub.
It enables you to automate, customize, and execute your software development workflows right in your repository.
For Smarter, GitHub Actions is used to build, test, and deploy the application automatically whenever code is pushed or a pull request is opened.

**What is a Workflow?**

A *workflow* is a configurable automated process made up of one or more jobs.
Workflows are defined in YAML files stored in the `.github/workflows <https://github.com/smarter-sh/smarter/tree/main/.github/workflows/>`_
directory of the repository. Each workflow can be triggered by specific GitHub events (like `push`, `pull_request`, or on a schedule).

**What is an Action?**

An *action* is a reusable unit of code that performs a specific task. Actions can be combined as steps within a job in a workflow. You can use actions created by the GitHub community, or write your own.

**Workflow vs. Action**

- **Workflow:** The overall automation pipeline (e.g., build, test, deploy).
- **Action:** A single step or task within a workflow (e.g., checking out code, setting up Python, uploading artifacts).

**Smarter’s Use of GitHub Actions**

Smarter’s repository includes workflows for:

- **Building** the application (installing dependencies, running linters, running tests).
- **Deploying** to production or staging environments.
- **Continuous Integration (CI):** Ensuring code quality and correctness on every change.

These workflows are defined in YAML files such as
`.github/workflows/build.yml <https://github.com/smarter-sh/smarter/tree/main/.github/workflows/build.yml>`_
and `.github/workflows/deploy.yml <https://github.com/smarter-sh/smarter/tree/main/.github/workflows/deploy.yml>`_.
Each file specifies the jobs and steps required for that part of the CI/CD process.

**Example Workflow Structure:**

.. code-block:: yaml

   name: Build and Test
   on: [push, pull_request]
   jobs:
     build:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - name: Set up Python
           uses: actions/setup-python@v5
           with:
             python-version: '3.11'
         - name: Install dependencies
           run: pip install -r requirements.txt
         - name: Run tests
           run: pytest

GitHub Actions workflows run on GitHub's servers (eg, inside Azure). These in point of fact are
Kubernetes pods running ephemeral containers spun up on demand to execute the jobs defined in the workflows.
At the point of instantiation of the pod the container image contains only the base OS (eg, the latest Linux Ubuntu in the case of the example above)
and afterwards, any software explicitly declared by the workflow itself. Also note that it is necessary to explicitly
check out the repository code using the `actions/checkout` action, as shown in the example above.

.. important::

  You must explicitly declare everything you need in the workflow, as the environment starts out completely blank.
  Once the workflow completes, the pod and container are destroyed, so no state is preserved between runs. However,
  artifacts can be uploaded and downloaded between jobs within a workflow if needed, and,
  GitHub provides caching mechanisms that you can optionally use
  to speed up dependency installation between workflow runs.

**GitHub Actions Secrets**

Some workflows may require sensitive information (like API keys, tokens, or passwords) to function correctly.
GitHub Actions provides a secure way to store and access these secrets using *GitHub Secrets*.
Secrets are encrypted environment variables that can be used in your workflows without exposing their values in the code

See `GitHub Secrets Configuration <https://github.com/smarter-sh/smarter/settings/secrets/actions>`_ for the list of currently configured GitHub Secrets in the main Smarter repository.
of the workflows.

**Further Reading and References**

- `GitHub Actions Documentation <https://docs.github.com/en/actions>`_
- `GitHub Actions: Getting Started Guide <https://docs.github.com/en/actions/quickstart>`_
- `GitHub Actions Tutorial for Beginners (YouTube) <https://www.youtube.com/watch?v=R8_veQiYBjI>`_
- `Understanding GitHub Actions (Official Guide) <https://docs.github.com/en/actions/learn-github-actions/understanding-github-actions>`_
- `Awesome Actions (Curated List) <https://github.com/sdras/awesome-actions>`_

For more details, see the actual workflow files in the `.github/workflows/ <https://github.com/smarter-sh/smarter/tree/main/.github/workflows/>`_ directory of the Smarter repository.
