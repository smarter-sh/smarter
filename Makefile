SHELL := /bin/bash
export PATH := /usr/local/bin:$(PATH)
export

ifeq ($(OS),Windows_NT)
    PYTHON := python.exe
    ACTIVATE_VENV := venv/Scripts/activate
else
    PYTHON := python3.13
    ACTIVATE_VENV := source venv/bin/activate
endif
PIP := $(PYTHON) -m pip

ifeq ("$(wildcard .env)","")
    $(shell cp .env.example .env)
endif
include .env

.PHONY: init activate build run test clean tear-down lint analyze coverage pre-commit-init pre-commit-run release docker-init docker-build docker-run docker-test python-init python-lint python-clean python-requirements keen-init keen-build keen-server helm change-log help

# Default target executed when no arguments are given to make.
all: help

# initialize local development environment.
# takes between 5 and 20 minutes to complete
init:
	@echo "==============================================================================="
	@echo "Initializing local development environment. This will verify and set up your"
	@echo "Python virtual environment, install all 3rd-party package requirements,"
	@echo "build the Docker containers, initialize the MySQL database, and create example users,"
	@echo "prompts and AI resources. This may take up to 20 minutes..."
	@echo "==============================================================================="
	make check-python							# verify Python 3.13 is installed
	make docker-check							# verify Docker is installed and running
	make python-init							# create/replace Python virtual environment and install dependencies
	smarter/manage.py collectstatic --noinput	# collect static files for the Django admin interface and other components
	make build			    					# build the Smarter Docker container
	make docker-init							# initialize MySQL and create the smarter database
	make pre-commit-init						# install and configure pre-commit
	@echo ""
	@echo ""
	@echo "==============================================================================="
	@echo "Initialization complete!"
	@echo ""
	@echo "Run 'source venv/bin/activate' to activate the Python virtual environment."
	@echo "Run 'make run' to start the application."
	@echo "    'make help' to see all available commands."
	@echo ""
	@echo "The application is served at http://localhost:9357/ with the following credentials:"
	@echo "    Username: admin"
	@echo "    Email: admin@$(or $(SMARTER_ROOT_DOMAIN),example.com)"
	@echo "    Password: smarter"
	@echo ""
	@echo "The database is accessible at localhost:3306 with the following credentials:"
	@echo "    Username: root"
	@echo "    Password: smarter"
	@echo "==============================================================================="

activate:
	./scripts/activate.sh

# complete Docker build. Performs all 13 steps of the build process regardless of current state.
# takes around 4 minutes to complete
build:
	@echo "==============================================================================="
	@echo "Building Docker containers ..."
	@echo "==============================================================================="
	make docker-build

# run the web application from Docker
# takes around 30 seconds to complete
run:
	@echo "==============================================================================="
	@echo "Running Docker containers ..."
	@echo "==============================================================================="
	make docker-run

test:
	make docker-test

clean:
	make python-clean
	make docker-prune

# destroy all Docker build and local artifacts
# takes around 1 minute to complete
tear-down:
	make python-clean
	make docker-prune

# ---------------------------------------------------------
# Code management
# ---------------------------------------------------------

lint:
	make python-lint

analyze:
	@echo "==============================================================================="
	@echo "Generating code analysis report using cloc ..."
	@echo "==============================================================================="
	cloc . --exclude-ext=svg,zip --fullpath --not-match-d=smarter/smarter/static/assets/ --vcs=git

# docker exec smarter-app bash -c "coverage run manage.py test smarter.apps.plugin && coverage report -m && coverage html"
coverage:
	@echo "==============================================================================="
	@echo "Generating code coverage report using Docker and coverage.py ..."
	@echo "==============================================================================="
	docker exec smarter-app bash -c "coverage run --source=smarter.lib.django.request manage.py test smarter.lib.django.tests.test_request_mixin && coverage report -m"

pre-commit-init:
	@echo "==============================================================================="
	@echo "Installing and configuring pre-commit ..."
	@echo "==============================================================================="
	pre-commit install
	pre-commit autoupdate

pre-commit-run:
	@echo "==============================================================================="
	@echo "Running pre-commit hooks on all files ..."
	@echo "==============================================================================="
	pre-commit run --all-files

release:
	@echo "==============================================================================="
	@echo "Forcing a new semantic release on GitHub by creating an empty commit and pushing to the repository ..."
	@echo "==============================================================================="
	git commit -m "fix: force a new release" --allow-empty && git push


# ---------------------------------------------------------
# Docker
# ---------------------------------------------------------
docker-check:
	@echo ""
	@echo "==============================================================================="
	@echo "Verifying that Docker is installed and running ..."
	@echo "==============================================================================="
	@echo ""
	@docker ps >/dev/null 2>&1 || { echo >&2 "This project requires Docker but it's not running.  Aborting."; exit 1; }

docker-init:
	@echo ""
	@echo "==============================================================================="
	@echo "Initializing Docker environment, including MySQL database and Smarter application setup. This may take a few minutes..."
	@echo "==============================================================================="
	make docker-check && \
	docker-compose up -d && \
	docker exec smarter-mysql bash -c "sleep 20; until echo '\q' | mysql -u smarter -psmarter; do echo 'Waiting for MySQL to be ready...'; sleep 10; done" && \
	docker exec smarter-mysql mysql -u smarter -psmarter -e 'DROP DATABASE IF EXISTS smarter; CREATE DATABASE smarter;' && \
	docker exec smarter-app bash -c "\
		python manage.py makemigrations && python manage.py migrate && \
		python manage.py initialize_platform && \
		python manage.py add_plugin_examples && \
		python manage.py create_stackademy && \
		python manage.py deploy_builtin_chatbots && \
		python manage.py deploy_example_chatbot" && \
	docker exec smarter-mysql mysql -u smarter -psmarter -e 'UPDATE smarter.chatbot_chatbot SET deployed = 0;'
	@echo "Docker and Smarter are initialized."
	docker ps


docker-shell:
	make docker-check && \
	docker exec -it smarter-app /bin/bash

docker-build:
	make docker-check && \
	docker-compose build
	docker image prune -f

docker-run:
	make docker-check && \
	docker compose up

docker-test:
	make docker-check && \
	docker exec smarter-app bash -c "python manage.py test smarter.lib.django.tests.test_timestampedmodel"

docker-prune:
	@echo ""
	@echo "==============================================================================="
	@echo "Pruning Docker images, containers, volumes, and networks. "
	@echo "This will free up drive space by removing all unused Docker objects..."
	@echo "==============================================================================="
	make docker-check && \
	docker-compose down && \
	docker builder prune -a -f && \
	docker image prune -a -f
	rm -rf ./mysql-data && \
	find ./ -name celerybeat-schedule -type f -exec rm -f {} + && \
	docker system prune -a --volumes && \
	docker volume prune -f && \
	docker network prune -f && \
	images=$$(docker images -q) && [ -n "$$images" ] && docker rmi $$images -f || @echo "No images to remove"

# ---------------------------------------------------------
# Python
# ---------------------------------------------------------
check-python:
	@echo ""
	@echo "==============================================================================="
	@echo "Verifying that Python $(PYTHON) is installed ..."
	@echo "==============================================================================="
	@echo ""
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo >&2 "This project requires $(PYTHON) but it's not installed.  Aborting."; exit 1; }

python-init:
	@echo "==============================================================================="
	@echo "Initializing Python virtual environment and installing dependencies. This may take a few minutes..."
	@echo "==============================================================================="
	mkdir -p .pypi_cache && \
	make check-python
	make python-clean && \
	npm install && \
	$(PYTHON) -m venv venv && \
	$(ACTIVATE_VENV) && \
	PIP_CACHE_DIR=.pypi_cache $(PIP) install -r smarter/requirements/local.txt

python-lint:
	@echo ""
	@echo "==============================================================================="
	@echo "Running Python linting using pre-commit ..."
	@echo "==============================================================================="
	@echo ""
	make check-python
	make pre-commit-run
	pylint smarter/smarter

python-clean:
	@echo ""
	@echo "==============================================================================="
	@echo "Cleaning Python virtual environment and __pycache__ directories ..."
	@echo "==============================================================================="
	@echo ""
	rm -rf venv
	find ./smarter/ -name __pycache__ -type d -exec rm -rf {} +

# FIX NOTE: mcdaniel. the pip version pin temporarily resolves a pip-compile issue.
#           AttributeError: 'PackageFinder' object has no attribute 'allow_all_prereleases'
python-requirements:
	@echo "==============================================================================="
	@echo "Compiling and updating Python dependency files using pip-compile ..."
	@echo "==============================================================================="
	pip install pip==25.3 setuptools wheel pip-tools
	pip-compile smarter/requirements/in/base.in -o smarter/requirements/base.txt
	pip-compile smarter/requirements/in/local.in -o smarter/requirements/local.txt
	pip-compile smarter/requirements/in/docker.in -o smarter/requirements/docker.txt


# ---------------------------------------------------------
# Keen
# ---------------------------------------------------------
keen-init:
	cd keen_v3.0.6/tools && npm install --global yarn && \
	npm install gulp@^4.0.2 && \
	npm install gulp-cli && \
	gulp --version

keen-build:
	cd keen_v3.0.6/tools && \
	yarn && \
	gulp --demo1

keen-server:
	cd keen_v3.0.6/tools && \
	gulp localhost


# -------------------------------------------------------------------------
# AWS and deployment
# -------------------------------------------------------------------------
helm-update:
	@echo "==============================================================================="
	@echo "Updating Helm chart dependencies for smarter/charts/smarter ..."
	@echo "==============================================================================="
	cd helm/charts/smarter && \
	helm dependency update


change-log:
	@echo "==============================================================================="
	@echo "Generating changelog..."
	@echo "==============================================================================="
	npx conventional-changelog -p angular -i CHANGELOG.md -s

# -------------------------------------------------------------------------
# Sphinx Documentation
#
# automated ci-cid build target for Sphinx documentation
# python -m sphinx -T -b html -d _build/doctrees -D language=en . $READTHEDOCS_OUTPUT/html
#
# our local build target for Sphinx documentation is intended to try to match
# what ReadTheDocs does as closely as possible.
# -------------------------------------------------------------------------
sphinx-init:
	@echo ""
	@echo "==============================================================================="
	@echo "Initializing Sphinx documentation environment."
	@echo "Note: this is a simplified Python environment that skips setting up the full"
	@echo "      development environment."
	@echo "==============================================================================="
	make check-python		# verify Python 3.13 is installed
	make python-init		# create/replace Python virtual environment and install dependencies
	make build			    # build the Smarter Docker container
	make pre-commit-init	# install and configure pre-commit

sphinx-docs:
	@echo ""
	@echo "==============================================================================="
	@echo "Building Sphinx documentation using local Python environment."
	@echo "This may take a few minutes..."
	@echo "==============================================================================="
	cd docs && make SPHINXOPTS="-W -T -D language=en" html

sphinx-linkcheck:
	cd docs && make linkcheck

######################
# HELP
######################

help:
	@echo '===================================================================='
	@echo 'init                   - Initialize local and Docker environments'
	@echo 'activate               - activates Python virtual environment'
	@echo 'build                  - Build Docker containers'
	@echo 'run                    - run web application from Docker'
	@echo 'test                   - run Python-Django unit tests in Docker'
	@echo 'clean                  - delete all local artifacts, virtual environment, node_modules, and Docker containers'
	@echo 'tear-down              - destroy all docker build and local artifacts'
	@echo '<************************** Code Management **************************>'
	@echo 'lint                   - Run all code linters and formatters'
	@echo 'analyze                - Generate code analysis report using cloc'
	@echo 'coverage               - Generate Docker-based code coverage analysis report'
	@echo 'pre-commit-init        - install and configure pre-commit'
	@echo 'pre-commit-run         - runs all pre-commit hooks on all files'
	@echo 'release                - Force a new Github release'
	@echo '<************************** Docker **************************>'
	@echo 'docker-init            - Initialize MySQL and create the smarter database'
	@echo 'docker-shell           - Open a shell in the smarter-app Docker container'
	@echo 'docker-build           - Build all Docker containers using docker-compose'
	@echo 'docker-run             - Start all Docker containers using docker-compose'
	@echo 'docker-test            - Run Python-Django unit tests in Docker'
	@echo 'docker-prune           - Remove unused Docker objects'
	@echo '<************************** Python **************************>'
	@echo 'python-init            - Create a Python virtual environment and install dependencies'
	@echo 'python-lint            - Run Python linting using pre-commit'
	@echo 'python-clean           - Destroy the Python virtual environment and remove __pycache__ directories'
	@echo 'python-requirements    - compile and update Python dependency files'
	@echo '<************************** Keen **************************>'
	@echo 'keen-init              - Install gulp, yarn and dependencies for Keen'
	@echo 'keen-build             - Build Keen app using gulp'
	@echo 'keen-server            - Start local Keen web server using gulp'
	@echo '<************************** AWS **************************>'
	@echo 'helm-update            - Update Helm chart dependencies'
	@echo '<************************** AWS **************************>'
	@echo 'sphinx-init            - Initialize Sphinx documentation environment'
	@echo 'sphinx-docs            - Build Sphinx documentation'
	@echo '===================================================================='
	@echo 'change-log             - update CHANGELOG.md file'
