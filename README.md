# The Smarter Project

[![Latest Release](https://img.shields.io/github/v/release/smarter-sh/smarter?label=release)](https://github.com/smarter-sh/smarter/releases)
![Build Status](https://github.com/smarter-sh/smarter/actions/workflows/build.yml/badge.svg?branch=main)
![Test Status](https://github.com/smarter-sh/smarter/actions/workflows/test.yml/badge.svg?branch=main)
![Deploy Status](https://github.com/smarter-sh/smarter/actions/workflows/deploy.yml/badge.svg?branch=main)
[![Python coverage](https://img.shields.io/codecov/c/github/smarter-sh/smarter/main?flag=python&label=Python%20coverage&logo=codecov)](https://codecov.io/gh/smarter-sh/smarter?flags%5B0%5D=python)
[![React coverage](https://img.shields.io/codecov/c/github/smarter-sh/smarter/main?flag=react&label=React%20coverage&logo=codecov)](https://codecov.io/gh/smarter-sh/smarter?flags%5B0%5D=react)
[![Docs](https://img.shields.io/badge/Read%20the%20Docs-smarter.sh-blue?logo=readthedocs)](https://docs.smarter.sh/en/latest/)
[![Website](https://img.shields.io/badge/official%20web%20site-smarter.sh-blue?logo=google-chrome)](https://smarter.sh)
[![Docker Pulls](https://img.shields.io/docker/pulls/mcdaniel0073/smarter.svg?logo=docker&label=DockerHub)](https://hub.docker.com/r/mcdaniel0073/smarter)
[![Artifact Hub](https://img.shields.io/endpoint?url=https://artifacthub.io/badge/repository/project-smarter)](https://artifacthub.io/packages/search?repo=project-smarter)
[![License: GNU AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)<br>

Smarter is used as an instructional tool at [University of British Columbia](https://www.ubc.ca/)
for teaching AI.

The Smarter Project is an open source, cloud-native
[platform](https://docs.smarter.sh/en/latest/smarter-platform.html) and
[developer framework](https://docs.smarter.sh/en/latest/smarter-framework.html)
for building sophisticated AI applications **without writing a single line of
Python**. An application that searches the web, queries your databases, calls
your APIs, uses the tools of any MCP server, and defends itself against prompt
injection and data leaks is described in one short YAML file, and deployed with
one command:

```console
smarter apply -f my-ai-application.yaml
```

![Smarter Manifest](https://cdn.smarter.sh/docs/smarter-framework/smarter-manifest.png)
![Smarter Web Console](https://cdn.smarter.sh/github.com/smarter-sh/react/dashboard-screenshot.png)

## Why Smarter?

- **No code. Just a manifest.** A [Smarter Manifest (SAM)](https://docs.smarter.sh/en/latest/smarter-framework/smarter-manifests.html)
  declares **what** an application is, rather than programming **how** it
  works. Prompt engineers, business analysts, and product managers can build,
  read, and change production AI applications themselves, and manifests are
  versioned, reviewed, and deployed from CI/CD like the rest of your
  infrastructure.
- **Every way to reach external data.** Each approach is a
  [Resource](https://docs.smarter.sh/en/latest/smarter-resources.html) that
  you declare in a manifest, with no code: [Remote APIs](https://docs.smarter.sh/en/latest/smarter-resources/plugin/plugin/api.html),
  [Remote SQL](https://docs.smarter.sh/en/latest/smarter-resources/plugin/plugin/sql.html),
  [MCP servers](https://docs.smarter.sh/en/latest/smarter-resources/smarter-mcpclient.html),
  [the web](https://docs.smarter.sh/en/latest/smarter-resources/plugin/plugin/websearch.html),
  [skills](https://docs.smarter.sh/en/latest/smarter-resources/plugin/plugin/skill.html),
  and [your own documents](https://docs.smarter.sh/en/latest/smarter-resources/smarter-vectorstore.html).
- **Governed from the first prompt.** Deterministic
  [Guardrails](https://docs.smarter.sh/en/latest/smarter-resources/smarter-guardrail.html)
  inspect every message on its way to the model and every reply on its way
  back, and every intervention is recorded.
- **Contained by design.** No code execution, private networks, hardened
  outbound requests, role-based access at every layer, and credentials the
  model never holds. See [Security](https://docs.smarter.sh/en/latest/smarter-platform/security.html).
- **Composed like an orchestra.** An
  [LLMClient](https://docs.smarter.sh/en/latest/smarter-resources/smarter-llmclient.html)
  combines a model from any provider with the plugins, MCP clients, and
  guardrails it needs, simply by listing them by name, and an
  [Orchestrator](https://docs.smarter.sh/en/latest/smarter-resources/smarter-orchestrator.html)
  coordinates several LLMClients in multi-agent workflows.
- **Built for teams.** Every Resource has an owner and is shared with everyone
  in the owner's [Account](https://docs.smarter.sh/en/latest/smarter-resources/smarter-account.html).
- **Runs at scale, on your infrastructure.** Start with a single Docker
  container on your laptop, then go to production on Kubernetes with the
  [Smarter Helm chart](https://artifacthub.io/packages/helm/project-smarter/smarter).
  No managed-service dependency and no vendor lock-in.

## At a Glance

- **Get started**:
  [Quick Start Guide](https://docs.smarter.sh/en/latest/smarter-platform/installation/quick-start.html) |
  [Prerequisites](https://docs.smarter.sh/en/latest/smarter-platform/prerequisites.html) |
  [Troubleshooting](https://docs.smarter.sh/en/latest/smarter-platform/trouble-shooting.html) |
  [Tutorial](https://docs.smarter.sh/learn/)
- **Platform**
  - A proxy server that gives secure, governed, auditable access to AI
    providers and resources, without exposing secrets or the underlying vendor
    accounts.
  - Build every AI resource with declarative YAML manifests, with no Python
    programming, much as you would with [Kubernetes](https://kubernetes.io/).
  - Manage resources with the
    [web console](https://docs.smarter.sh/en/latest/smarter-platform/smarter-web-console.html),
    the [REST API](https://docs.smarter.sh/en/latest/smarter-framework/smarter-api.html),
    and the [command-line interface](https://smarter.sh/cli).
  - Runs at scale on Kubernetes, with automatic horizontal scaling of
    application servers and background workers.
  - Built-in [logging](https://docs.smarter.sh/en/latest/smarter-framework/developer-reference/smarter-journal.html),
    [cost accounting](https://docs.smarter.sh/en/latest/smarter-platform/cost-accounting.html),
    and [security](https://docs.smarter.sh/en/latest/smarter-platform/security.html).
- **Knowledge and tools**
  - API, SQL, Websearch, Skill, and Static
    [Plugins](https://docs.smarter.sh/en/latest/smarter-resources/smarter-plugin.html).
  - [MCPClients](https://docs.smarter.sh/en/latest/smarter-resources/smarter-mcpclient.html)
    for the Model Context Protocol ecosystem.
  - [Vectorstores](https://docs.smarter.sh/en/latest/smarter-resources/smarter-vectorstore.html)
    for semantic search over your own content.
- **Trust and safety**
  - Input and output Guardrails for moderation, self-harm, personal data, data
    subject requests, leaked secrets, profanity, fabricated citations, prompt
    injection, jailbreaks, and code injection.
  - End-to-end audit, from each
    [Prompt](https://docs.smarter.sh/en/latest/smarter-resources/smarter-prompt.html)
    back to the Account that authorized it.
- **Models and workflows**
  - Works with many [AI model providers](https://docs.smarter.sh/en/latest/smarter-resources/smarter-provider.html),
    including OpenAI, Google AI, Meta AI, and DeepSeek, as well as self-hosted
    models with [LLMHost](https://docs.smarter.sh/en/latest/smarter-resources/smarter-llmhost.html).
  - Multi-agent workflows with Orchestrator.
  - A prompt engineering workbench for testing applications before you deploy
    them.
- **Developer framework**
  - For when you do want to write code: built on Django, Django REST Framework,
    and Pydantic, and the same framework that Smarter itself is built on.
  - Automated AWS cloud infrastructure and Kubernetes management.
  - A [React component](https://docs.smarter.sh/en/latest/smarter-framework/developer-reference/react-integration/smarter-chat.html)
    that adds a Smarter chat to any web page.
  - [Python SDK](https://pypi.org/project/smarter-api/),
    [NPM packages](https://www.npmjs.com/package/@smarter.sh/ui-chat), and a
    [VS Code extension](https://marketplace.visualstudio.com/items?itemName=querium.smarter-manifest).

## Quickstart

This setup uses Docker and takes around 20 minutes for first time installations.

1. Verify project requirements:

   - [Windows](./setup/windows/), [macOS](./setup/macos/), [Linux](./setup/ubuntu/)
     operating system
   - 20Gib disk storage capacity
   - 4Gib system memory
   - [Python 3.13](https://www.python.org/)
   - [Docker](https://www.docker.com/products/docker-desktop/),
   - [Docker Compose](https://docs.docker.com/compose/install/).

2. Add your credentials to [.env](./.env.example) in the root of this repo.
   See the inline documentation for details on the minimum environment variables
   that you will need to set.

3. Initialize, build and run the application locally.

```console
git clone https://github.com/smarter-sh/smarter
make help           # scaffolds a .env file in the root of the repo
                    #
                    # ****************************
                    # STOP HERE!
                    # ****************************
                    # Add your credentials to .env located in the project root folder.
                    #
make init           # pulls Docker containers, creates a Python virtual environment,
                    # installs all packages, creates and initializes a
                    # local MySql database, preloads example AI resources
make run            # runs all docker containers and starts a
                    # local web server http://localhost:9357/
```

4. Login at http://localhost:9357/login/ with user `admin@smarter.sh` and
   password `smarter`.

See these onboarding videos:

- [Smarter Developer Onboarding I](https://youtu.be/-hZEO9sMm1s)
- [Smarter Developer Onboarding II](https://www.youtube.com/watch?v=G2RSCzxxupE)
- [Smarter Developer Workflow Tutorial](https://youtu.be/XolFLX1u9Kg)

## Key Features

**Smarter** implements a yaml manifest-based approach to managing AI resources
that is inspired by the [Kubernetes](https://kubernetes.io/) project.

It provides a unified, declarative way to define, configure, and orchestrate
the disparate resources that are required for creating and managing AI resources
that integrate to other enterprise resources like REST API's and Sql databases.
And it gives prompt engineering teams an intuitive workbench approach to
designing, prototyping, testing, deploying and managing powerful AI resources
for common corporate use cases including agentic workflows, customer facing chat
solutions, and more. It includes a separately managed
[React-based chat UI](https://github.com/smarter-sh/smarter-chat) that is
compatible with a wide variety of front end ecosystems including NPM, Wordpress,
Squarespace, Drupal, Office 365, Sharepoint, .Net, Netsuite, salesforce.com, and
SAP. There is a
[Golang command-line interface](https://github.com/smarter-sh/smarter-cli),
and a [PyPi package](https://github.com/smarter-sh/smarter-python) for
integrating the API functions into your own Python projects. It is developed to
support prompt engineering teams working in large organizations. Accordingly,
**Smarter** provides common enterprise features such as credentials management,
team workgroup management, role-based security, accounting cost codes, and
logging and audit capabilities.

**Smarter** provides seamless integration and interoperation between LLMs from
DeepSeek, Google AI, Meta AI and OpenAI. It is LLM provider-agnostic, and
provides seamless integrations to a continuously evolving list of value added
services for security management, prompt content moderation, audit, cost
accounting, and workflow management. **Smarter** is cloud native and runs on
Kubernetes, on-site in your data center or in the cloud.

**Smarter** is cost effective when running at scale. It is extensible and
architected on the philosophy of a compact core that does not require
customization nor forking. It is horizontally scalable. It is natively
multi-tenant, and can be installed alongside your existing systems.

## Helm Chart

See [ghcr.io/smarter-sh/charts/smarter](https://ghcr.io/smarter-sh/charts/smarter)
or [Artifact Hub](https://artifacthub.io/packages/helm/project-smarter/smarter).

## Documentation

Read the Docs: [docs.smarter.sh](https://docs.smarter.sh/)

## Support

Please report bugs to the [GitHub Issues Page](https://github.com/smarter-sh/smarter/issues)
for this project.

## Contributing

Please see the [CONTRIBUTING](https://docs.smarter.sh/en/latest/smarter-framework/guides/contributing.html).
