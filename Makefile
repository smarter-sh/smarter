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


.PHONY: all init activate collectstatic build run test clean tear-down lint analyze coverage pre-commit-init pre-commit-run release change-log \
	docker-check docker-init docker-shell docker-build docker-run docker-test docker-prune \
	docker-build-for-react \
	python-init python-lint python-clean python-requirements check-python \
	keen-init keen-build keen-server \
	react-install react-build react-build-ci \
	helm-update \
	sphinx-init sphinx-docs sphinx-linkcheck \
	help

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
	make react-build							# build React frontend apps and collect static files
	make collectstatic							# collect static files for the Django admin interface and other components
	make docker-build 			                # build the Smarter containers, including building the React frontend components
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

collectstatic:
	python smarter/manage.py collectstatic --noinput

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
	docker exec smarter-app bash -c "coverage run --source=smarter.apps.account manage.py test smarter.apps.account && coverage report -m"

change-log:
	@echo "==============================================================================="
	@echo "Generating changelog..."
	@echo "==============================================================================="
	npx conventional-changelog -p angular -i CHANGELOG.md -s

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
		python manage.py reset_cache && \
		python manage.py makemigrations && python manage.py migrate && \
		python manage.py initialize_platform && \
		python manage.py add_plugin_examples && \
		python manage.py create_stackademy && \
		python manage.py deploy_builtin_llm_clients && \
		python manage.py deploy_example_llm_client" && \
	docker exec smarter-mysql mysql -u smarter -psmarter -e 'UPDATE smarter.llm_client_llmclient SET deployed = 0;'
	@echo "Docker and Smarter are initialized."
	docker ps


docker-shell:
	make docker-check && \
	docker exec -it smarter-app /bin/bash

# An abbreviated build to improve developer workflow efficiency by skipping
# static asset collection (including by not building the React frontend components)
docker-build:
	make docker-check && \
	docker-compose build \
	  --build-arg DOCKER_COLLECT_STATIC_FILES=false \
      --build-arg DOCKER_REACT_REMOTE_CACHE_BUSTER= \
      --build-arg DOCKER_REACT_REMOTE_CDN_URL= && \
	docker image prune -f

# the DOCKER_REACT_REMOTE_CACHE_BUSTER build argument forces Docker to rebuild the React
# frontend assets from the CDN distribution.
#
# example usage: docker-compose build  --progress=plain --build-arg DOCKER_REACT_REMOTE_CACHE_BUSTER=$(shell date +%s) --build-arg DOCKER_REACT_REMOTE_CDN_URL=https://cdn.smarter.sh/react
docker-build-for-react:
	make docker-check && \
	docker-compose build  --progress=plain \
	  --build-arg DOCKER_COLLECT_STATIC_FILES=true \
      --build-arg DOCKER_REACT_REMOTE_CACHE_BUSTER=$(shell date +%s) \
      --build-arg DOCKER_REACT_REMOTE_CDN_URL=
	docker image prune -f

docker-run:
	make docker-check && \
	docker compose up

docker-test:
	make docker-check && \
	docker exec smarter-app bash -c "python manage.py test smarter.lib"

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

# -------------------------------------------------------------------------
# Helm
# -------------------------------------------------------------------------
helm-update:
	@echo "==============================================================================="
	@echo "Updating Helm chart dependencies for smarter/charts/smarter ..."
	@echo "==============================================================================="
	cd helm/charts/smarter && \
	helm dependency update

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

# ---------------------------------------------------------
# Python
# ---------------------------------------------------------
check-python:
	@echo ""
	@echo "==============================================================================="
	@echo "Verifying that Python $(PYTHON) is installed ..."
	@echo "==============================================================================="
	@echo ""
	@command -v $(PYTHON) >/dev/null 2>&1 || { \
	echo >&2 "This project requires $(PYTHON) but it's not installed.  Aborting."; \
	echo >&2 "python --version output:"; \
	python --version 2>&1; \
	exit 1; \
}

python-init:
	@echo "==============================================================================="
	@echo "Initializing Python virtual environment and installing dependencies. This may take a few minutes..."
	@echo "==============================================================================="
	rm -r -f venv && \
	mkdir -p .pypi_cache && \
	make check-python
	make python-clean && \
	npm install && \
	$(PYTHON) -m venv venv && \
	$(ACTIVATE_VENV) && \
	$(PIP) install pip==25.3 setuptools wheel pip-tools && \
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
# React
# ---------------------------------------------------------
react-install:
	cd smarter/react && npm install --include=dev

react-build:
	@echo "==============================================================================="
	@echo "Building and collecting React files on local filesystem ..."
	@echo "==============================================================================="
	cd smarter/react && NODE_ENV=production npm run build

react-build-ci:
	cd smarter/react && \
	NODE_ENV=production npm ci --include=dev && \
	NODE_ENV=production npm run build

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

sphinx-publish:
	cd docs/build/html && \
	aws s3 sync . s3://docs.smarter.sh/ --delete && \
	aws cloudfront create-invalidation --distribution-id E3J3PFZATCQOFX --paths "/*"

######################
# HELP
######################

help:
	@echo '===================================================================='
	@echo 'init                   - Initialize local and Docker environments'
	@echo 'activate               - Activate Python virtual environment'
	@echo 'build                  - Build Docker containers'
	@echo 'run                    - Run web application from Docker'
	@echo 'test                   - Run Python-Django unit tests in Docker'
	@echo 'clean                  - Delete all local artifacts, virtual environment, node_modules, and Docker containers'
	@echo 'tear-down              - Destroy all Docker build and local artifacts'
	@echo '<************************** Code Management **************************>'
	@echo 'lint                   - Run all code linters and formatters'
	@echo 'analyze                - Generate code analysis report using cloc'
	@echo 'coverage               - Generate Docker-based code coverage report'
	@echo 'pre-commit-init        - Install and configure pre-commit'
	@echo 'pre-commit-run         - Run all pre-commit hooks on all files'
	@echo 'release                - Force a new Github release'
	@echo 'change-log             - Update CHANGELOG.md file'
	@echo '<************************** Docker **************************>'
	@echo 'docker-check           - Verify Docker is installed and running'
	@echo 'docker-init            - Initialize MariaDB and create the smarter database'
	@echo 'docker-shell           - Open a shell in the smarter-app Docker container'
	@echo 'docker-build           - Build all Docker containers using docker-compose'
	@echo 'docker-run             - Start all Docker containers using docker-compose'
	@echo 'docker-test            - Run Python-Django unit tests in Docker'
	@echo 'docker-prune           - Remove unused Docker objects and clean up Docker artifacts'
	@echo '<************************** Python **************************>'
	@echo 'check-python           - Verify Python 3.13 is installed'
	@echo 'python-init            - Create a Python virtual environment and install dependencies'
	@echo 'python-lint            - Run Python linting using pre-commit and pylint'
	@echo 'python-clean           - Destroy the Python virtual environment and remove __pycache__ directories'
	@echo 'python-requirements    - Compile and update Python dependency files'
	@echo '<************************** React **************************>'
	@echo 'react-install          - Install npm dependencies for React frontend apps'
	@echo 'react-build            - Build all React frontend apps and collect static files'
	@echo 'react-build-ci         - Build all React frontend apps using CI settings'
	@echo '<************************** Keen **************************>'
	@echo 'keen-init              - Install gulp, yarn and dependencies for Keen'
	@echo 'keen-build             - Build Keen app using gulp'
	@echo 'keen-server            - Start local Keen web server using gulp'
	@echo '<************************** Helm **************************>'
	@echo 'helm-update            - Update Helm chart dependencies'
	@echo '<************************** Sphinx Documentation **************************>'
	@echo 'sphinx-init            - Initialize Sphinx documentation environment'
	@echo 'sphinx-docs            - Build Sphinx documentation'
	@echo 'sphinx-linkcheck       - Check documentation links'
	@echo 'sphinx-publish         - Publish documentation to AWS S3 and invalidate CloudFront cache'
	@echo '===================================================================='
