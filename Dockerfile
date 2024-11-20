#------------------------------------------------------------------------------
# This Dockerfile is used to build
# - a Docker image for the Smarter application.
# - a Docker container for the Smarter Celery worker.
# - a Docker container for the Smarter Celery beat.
#
# This image is used for all environments (local, alpha, beta, next and production).
#------------------------------------------------------------------------------

# Use the official Python image as a parent image
FROM --platform=linux/amd64 python:3.11-bookworm

LABEL maintainer="Lawrence McDaniel <lawrence@querium.com>"

# Environment: local, alpha, beta, next, or production
ARG ENVIRONMENT
ENV ENVIRONMENT=$ENVIRONMENT
RUN echo "ENVIRONMENT: $ENVIRONMENT"

ENV PYTHONPATH="${PYTHONPATH}:/smarter"

# Create a non-root user to run the application
RUN adduser --disabled-password --gecos '' smarter_user

# create a data directory for the smarter_user that
# the application can use to store data.
RUN mkdir -p /data/.kube && \
    touch /data/.kube/config && \
    chown -R smarter_user:smarter_user /data && \
    chmod -R 755 /data

# Set the KUBECONFIG environment variable
ENV KUBECONFIG=/data/.kube/config

# Setup our file system.
# so that the Docker file system matches up with the local file system.
WORKDIR /smarter
COPY ./smarter/requirements ./requirements
RUN chown smarter_user:smarter_user -R .

COPY ./scripts/pull_s3_env.sh .
RUN chown smarter_user:smarter_user -R . && \
    chmod +x pull_s3_env.sh

# bring Ubuntu up to date
RUN apt-get update && apt-get install -y

# install Node
# see: https://deb.nodesource.com/
RUN apt-get install -y ca-certificates curl gnupg && \
    mkdir -p /etc/apt/keyrings/ && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg  && \
    NODE_MAJOR=20  && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list  && \
    apt-get update && apt-get install nodejs -y


RUN apt-get update

RUN apt-get install default-mysql-client build-essential libssl-dev libffi-dev python3-dev python-dev-is-python3 -y

RUN rm -rf /var/lib/apt/lists/*

# Download kubectl, which is a requirement for using the Kubernetes API
RUN apt-get install -y curl && \
    curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x ./kubectl && \
    mv ./kubectl /usr/local/bin/kubectl

# install aws cli
RUN curl "https://d1vvhvl2y92vvt.cloudfront.net/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install

# Add all Python package dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements/docker.txt

# Install Python dependencies for the local environment for cases where
# we're going to run python unit tests in the Docker container.
RUN if [ "$ENVIRONMENT" = "local" ] ; then pip install -r requirements/local.txt ; fi

# Add our source code and make the 'smarter' directory the working directory
# we want this to be the last step so that we can take advantage of Docker's
# caching mechanism.
COPY ./smarter .
COPY ./doc /data/doc
COPY ./Dockerfile /data/Dockerfile
COPY ./Makefile /data/Makefile
COPY ./docker-compose.yml /data/docker-compose.yml

# Build the React app and collect static files
WORKDIR /smarter/smarter/apps/chatapp/reactapp
RUN npm install --only=production
RUN npm run build

WORKDIR /smarter
RUN python manage.py collectstatic --noinput

# Add a non-root user and switch to it
# setup the run-time environment
#
# TO DO: add auto download of AWS S3 bucket with settings.
USER smarter_user
CMD ["gunicorn", "smarter.wsgi:application", "-b", "0.0.0.0:8000"]
EXPOSE 8000
