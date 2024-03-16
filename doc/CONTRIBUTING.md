# Developer Setup Guide

[![OpenAI](https://a11ybadges.com/badge?logo=openai)](https://platform.openai.com/)
[![LangChain](https://a11ybadges.com/badge?text=LangChain&badgeColor=0834ac)](https://www.langchain.com/)
[![Amazon AWS](https://a11ybadges.com/badge?logo=amazonaws)](https://aws.amazon.com/)
[![Bootstrap](https://a11ybadges.com/badge?logo=bootstrap)](https://getbootstrap.com/)
[![ReactJS](https://a11ybadges.com/badge?logo=react)](https://react.dev/)
[![NPM](https://a11ybadges.com/badge?logo=npm)](https://www.npmjs.com/)
[![Yarn](https://a11ybadges.com/badge?logo=yarn)](https://yarnpkg.com/)
[![Gulp](https://a11ybadges.com/badge?logo=gulp)](https://gulpjs.com/)
[![SASS](https://a11ybadges.com/badge?logo=sass)](https://sass-lang.com/)
[![Python](https://a11ybadges.com/badge?logo=python)](https://www.python.org/)
[![Django](https://a11ybadges.com/badge?logo=django)](https://www.djangoproject.com/)
[![Terraform](https://a11ybadges.com/badge?logo=terraform)](https://www.terraform.io/)

You should be able to work unencumbered in any of Linux, macOS or Windows. This repository contains four distinct projects, respectively, written in:

- [Python](#python-setup)
- [ReactJS](#reactjs-setup)
- [Terraform](#terraform-setup)
- [Keen Bootstrap Theme](#keen-bootstrap-theme-setup)

In each case there are various technology-specific resources that you'll need to initialize in your development environment. See setup instructions below for each technology.

## Quick Start

Smarter follows opinionated code style policies for most of the technologies in this repo. With that in mind, following is how to correctly setup your local development environment. Before attempting to setup this project you should ensure that the following prerequisites are installed in your local environment:

- npm: 10.4 or later
- python: 3.11 or later
- terraform 1.7 or later
- terragrunt 0.54 or later
- awscli: 2.15 or later
- git: 2.x or later
- make: 3.8 or later

```console
git clone https://github.com/QueriumCorp/smarter.git
make            # scaffold a .env file in the root of the repo
                #
                # ****************************
                # STOP HERE!
                # ****************************
                # Add your credentials to .env located in the project
                # root folder.

make init       # initialize Terraform, Python virtual environment and NPM
make pre-commit # install code analyzers and linters
make lint       # test run to ensure that everything in pre-commit is working.

make build      # deploy AWS cloud infrastructure, build ReactJS web app
make run        # run the web app locally in your dev environment
```

To preserve your own sanity, don't spend time formatting your Python, Terraform, JS or any other source code because pre-commit invokes automatic code formatting utilities such as black, flake8 and prettier, on all local commits, and these will reformat the code in your commit based on policy configuration files found in the root of this repo.

## Repository Setup

### .env setup

Smarter uses a **LOT** of configuration data. You'll find a pre-formatted quick-start sample .env [here](./example-dot-env) to help you get started, noting however that simply running `make` from the root of this repo will scaffold this exact file for you.

### pre-commit setup

This project uses pre-commit as a first-pass automated code review / QC process. pre-commit runs a multitude of utilities and checks for code formatting, linting, syntax checking, and ensuring that you don't accidentally push something to GitHub which you'd later regret. Broadly speaking, these checks are aimed at minimizing the extent of commits that contain various kinds of defects and stylistic imperfections that don't belong on the main branch of the project.

Note that many of the pre-commit commands are actually executed by Python which in turn is calling pip-installed packages listed in smarter/requirements/local.txt located in the root of the repo. It therefore is important that you first create the Python virtual environment using `make pre-commit`. It also is a good idea to do a complete 'dry run' of pre-commit, to ensure that your developer environment is correctly setup:

```console
make pre-commit
```

Output should look similar to the following:

![pre-commit output](https://github.com/QueriumCorp/smarter/blob/main/doc/img/pre-commit.png)

### Github Secrets setup

Common secrets for automated CD/CD processes are managed with [GitHub Secrets](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions). The GitHub Actions automated processes depend on several of these. When creating pull requests, the GitHub Actions will use these secrets, [github.com/QueriumCorp/smarter/settings/secrets/actions](https://github.com/QueriumCorp/smarter/settings/secrets/actions), so there's nothing special for you to do.

On the other hand, if you've forked this repo and are working on your own independent project, then you'll need to initialize each of these yourself.

![Github Secrets](https://github.com/QueriumCorp/smarter/blob/main/doc/img/github-secrets.png)

### Kubernetes Secrets

The Terraform code in this repo generates several sets of sensitive data that are persisted to [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/). This configuration data is tightly integrated to the CI/CD build and deploy workflows, and fully automates configuration of all back end services on which Smarter relies including for example, MySQL, SMTP Email, AWS S3, AWS Elastic Container Registry, and Kubernetes itself.

![Kubernetes Secrets](https://github.com/QueriumCorp/smarter/blob/main/doc/img/kubernetes-secrets.png)

### GitHub Actions

This project depends heavily on GitHub Actions to automate routine activities, so that hopefully, the source code is always well-documented and easy to read, and everything works perfectly. We automate the following in this project:

- Code style and linting checks, during both pre-commit as well as triggered on pushes to the main branch
- Unit tests for Python, React and Terraform
- Docker builds
- Environment-specific deployments to Kubernetes
- Semantic Version releases
- version bumps from npm, PyPi and Terraform Registry

A typical pull request will look like the following:

![Automated pull request](https://github.com/QueriumCorp/smarter/blob/main/doc/img/automated-pr.png)

## Python Setup

Smarter is built on the [Django](https://www.djangoproject.com/) web development framework for Python. Moreover, the API is implemented with [Django REST Framework](https://www.django-rest-framework.org/). Smarter strictly follows generally accepted best practices and coding conventions for both of these. Thus, to work effectively on this project you'll need familiarity with both of these third party code libraries. Also note that this project leverages [Dependabot](https://github.com/dependabot) and [Mergify](https://mergify.com/) for managing version numbers of all Python dependencies that are used in this project. These two services monitor all of the Python (and NPM and Terraform) dependencies for the project, automatically bumping package versions as well as running unit-tests in order to guard the main branch against breaking changes. Versions should therefore always be up to date at the moment that you clone the repo, and it should not be necessary for you to manually bump PyPi package version numbers inside the Python requirements files.

- Python requirements: [smarter/requirements](../smarter/requirements/).
- Django settings: [smarter/smarter/settings](../smarter/smarter/settings/)
- Dependabot configuration: [.github/dependabot.yml](../.github/dependabot.yml)
- Mergify configuration: [.mergify.yml](../.mergify.yml)

```console
make django-init
make python-lint
source venv/bin/activate
```

### Configuration Data

Smarter generally follows Django's convention of storing most configuration data in environment-specific python modules that are accessible via `django.conf.settings`. However, in light of the fact that Smarter uses a **LOT** of configuration data, and that this configuration data necessarily lives in many different locations, we also have our own propriety configuration module which is based on [Pydantic](https://docs.pydantic.dev/). The module can be found [here](../smarter/smarter/apps/common/conf.py) and is accessed as follows:

```python
from smarter.apps.common.conf import settings as smarter_settings
```

### Unit Tests

We're using `unittest` combined with `django.test` in this project. There's a shortcut for running all tests: `make django-test`. You should create relevant unit tests for your new features, sufficient to achieve a [Coverage](https://coverage.readthedocs.io/) analysis of at least 75%.

### Coverage

Coverage.py is a tool for measuring code coverage of Python programs. It monitors your program, noting which parts of the code have been executed, then analyzes the source to identify code that could have been executed but was not.

Coverage measurement is typically used to gauge the effectiveness of tests. It can show which parts of your code are being exercised by tests, and which are not.

Note the following shortcut for running a Coverage report: `make coverage`.

**Our goal for this project is to maintain an overall Coverage score of at least 80%.**

## ReactJS Setup

Please refer to this detailed [ReactJS setup guide](./client/README.md) for how to use vite.js to initialize the ReactJS development environment.

Note that this project leverages Dependabot for managing version numbers of all NPM packages that are used in this project, regardless of where and how. Versions should always be up to date at the moment that you clone the repo. It therefore should never be necessary for you to manually bump package.json version numbers.

```console
make react-init
```

## Terraform Setup

If you're new to Terraform then refer to this [Terraform Getting Started Guide](./TERRAFORM_GETTING_STARTED_GUIDE.md) for detailed setup instructions.

Note that this project leverages Dependabot for managing version numbers of all Terraform modules that are used in this project. Versions should always be up to date at the moment that you clone the repo. It therefore should not be necessary for you to manually bump module version numbers.

Also be aware that Terraform is a high-level scripting tool running on top of [AWS CLI](https://aws.amazon.com/cli/), and hence, it's capabilities are ultimately limited to the permissions granted to the [AWS IAM](https://aws.amazon.com/iam/) user account that you're using in your AWS CLI configuration.

```console
cd aws/dev
terragrunt init
terragrunt plan
terragrunt apply
```

## Keen Bootstrap Theme Setup

The Smarter dashboard UX is created with this [Bootstrap-based theme package](https://themes.getbootstrap.com/product/keen-the-ultimate-bootstrap-admin-theme/) authored and maintained by [KeenThemes](https://keenthemes.com/).

The complete, unmodified original set of resource files are located in this [keen_v3.0.6](../keen_v3.0.6/) folder in this repo.

These assets have been fully integrated into Django's templating system, which means that the html has been normalized, and that other static assets like fonts, svg, css, js and images are served from this [static](../smarter/smarter/static/) folder.

[SASS variables](../keen_v3.0.6/demo1/src/sass/layout/_variables.custom.scss)

Note the following helper commands:

```console
make keen-init      # locally installs npm, yarn and gulp requirements
make keen-build     # compile Sass and javascript into css and js bundles
make keen-server    # locally run the demo site
```
