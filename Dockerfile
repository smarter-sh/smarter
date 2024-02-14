# Use the official Python image as a parent image
FROM --platform=linux/amd64 python:3.11-buster

# Define environment variables
ARG DEBUG_MODE
ARG OPENAI_API_KEY
ARG PINECONE_API_KEY
ARG PINECONE_ENVIRONMENT
ARG GOOGLE_MAPS_API_KEY
ARG MYSQL_HOST
ARG MYSQL_PORT
ARG MYSQL_USER
ARG MYSQL_PASSWORD
ARG MYSQL_DATABASE

WORKDIR /app

# Install MySQL Client
RUN apt-get update && \
    apt-get install -y default-mysql-client && \
    rm -rf /var/lib/apt/lists/*

# Add all Python package dependencies
RUN mkdir requirements
COPY requirements ./requirements
RUN pip install --upgrade pip
RUN pip install -r requirements/deploy.txt

# Add our source code
COPY python/smarter .

# Collect static files
RUN python manage.py collectstatic --noinput


CMD ["gunicorn", "smarter.wsgi:application", "-b", "0.0.0.0:8000"]

EXPOSE 8000
