#------------------------------------------------------------------------------
# This Dockerfile is used to build
# - a Docker image for the Smarter application.
# - a Docker container for the Smarter Celery worker.
# - a Docker container for the Smarter Celery beat.
#
# This image is used for all environments (local, alpha, beta, next and production).
#------------------------------------------------------------------------------

################################## base #######################################
# Use the official Python image as a parent image
# see https://hub.docker.com/_/python
#
# 3.12-slim-trixie is an official Docker image tag for Python 3.12 based on
# Debian "Trixie" (the codename for Debian 13).
# The "slim" variant is a minimal image that excludes unnecessary files and packages,
# making it smaller and faster to download and build.
# It is commonly used for production deployments where a lightweight Python environment is preferred.
FROM --platform=linux/amd64 python:3.12-slim-trixie AS linux_base

LABEL maintainer="Lawrence McDaniel <lpm0073@gmail.com>" \
  description="Docker image for the Smarter Api" \
  license="GNU AGPL v3" \
  vcs-url="https://github.com/smarter-sh/smarter" \
  org.opencontainers.image.title="Smarter API" \
  org.opencontainers.image.version="0.13.12" \
  org.opencontainers.image.authors="Lawrence McDaniel <lpm0073@gmail.com>" \
  org.opencontainers.image.url="https://smarter-sh.github.io/smarter/" \
  org.opencontainers.image.source="https://github.com/smarter-sh/smarter" \
  org.opencontainers.image.documentation="https://platform.smarter.sh/docs/"


# Environment: local, alpha, beta, next, or production
ARG ENVIRONMENT=local
ENV ENVIRONMENT=$ENVIRONMENT
RUN echo "ENVIRONMENT: $ENVIRONMENT"

############################## install system packages #################################
# build-essential           needed to build some python packages, but not included in 3.12-slim-trixie
# libssl-dev                ... ditto ...
# libffi-dev                ... ditto ...
# python3-dev               ... ditto ...
# pkg-config                ... ditto ...
# ------
# ca-certificates           needed for SSL/TLS support in http requests but not included in 3.12-slim-trixie
# python-dev-is-python3     helper package to ensure that the 'python' command points to python3
# default-mysql-client      needed for Django mysql backend support
# libmariadb-dev            needed for default-mysql-client python package
# git                       used in manage.py commands
# ------
# curl                      used below in this Dockerfile to download files
# unzip                     used below in this Dockerfile to install aws cli
# procps                    provides the 'ps' command, used for liveness/readiness probes of the beat pod in kubernetes
FROM linux_base AS system_packages

RUN apt-get update && apt-get upgrade -y && apt-get install -y \
  build-essential \
  libssl-dev \
  libffi-dev \
  python3-dev \
  pkg-config \
  ca-certificates \
  python-dev-is-python3 \
  default-mysql-client \
  libmariadb-dev \
  git \
  curl \
  unzip \
  procps && \
  rm -rf /var/lib/apt/lists/*

# Install kubectl, required for smarter/common/helpers/k8s_helpers.py
RUN curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl" && \
  chmod +x ./kubectl && \
  mv ./kubectl /usr/local/bin/kubectl

# install aws cli, required for smarter/common/helpers/aws/
RUN curl "https://d1vvhvl2y92vvt.cloudfront.net/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
  unzip awscliv2.zip && \
  ./aws/install && \
  rm -rf awscliv2.zip aws

############################## create app user #################################
FROM system_packages AS user_setup

# Create a non-root user to run the application
RUN adduser --disabled-password --gecos '' smarter_user

# create a data directory for the smarter_user that
# the application can use to store data.
# - add a .kube directory and an empty config file
# - add a celery directory for celerybeat to use to store its schedule.
RUN mkdir -p /home/smarter_user/data/.kube && touch /home/smarter_user/data/.kube/config && \
  mkdir -p /home/smarter_user/data/celery

# Set the KUBECONFIG environment variable
ENV KUBECONFIG=/home/smarter_user/data/.kube/config

# ensure that the smarter_user owns everything in the /smarter directory.
RUN chown -R smarter_user:smarter_user /home/smarter_user/

# so that the Docker file system matches up with the local file system.
WORKDIR /smarter

# Switch to non-root user
USER smarter_user

############################## python setup #################################
FROM user_setup AS venv
# Create and activate a virtual environment in the user's home directory
RUN python -m venv /home/smarter_user/venv
ENV PATH="/home/smarter_user/venv/bin:$PATH"

# Add all Python package dependencies
COPY ./smarter/requirements requirements
RUN pip install --upgrade pip && \
  pip install --no-cache-dir -r requirements/docker.txt

# Install Python dependencies for the local environment for cases where
# we're going to run python unit tests in the Docker container.
RUN if [ "$ENVIRONMENT" = "local" ] ; then pip install -r requirements/local.txt ; fi

############################## application ##################################
FROM venv AS application
# do this last so that we can take advantage of Docker's caching mechanism.
WORKDIR /home/smarter_user/
COPY --chown=smarter_user:smarter_user ./smarter ./smarter
COPY --chown=smarter_user:smarter_user ./smarter/smarter/apps/chatbot/data/ ./data/manifests/

################################# permissuions #######################################
FROM application AS permissions

# ensure that smarter_user owns everything and has the minimum
# permissions needed to run the application and to manage files
# that the application needs to write to in /home/smarter_user.
# this is important because by default Debian adds
# read-only and execute permissions to the group and to public.
# We don't want either of these.
#
# files:                    r-------- so that smarter_user can read them
# directories:              r-x------ so that smarter_user can cd into them
# venv/bin/*:               r-x------ so that smarter_user can execute them
# smarter/**/migrations:    rwx------ so that smarter_user can write django migration files.
# data:                     rwx------ so that smarter_user can manage the data directory.
# .cache:                   rwx------ bc some python packages want to write to .cache, like tldextract

USER root
RUN chown -R smarter_user:smarter_user /home/smarter_user/ && \
  find /home/smarter_user/ -type f -exec chmod 400 {} + && \
  find /home/smarter_user/ -type d -exec chmod 500 {} + && \
  find /home/smarter_user/venv/bin/ -type f -exec chmod 500 {} + && \
  find /home/smarter_user/smarter/smarter/ -type d -name migrations -exec chmod 700 {} + && \
  chmod -R 700 /home/smarter_user/data && \
  chmod -R 700 /home/smarter_user/.cache

################################# data #################################
FROM permissions AS data
# Add our source code and make the 'smarter' directory the working directory
# we want this to be the last step so that we can take advantage of Docker's
# caching mechanism.
WORKDIR /home/smarter_user/

COPY --chown=smarter_user:smarter_user ./docs ./data/docs
COPY --chown=smarter_user:smarter_user ./README.md ./data/docs/README.md
COPY --chown=smarter_user:smarter_user ./CHANGELOG.md ./data/docs/CHANGELOG.md
COPY --chown=smarter_user:smarter_user ./CODE_OF_CONDUCT.md ./data/docs/CODE_OF_CONDUCT.md
COPY --chown=smarter_user:smarter_user ./Dockerfile ./data/Dockerfile
COPY --chown=smarter_user:smarter_user ./Makefile ./data/Makefile
COPY --chown=smarter_user:smarter_user ./docker-compose.yml ./data/docker-compose.yml


# Collect static files
############################## collect_assets ##################################
FROM data AS collect_assets
WORKDIR /home/smarter_user/smarter
RUN python manage.py collectstatic --noinput


################################# final #######################################
FROM collect_assets AS serve_application

WORKDIR /home/smarter_user/smarter
USER smarter_user
CMD ["gunicorn", "smarter.wsgi:application", "-b", "0.0.0.0:8000"]
EXPOSE 8000
