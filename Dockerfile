#------------------------------------------------------------------------------
# This Dockerfile is used to build the following:
# - Smarter application.
# - Smarter Celery worker.
# - Smarter Celery beat.
#
# This image is used for all environments (local, alpha, beta, next and production).
# - It is published to DockerHub as mcdaniel0073/smarter:latest
#   https://hub.docker.com/repository/docker/mcdaniel0073/smarter/general
# - It is also the basis of the Helm chart used to deploy Smarter to production Kubernetes clusters.
#   https://artifacthub.io/packages/helm/project-smarter/smarter
#------------------------------------------------------------------------------

################################## base #######################################
# Use the official Python image as a parent image
# see https://hub.docker.com/_/python
#
# 3.13-slim-trixie is an official Docker image tag for Python 3.13 based on
# Debian "Trixie" (the codename for Debian 13).
# The "slim" variant is a minimal image that excludes unnecessary files and packages,
# making it smaller and faster to download and build.
# It is commonly used for production deployments where a lightweight Python environment is preferred.
# This is important because the Smarter container image build exceeds 2.4 GB,
# even when using the slim image as a base.
FROM python:3.13-slim-trixie AS linux_base

LABEL maintainer="Lawrence McDaniel <lpm0073@gmail.com>" \
  description="Docker image for the Smarter Api and web console" \
  license="GNU AGPL v3" \
  vcs-url="https://github.com/smarter-sh/smarter" \
  org.opencontainers.image.title="Smarter API" \
  org.opencontainers.image.version="0.14.0-alpha.16" \
  org.opencontainers.image.authors="Lawrence McDaniel <lpm0073@gmail.com>" \
  org.opencontainers.image.url="https://smarter.sh/" \
  org.opencontainers.image.source="https://github.com/smarter-sh/smarter" \
  org.opencontainers.image.documentation="https://docs.smarter.sh/"


# Environment: local, alpha, beta, next, or production
ARG TARGETPLATFORM
ARG TARGETARCH
ARG SCHEMA=APP

# from .env file. This is used to control which environment we're building the image for, and therefore
# which dependencies we install and which settings are used.
ARG ENVIRONMENT=local
ENV ENVIRONMENT=$ENVIRONMENT

# from .env file. This is used to control whether we build react components
# files during the build process.
ARG BUILD_REACT_COMPONENTS=true
ENV BUILD_REACT_COMPONENTS=${BUILD_REACT_COMPONENTS}

# from .env file. This is used to control whether we collect static files during the build process.
ARG COLLECT_STATIC_FILES=true
ENV COLLECT_STATIC_FILES=${COLLECT_STATIC_FILES}

############################## install system packages #################################
# build-essential           needed to compile Python packages with native extensions
# libssl-dev                needed by Python packages that link against OpenSSL
# libffi-dev                needed by Python packages that link against libffi
# python3-dev               provides Python headers for building native extensions
# pkg-config                helps build scripts locate system libraries
# ------
# ca-certificates           enables SSL/TLS certificate validation in HTTP clients
# python-dev-is-python3     ensures the 'python' command resolves to python3
# wget                      used to download build artifacts in later stages
# git                       used by manage.py commands and dependency installs
# curl                      used below in this Dockerfile to download kubectl and AWS CLI
# jq                        used below in this Dockerfile to parse React manifest.json
#                           files to determine which static assets download.
# unzip                     used below in this Dockerfile to install AWS CLI
# procps                    provides the 'ps' command for container health checks
# redis-tools               provides Redis CLI utilities for diagnostics and admin tasks
# libncurses6               runtime library required by terminal-oriented utilities
# groff                     enables formatted 'aws help' output
# less                      pager used by AWS CLI help and other terminal tools
FROM linux_base AS system_packages

# Install system packages
# The Python slim trixie image is based on Debian and is a limited installation. Most of these packages
# would ordinarily be included in a full Debian installation, but are missing from the slim image and
# we therefore need to "add these back in" as part of our Dockerfile.
RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get upgrade -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    pkg-config \
    ca-certificates \
    python-dev-is-python3 \
    wget \
    git \
    curl \
    jq \
    unzip \
    procps \
    redis-tools \
    libncurses6 \
    groff \
    less && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

FROM system_packages AS kubectl

# Install kubectl, required for smarter/common/helpers/k8s_helpers.py used for ChatBot/Agent
# deployments in which dedicated Kubernetes ingress and TLS certificates are created. There
# are Kubernetes builds for both amd64 and arm64 architectures (we build both for DockerHub
# multi-arch support).
RUN if [ "$TARGETARCH" = "arm64" ]; then \
      KUBECTL_ARCH="arm64"; \
    else \
      KUBECTL_ARCH="amd64"; \
    fi && \
    curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/${KUBECTL_ARCH}/kubectl" && \
    chmod +x ./kubectl && \
    mv ./kubectl /usr/local/bin/kubectl

FROM kubectl AS mariadb_connector

# Install MariaDB.
# installs libmariadb-dev libmariadb-dev-compat mariadb-client, Connector/C and mariadb_config.
# See
# - https://mariadb.com/docs/connectors/mariadb-connector-c/install-mariadb-connector-c
# - https://mariadb.com/downloads/

ARG MARIADB_VERSION=12.2
ENV MARIADB_CONFIG=/usr/bin/mariadb_config
ENV MARIADB_CONFIG_ALTERNATIVE=/usr/local/bin/mariadb_config
RUN curl -LsS -o mariadb_repo_setup https://downloads.mariadb.com/MariaDB/mariadb_repo_setup && \
    chmod +x mariadb_repo_setup && \
    ./mariadb_repo_setup --mariadb-server-version="${MARIADB_VERSION}" && \
    apt-get update && \
    apt-get install -y --no-install-recommends libmariadb-dev libmariadb-dev-compat mariadb-client && \
    test -x "$MARIADB_CONFIG" || (echo "mariadb_config not found at $MARIADB_CONFIG" && exit 1) && \
    ln -sf "$MARIADB_CONFIG" "$MARIADB_CONFIG_ALTERNATIVE" && \
    rm -f mariadb_repo_setup && \
    rm -rf /var/lib/apt/lists/*


FROM mariadb_connector AS aws_cli

# install aws cli, required for smarter/common/helpers/aws/
# We rely extensively on AWS support, for Route53, S3, Simple Email Service,
# Elastic Kubernetes Service, etc. There are AWS CLI builds for both
# amd64 and arm64 architectures (we build both for DockerHub multi-arch support).
RUN if [ "$TARGETARCH" = "arm64" ]; then \
      curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"; \
    else \
      curl "https://d1vvhvl2y92vvt.cloudfront.net/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"; \
    fi && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws


############################## create app user #################################
FROM aws_cli AS user_setup


# Create a non-root user to run the application
RUN adduser --disabled-password --gecos '' smarter_user

# create a data directory for the smarter_user that
# the application can use to store data.
# - add a .kube directory and an empty config file
# - add a celery directory for celerybeat to use to store its schedule.
RUN mkdir -p /home/smarter_user/data/.kube && touch /home/smarter_user/data/.kube/config && \
  mkdir -p /home/smarter_user/data/celery && \
  mkdir -p /home/smarter_user/data/media        # fallback Django storage when not using S3 or other external storage.

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

# Add all Python package dependencies.
# We do this before adding the application code so that we can take advantage
# of Docker's caching mechanism. If the requirements files do not change,
# Docker will use the cached layer and not reinstall the packages.
#
# mcdaniel jan-2026: adding local requirements.txt back in because of the
# https://github.com/smarter-sh/smarter-deploy repo that is used to deploy
# smarter locally for non-developers.
COPY ./smarter/requirements requirements
RUN pip install pip==25.3 setuptools wheel pip-tools && \
  pip install --no-cache-dir -r requirements/docker.txt

# Install Python dependencies for the local environment for cases where
# we're going to run python unit tests in the Docker container.
RUN if [ "$ENVIRONMENT" = "local" ] ; then pip install -r requirements/local.txt ; fi

FROM venv AS react_cache_buster

ENV REACT_COMPONENTS="dashboard prompt_list prompt_passthrough terminal_emulator"

ARG REACT_MANIFESTS_HASH
ENV REACT_MANIFESTS_HASH=${REACT_MANIFESTS_HASH}

# Download all manifests and compute a combined hash for cache busting
RUN for app in $REACT_COMPONENTS; do \
      url="https://cdn.smarter.sh/react/${app}/manifest.json"; \
      echo "Downloading manifest for ${app} from ${url}"; \
      echo "Last-Modified for $url: $(curl -sI "$url" | grep -i '^Last-Modified:')" \
      curl -fsSL "$url" -o "/tmp/${app}_manifest.json"; \
      sha256sum "/tmp/${app}_manifest.json" | awk '{print $1}' > "/tmp/${app}_manifest.hash"; \
    done && \
    cat /tmp/*_manifest.hash | sha256sum | awk '{print $1}' > /tmp/react_manifests.hash


################################ build react ###################################
# The Smarter web console UI includes several React components, such as the
# main dashboard, prompt (Chatbots) list, terminal emulator, and prompt passthrough.
# Vite pushes builds of these React components to a CDN which is used as a general
# purpose distribution mechanism for the latest production-ready builds of these components.
#
# The downloaded assets are placed in smarter/smarter/static/react/,
# from which Django collects its static files. This directory is ignored by git
# because it contains build assets rather than source code, so, these assets
# are always fetched as part of the Docker build process rather than being
# committed to the repository.
#
# Developers: Note that Vite also saves locally to this same directory for local development.
# Thus, you can still use the Makefile command `make collectstatic`
# to build React components locally if needed, but the default and recommended workflow
# is to rely on the CDN downloads for all environments.
#
# example manifest.json file for reference: https://cdn.smarter.sh/react/terminal_emulator/manifest.json
# {
#   "_rolldown-runtime.js": {
#     "file": "assets/rolldown-runtime.js",
#     "name": "rolldown-runtime"
#   },
#   "_xterm-kHJ-D0s7.css": {
#     "file": "assets/xterm-kHJ-D0s7.css",
#     "src": "_xterm-kHJ-D0s7.css"
#   },
#   "_xterm.js": {
#     "file": "assets/xterm.js",
#     "name": "xterm",
#     "imports": [
#       "_rolldown-runtime.js"
#     ],
#     "css": [
#       "assets/xterm-kHJ-D0s7.css"
#     ]
#   },
#   "index.html": {
#     "file": "assets/index.js",
#     "name": "index",
#     "src": "index.html",
#     "isEntry": true,
#     "imports": [
#       "_rolldown-runtime.js",
#       "_xterm.js"
#     ],
#     "css": [
#       "assets/index-58MXwt-L.css"
#     ]
#   }
# }
FROM react_cache_buster AS react_assets

# this resolves to d33lzt17u1szu4.cloudfront.net
ENV CDN_BASE=https://cdn.smarter.sh/react
ENV REACT_STAGING_FOLDER=/tmp/react_assets
RUN mkdir -p ${REACT_STAGING_FOLDER}

WORKDIR ${REACT_STAGING_FOLDER}

ENV REACT_COMPONENTS="dashboard prompt_list prompt_passthrough terminal_emulator"

# set -e : fail immediately on error.
# set --u : fail on undefined variables
#
# Notes:
# - build FAILS if manifest.json cannot be downloaded
# - downloads EVERY unique asset referenced anywhere in manifest.json
# - preserves nested paths like assets/foo.js
# - safely handles:
#     - imports
#     - css
#     - entrypoints
#     - runtime chunks
#     - arbitrary manifest complexity
RUN set -eu; \
    for app in ${REACT_COMPONENTS}; do \
        echo "Collecting assets for React component: ${app}"; \
        APP_ROOT="${REACT_STAGING_FOLDER}/${app}"; \
        MANIFEST="${APP_ROOT}/manifest.json"; \
        \
        mkdir -p "${APP_ROOT}"; \
        \
        url="${CDN_BASE}/${app}/manifest.json"; \
        echo "Downloading manifest for ${app} from ${url}"; \
        curl --retry 5 --retry-delay 2 --retry-all-errors -fsSL \
            "${url}" \
            -o "${MANIFEST}"; \
        \
        echo "Downloaded manifest for ${app}:"; \
        cat "${MANIFEST}"; \
        \
        url="${CDN_BASE}/${app}/index.html"; \
        echo "Downloading index.html for ${app} from ${url}"; \
        curl --retry 5 --retry-delay 2 --retry-all-errors -fsSL \
            "${url}" \
            -o "${APP_ROOT}/index.html"; \
        \
        jq -r ' \
            [ \
              .[] | \
              (.file), \
              (.css[]?) \
            ] \
            | unique[] \
        ' "${MANIFEST}" \
        | while read -r ASSET_FILE; do \
            [ -n "${ASSET_FILE}" ] || continue; \
            \
            DEST_PATH="${APP_ROOT}/${ASSET_FILE}"; \
            DEST_DIR="$(dirname "${DEST_PATH}")"; \
            \
            mkdir -p "${DEST_DIR}"; \
            \
            url="${CDN_BASE}/${app}/${ASSET_FILE}"; \
            echo "Downloading asset: ${url}"; \
            curl --retry 5 --retry-delay 2 --retry-all-errors -fsSL \
                "${url}" \
                -o "${DEST_PATH}"; \
        done; \
    done


############################## application ##################################
FROM react_assets AS application
# do this last so that we can take advantage of Docker's caching mechanism.
WORKDIR /home/smarter_user/
COPY --chown=smarter_user:smarter_user ./smarter ./smarter
COPY --chown=smarter_user:smarter_user ./smarter/smarter/apps/chatbot/data/ ./data/manifests/
RUN mkdir -p /home/smarter_user/data/manifests/example_manifests

COPY --from=react_assets /tmp/react_assets/ /home/smarter_user/smarter/smarter/static/react/


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
RUN if [ "$ENVIRONMENT" != "local" ] ; then chown -R smarter_user:smarter_user /home/smarter_user/ && \
  find /home/smarter_user/ -type f -exec chmod 400 {} + && \
  find /home/smarter_user/ -type d -exec chmod 500 {} + && \
  find /home/smarter_user/venv/bin/ -type f -exec chmod 500 {} + && \
  find /home/smarter_user/smarter/smarter/ -type d -name migrations -exec chmod 700 {} + && \
  chmod -R 700 /home/smarter_user/data && \
  chmod -R 700 /home/smarter_user/.cache && \
  chmod 755 /home/smarter_user/smarter/manage.py ; fi

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



############################## collect_assets ##################################
# This is a Django application, so we need to collect static assets.
# We do this in a separate stage so that if the application code changes
# but the static assets do not change, we can take advantage of Docker's
# caching mechanism.
FROM data AS collect_assets
WORKDIR /home/smarter_user/smarter
RUN if [ "$COLLECT_STATIC_FILES" = "true" ]; then python manage.py collectstatic --noinput; else echo "Skipping collectstatic"; fi

################################# final #######################################
# This is the final stage that will be used to run the application.
# Uvicorn is used as the application server.
# "smarter.asgi:application" is the ASGI application callable and corresponds
# to the "application" variable in smarter/asgi.py.
# The application will listen on all interfaces (0.0.0.0).
FROM collect_assets AS serve_application

WORKDIR /home/smarter_user/smarter
USER smarter_user
CMD ["uvicorn", "smarter.asgi:application", "--host", "0.0.0.0", "--port", "9357", "--workers", "2"]
EXPOSE 8000
