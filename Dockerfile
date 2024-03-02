# Use the official Python image as a parent image
FROM --platform=linux/amd64 python:3.11-buster

# Define environment variables
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG AWS_REGION
ARG ENVIRONMENT
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

WORKDIR /app

# Install MySQL Client, cryptography dependencies for django-rest-knox,
# and update apt packages.
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y default-mysql-client -y && \
    apt-get install build-essential libssl-dev libffi-dev python3-dev python-dev -y && \
    rm -rf /var/lib/apt/lists/*

# Install Node.js and npm
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash -
RUN apt-get install -y nodejs

# Add our source code
COPY smarter .

# Add all Python package dependencies
RUN mkdir smarter
RUN mkdir smarter/requirements
COPY smarter/requirements ./smarter/requirements
RUN pip install --upgrade pip
RUN pip install -r smarter/requirements/deploy.txt


# Build the React app and collect static files
RUN cd smarter/apps/chatapp/reactapp/ && npm install && npm run build && cd ../../../../
RUN python manage.py collectstatic --noinput


CMD ["gunicorn", "smarter.wsgi:application", "-b", "0.0.0.0:8000"]

EXPOSE 8000
