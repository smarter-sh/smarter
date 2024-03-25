#------------------------------------------------------------------------------
# This Dockerfile is used to build
# - a Docker image for the Smarter application.
# - a Docker container for the Smarter Celery worker.
# - a Docker container for the Smarter Celery beat.
#
# This image is used for all environments (local, dev, staging, and production).
#------------------------------------------------------------------------------

# Use the official Python image as a parent image
FROM --platform=linux/amd64 python:3.11-buster

# Define environment variables
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG AWS_REGION
ARG ENVIRONMENT
ARG DJANGO_SETTINGS_MODULE
ARG DEBUG_MODE
ARG DUMP_DEFAULTS
ARG MYSQL_HOST
ARG MYSQL_PORT
ARG MYSQL_DATABASE
ARG MYSQL_USER
ARG MYSQL_PASSWORD
ARG OPENAI_API_KEY
ARG PINECONE_API_KEY
ARG PINECONE_ENVIRONMENT
ARG GOOGLE_MAPS_API_KEY
ARG SECRET_KEY
ARG SMTP_HOST
ARG SMTP_PORT
ARG SMTP_USE_SSL
ARG SMTP_USE_TLS
ARG SMTP_USERNAME
ARG SMTP_PASSWORD
ARG CACHES_LOCATION
ARG CELERY_BROKER_URL
ARG CELERY_RESULT_BACKEND

# Set environment variables
ENV ENVIRONMENT=$ENVIRONMENT
ENV PYTHONPATH "${PYTHONPATH}:/smarter"
ENV CELERY_APP "smarter.smarter_celery.celery_app"

# Create a non-root user to run the application
RUN adduser --disabled-password --gecos '' smarter_user

# Setup our file system.
# - Add our source code and make the 'smarter' directory the working directory
#   so that the Docker file system matches up with the local file system.
# - Create a directory for the celerybeat-schedule file and change its ownership to smarter_user
WORKDIR /smarter
COPY ./smarter .
RUN mkdir celerybeat && chown smarter_user:smarter_user celerybeat

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
RUN pip install -r requirements/aws.txt

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
