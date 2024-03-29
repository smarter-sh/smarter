#------------------------------------------------------------------------------
# This Dockerfile is used to build
# - a Docker image for the Smarter application.
# - a Docker container for the Smarter Celery worker.
# - a Docker container for the Smarter Celery beat.
#
# This image is used for all environments (local, alpha, beta, next and production).
#------------------------------------------------------------------------------

# Use the official Python image as a parent image
FROM --platform=linux/amd64 python:3.11-buster

# Environment: local, alpha, beta, next, or production
ARG ENVIRONMENT
ENV ENVIRONMENT=$ENVIRONMENT
RUN echo "ENVIRONMENT: $ENVIRONMENT"

ENV PYTHONPATH="${PYTHONPATH}:/smarter"

# Create a non-root user to run the application
RUN adduser --disabled-password --gecos '' smarter_user

# Setup our file system.
# Add our source code and make the 'smarter' directory the working directory
# so that the Docker file system matches up with the local file system.
WORKDIR /smarter
COPY ./smarter .
RUN chown smarter_user:smarter_user -R .

# Install system packages for the Smarter application.
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y default-mysql-client -y && \
    apt-get install build-essential libssl-dev libffi-dev python3-dev python-dev -y && \
    rm -rf /var/lib/apt/lists/*

# Install Node.js and npm
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash -
RUN apt-get install -y nodejs

# Add all Python package dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements/docker.txt

# Install Python dependencies for the local environment for cases where
# we're going to run python unit tests in the Docker container.
RUN if [ "$ENVIRONMENT" = "local" ] ; then pip install -r requirements/local.txt ; fi


# Build the React app and collect static files
RUN cd smarter/apps/chatapp/reactapp/ && npm install && npm run build && cd ../../../../
RUN python manage.py collectstatic --noinput

# Add a non-root user and switch to it
# setup the run-time environment
USER smarter_user
CMD ["gunicorn", "smarter.wsgi:application", "-b", "0.0.0.0:8000"]
EXPOSE 8000
