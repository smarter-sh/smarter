#------------------------------------------------------------------------------
# This Dockerfile is used to build
# - a Docker image for the Smarter application.
# - a Docker container for the Smarter Celery worker.
# - a Docker container for the Smarter Celery beat.
#
# This image is used for all environments (local, alpha, beta, next and production).
#------------------------------------------------------------------------------

# Use the official Python image as a parent image
################################## base #######################################
FROM --platform=linux/amd64 python:3.12-bookworm AS linux_base

LABEL maintainer="Lawrence McDaniel <lawrence@querium.com>" \
      description="Docker image for the Smarter Api" \
      license="MIT" \
      vcs-url="https://github.com/smarter-sh/smarter" \
      org.opencontainers.image.title="Smarter API" \
      org.opencontainers.image.version="0.13.1" \
      org.opencontainers.image.authors="Lawrence McDaniel <lawrence@querium.com>" \
      org.opencontainers.image.url="https://smarter-sh.github.io/smarter/" \
      org.opencontainers.image.source="https://github.com/smarter-sh/smarter" \
      org.opencontainers.image.documentation="https://platform.smarter.sh/docs/"


# Environment: local, alpha, beta, next, or production
ARG ENVIRONMENT
ENV ENVIRONMENT=$ENVIRONMENT
RUN echo "ENVIRONMENT: $ENVIRONMENT"

############################## install system packages #################################
FROM linux_base AS system_packages

# bring Ubuntu up to date and install dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    default-mysql-client \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    python-dev-is-python3 \
    unzip && \
    rm -rf /var/lib/apt/lists/*

# install Node
# see: https://deb.nodesource.com/
RUN mkdir -p /etc/apt/keyrings/ && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    NODE_MAJOR=20 && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Download kubectl, which is a requirement for using the Kubernetes API
RUN curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x ./kubectl && \
    mv ./kubectl /usr/local/bin/kubectl

# install aws cli
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
RUN mkdir -p /home/smarter_user/data/.kube && \
    touch /home/smarter_user/data/.kube/config && \
    chown -R smarter_user:smarter_user /home/smarter_user/data && \
    chmod -R 755 /home/smarter_user/data

# Set the KUBECONFIG environment variable
ENV KUBECONFIG=/home/smarter_user/data/.kube/config


############################## python requirements #################################
FROM user_setup AS requirements
# Setup our file system.
# so that the Docker file system matches up with the local file system.
WORKDIR /smarter
COPY ./smarter/requirements ./requirements
RUN chown smarter_user:smarter_user -R .

COPY ./scripts/pull_s3_env.sh .
RUN chown smarter_user:smarter_user -R . && \
    chmod +x pull_s3_env.sh

# Set permissions for the non-root user
RUN chown -R smarter_user:smarter_user /smarter

# Switch to non-root user
USER smarter_user


############################## install python packages #################################
FROM requirements AS venv
# Create and activate a virtual environment in the user's home directory
RUN python -m venv /home/smarter_user/venv
ENV PATH="/home/smarter_user/venv/bin:$PATH"

# Add all Python package dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements/docker.txt

# Install Python dependencies for the local environment for cases where
# we're going to run python unit tests in the Docker container.
RUN if [ "$ENVIRONMENT" = "local" ] ; then pip install -r requirements/local.txt ; fi

################################# data #################################
FROM venv AS data
# Add our source code and make the 'smarter' directory the working directory
# we want this to be the last step so that we can take advantage of Docker's
# caching mechanism.
WORKDIR /home/smarter_user/

COPY --chown=smarter_user:smarter_user ./docs ./data/doc
COPY --chown=smarter_user:smarter_user ./README.md ./data/docs/README.md
COPY --chown=smarter_user:smarter_user ./CHANGELOG.md ./data/docs/CHANGELOG.md
COPY --chown=smarter_user:smarter_user ./CODE_OF_CONDUCT.md ./data/docs/CODE_OF_CONDUCT.md
COPY --chown=smarter_user:smarter_user ./Dockerfile ./data/Dockerfile
COPY --chown=smarter_user:smarter_user ./Makefile ./data/Makefile
COPY --chown=smarter_user:smarter_user ./docker-compose.yml ./data/docker-compose.yml

############################## application ##################################
FROM data AS application
# do this last so that we can take advantage of Docker's caching mechanism.
WORKDIR /home/smarter_user/
COPY --chown=smarter_user:smarter_user ./smarter ./smarter
COPY --chown=smarter_user:smarter_user ./smarter/smarter/apps/chatbot/data/ ./data/manifests/

# Collect static files
############################## collect_assets ##################################
FROM application AS collect_assets
WORKDIR /home/smarter_user/smarter
RUN python manage.py collectstatic --noinput

################################# final #######################################
FROM collect_assets AS final
CMD ["gunicorn", "smarter.wsgi:application", "-b", "0.0.0.0:8000"]
EXPOSE 8000
